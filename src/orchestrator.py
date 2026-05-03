"""
Orchestrator: the central brain of claude-crew.

It runs its own Claude agentic loop with two tools:
  - delegate_to_agent: hand a task to a specialist
  - complete: mark the goal done and return a summary

It receives results from each agent and uses them as context when
deciding what to do next — enabling genuine multi-step, multi-agent collaboration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import anthropic

from .agents import REGISTRY
from .agents.base import MODEL, MAX_TOKENS, AgentResult

ORCHESTRATOR_SYSTEM = """You are the Orchestrator of an elite AI team called Claude Crew.

Your team:
  • coder     — senior software engineer, writes production code in any language
  • marketer  — growth marketer, writes copy, campaigns, positioning, launch plans
  • designer  — UI/UX expert, produces working HTML/CSS interfaces
  • analyst   — research analyst, competitive intelligence, strategic synthesis
  • sales     — sales strategist, outreach emails, pitch decks, proposals

Your job:
1. Analyse the user's goal and form a clear plan
2. Break the goal into specific, well-scoped tasks
3. Delegate each task to the right specialist using delegate_to_agent
4. Pass relevant context from earlier agents to later ones
5. Once all tasks are done, call complete with a summary

Rules:
- Be strategic about sequencing: analyst research should inform marketer copy;
  marketer copy should inform designer landing page; etc.
- One delegate_to_agent call per turn — wait for results before deciding next steps
- Keep task descriptions specific and actionable, not vague
- When passing context, summarise the key outputs — don't dump everything
- Call complete only when the goal is genuinely accomplished
"""

DELEGATE_TOOL = {
    "name": "delegate_to_agent",
    "description": "Delegate a specific task to one specialist agent on your team.",
    "input_schema": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": ["coder", "marketer", "designer", "analyst", "sales"],
                "description": "Which specialist to assign this task to.",
            },
            "task": {
                "type": "string",
                "description": "Clear, specific task description. Include all context the agent needs.",
            },
            "context": {
                "type": "string",
                "description": "Relevant output from previous agents. Omit if this is the first delegation.",
            },
        },
        "required": ["agent", "task"],
    },
}

COMPLETE_TOOL = {
    "name": "complete",
    "description": "Mark the overall goal as complete. Call this once all tasks are done.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Summary of what was accomplished, which agents were used, and where artifacts are saved.",
            },
        },
        "required": ["summary"],
    },
}


@dataclass
class CrewResult:
    goal: str
    summary: str
    agent_results: list[AgentResult] = field(default_factory=list)
    success: bool = True


class Orchestrator:
    def __init__(
        self,
        workspace: Path | None = None,
        on_event: Callable[[str, str, str], None] | None = None,
        allow_code_execution: bool = False,
    ) -> None:
        self.workspace = workspace or Path("workspace")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.on_event = on_event or (lambda kind, agent, msg: None)
        self.allow_code_execution = allow_code_execution

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _get_agent(self, name: str):
        cls = REGISTRY.get(name)
        if cls is None:
            return None
        return cls(
            workspace=self.workspace,
            on_event=self.on_event,
            allow_code_execution=self.allow_code_execution,
        )

    def run(self, goal: str) -> CrewResult:
        self.on_event("orchestrator_start", "orchestrator", goal)

        agent_results: list[AgentResult] = []
        final_summary = ""
        completed = False

        messages: list[dict] = [{"role": "user", "content": f"Goal: {goal}"}]

        while not completed:
            self.on_event("orchestrator_thinking", "orchestrator", "Planning next step...")

            response = self._client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=ORCHESTRATOR_SYSTEM,
                tools=[DELEGATE_TOOL, COMPLETE_TOOL],
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Orchestrator wrapped up without calling complete — extract text
                final_summary = " ".join(
                    b.text for b in response.content if hasattr(b, "text")
                ).strip()
                completed = True
                break

            if response.stop_reason == "tool_use":
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    if block.name == "complete":
                        final_summary = block.input.get("summary", "")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": "Goal marked as complete.",
                        })
                        completed = True

                    elif block.name == "delegate_to_agent":
                        agent_name = block.input["agent"]
                        task = block.input["task"]
                        context = block.input.get("context", "")

                        agent = self._get_agent(agent_name)
                        if agent is None:
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": f"Error: unknown agent '{agent_name}'",
                            })
                            continue

                        result = agent.run(task, context)
                        agent_results.append(result)

                        # Build a rich tool result so orchestrator knows what happened
                        artifact_list = "\n".join(f"  - {a}" for a in result.artifacts)
                        tool_result_text = f"""Agent '{agent_name}' completed the task.

Output summary:
{result.output[:1500]}

Artifacts saved:
{artifact_list if artifact_list else '  (none)'}
"""
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": tool_result_text,
                        })

                messages.append({"role": "user", "content": tool_results})

            else:
                # Unexpected stop — bail
                final_summary = f"Stopped unexpectedly: {response.stop_reason}"
                completed = True

        self.on_event("orchestrator_done", "orchestrator", final_summary)
        return CrewResult(
            goal=goal,
            summary=final_summary,
            agent_results=agent_results,
            success=True,
        )
