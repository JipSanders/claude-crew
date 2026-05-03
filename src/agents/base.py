"""
BaseAgent: the core agentic loop all specialist agents inherit from.

Each agent runs its own Claude instance with a specialised system prompt
and a set of domain tools. The loop continues until Claude signals end_turn
(no more tool calls needed).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import anthropic

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8096
WORKSPACE = Path("workspace")


@dataclass
class AgentResult:
    agent_name: str
    task: str
    output: str
    artifacts: list[str] = field(default_factory=list)
    success: bool = True


# ── Shared tool definitions ────────────────────────────────────────────────

FILE_TOOLS = [
    {
        "name": "write_file",
        "description": "Write content to a file in the workspace directory. Use this to save all deliverables.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename (e.g. 'landing_page.html', 'copy.md'). Subdirectories allowed.",
                },
                "content": {
                    "type": "string",
                    "description": "Full file content to write.",
                },
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from the workspace directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename relative to workspace/",
                },
            },
            "required": ["filename"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files currently in the workspace directory.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]

CODE_TOOL = {
    "name": "run_python",
    "description": "Execute a Python code snippet and return stdout/stderr. Use sparingly — only for computation or validation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute.",
            },
        },
        "required": ["code"],
    },
}


# ── Tool executors ─────────────────────────────────────────────────────────

def _write_file(filename: str, content: str, workspace: Path) -> str:
    path = workspace / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Saved to workspace/{filename} ({len(content):,} chars)"


def _read_file(filename: str, workspace: Path) -> str:
    path = workspace / filename
    if not path.exists():
        return f"Error: workspace/{filename} not found"
    return path.read_text(encoding="utf-8")


def _list_files(workspace: Path) -> str:
    if not workspace.exists():
        return "Workspace is empty."
    files = sorted(workspace.rglob("*"))
    if not files:
        return "Workspace is empty."
    return "\n".join(f"  workspace/{f.relative_to(workspace)}" for f in files if f.is_file())


def _run_python(code: str) -> str:
    try:
        result = subprocess.run(
            ["python3", "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if err:
            return f"stdout:\n{out}\nstderr:\n{err}" if out else f"stderr:\n{err}"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: execution timed out after 15s"
    except Exception as e:
        return f"Error: {e}"


# ── BaseAgent ──────────────────────────────────────────────────────────────

class BaseAgent:
    name: str = "agent"
    description: str = ""
    system_prompt: str = ""
    color: str = "white"
    emoji: str = "🤖"

    # Subclasses set this to True to include CODE_TOOL
    include_code_tool: bool = False

    def __init__(
        self,
        workspace: Path | None = None,
        on_event: Callable[[str, str, str], None] | None = None,
        allow_code_execution: bool = False,
    ) -> None:
        self.workspace = workspace or WORKSPACE
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.on_event = on_event or (lambda kind, agent, msg: None)
        self.allow_code_execution = allow_code_execution
        self._artifacts: list[str] = []

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
        self._client = anthropic.Anthropic(api_key=api_key)

    @property
    def tools(self) -> list[dict]:
        t = list(FILE_TOOLS)
        if self.include_code_tool and self.allow_code_execution:
            t.append(CODE_TOOL)
        return t

    def _execute_tool(self, name: str, inputs: dict[str, Any]) -> str:
        if name == "write_file":
            result = _write_file(inputs["filename"], inputs["content"], self.workspace)
            self._artifacts.append(f"workspace/{inputs['filename']}")
            self.on_event("file", self.name, inputs["filename"])
            return result
        if name == "read_file":
            return _read_file(inputs["filename"], self.workspace)
        if name == "list_files":
            return _list_files(self.workspace)
        if name == "run_python":
            self.on_event("code", self.name, "running python snippet")
            return _run_python(inputs["code"])
        return f"Unknown tool: {name}"

    def run(self, task: str, context: str = "") -> AgentResult:
        self._artifacts = []
        self.on_event("start", self.name, task)

        user_content = task
        if context:
            user_content = f"{task}\n\n---\nContext from previous work:\n{context}"

        messages: list[dict] = [{"role": "user", "content": user_content}]

        while True:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                output = " ".join(
                    block.text for block in response.content if hasattr(block, "text")
                ).strip()
                self.on_event("done", self.name, output[:120] + "..." if len(output) > 120 else output)
                return AgentResult(
                    agent_name=self.name,
                    task=task,
                    output=output,
                    artifacts=list(self._artifacts),
                    success=True,
                )

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason — bail gracefully
                return AgentResult(
                    agent_name=self.name,
                    task=task,
                    output=f"Stopped unexpectedly: {response.stop_reason}",
                    artifacts=list(self._artifacts),
                    success=False,
                )
