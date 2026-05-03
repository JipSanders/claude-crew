# 🤖 claude-crew

> *An orchestrated team of specialist AI agents — each an expert in their domain, coordinated by a central brain that plans, delegates, and synthesises.*

Give the crew a high-level goal. The Orchestrator figures out which specialists to call, in what order, and passes context between them so each agent builds on the last.

---

## How it works

```
You → "Launch my product on Product Hunt"
        │
        ▼
   🧠 Orchestrator
   Plans: analyst → marketer → designer → sales
        │
        ├─▶ 🔍 Analyst      — researches PH launch best practices
        │        │ results ──▶
        ├─▶ 📣 Marketer     — writes positioning copy and launch post
        │        │ results ──▶
        ├─▶ 🎨 Designer     — builds a landing page from the copy
        │        │ results ──▶
        └─▶ 🤝 Sales        — writes outreach emails to potential upvoters
                │
                ▼
         workspace/          ← all artifacts saved here
```

Every agent runs its own Claude agentic loop with domain-specific tools. The orchestrator waits for each result before deciding the next step — enabling genuine multi-step, multi-agent collaboration.

---

## Agents

| Agent | Role | What it produces |
|-------|------|-----------------|
| 🧠 **Orchestrator** | Central brain | Plans, delegates, synthesises |
| 💻 **Coder** | Senior software engineer | Production code, scripts, APIs |
| 📣 **Marketer** | Growth strategist | Copy, campaigns, launch plans |
| 🎨 **Designer** | UI/UX expert | Working HTML/CSS interfaces |
| 🔍 **Analyst** | Research strategist | Market analysis, competitive intel |
| 🤝 **Sales** | Sales copywriter | Outreach, pitch decks, proposals |

---

## Quickstart

```bash
git clone https://github.com/JipSanders/claude-crew
cd claude-crew
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

```bash
python crew.py "Write a launch strategy and landing page for my SaaS app"
```

All artifacts land in `workspace/`.

---

## Example goals

```bash
# Multi-agent: analyst → marketer → designer
python crew.py "Create a go-to-market strategy and landing page for a developer tool"

# Multi-agent: coder → marketer
python crew.py "Build a Python CLI tool for renaming files, then write the README and launch copy"

# Single-agent deep work
python crew.py "Analyse the competitive landscape for AI coding assistants in 2025"

# Sales focus
python crew.py "Write 3 cold outreach emails targeting CTOs for an AI productivity tool"

# Code execution enabled
python crew.py "Build and run a data analysis script on a sample CSV" --allow-code
```

---

## Options

```
python crew.py "your goal"        Run the crew on a goal
python crew.py --list-agents      Show all available agents
python crew.py "..." --allow-code Let the coder agent execute Python
python crew.py "..." --workspace ./output  Custom output directory
```

---

## Architecture

```
claude-crew/
├── crew.py                 # CLI entry point
└── src/
    ├── orchestrator.py     # Central brain — Claude agent with delegate/complete tools
    ├── display.py          # Rich terminal UI
    └── agents/
        ├── base.py         # BaseAgent: agentic loop, file tools, shared interface
        ├── coder.py
        ├── marketer.py
        ├── designer.py
        ├── analyst.py
        └── sales.py
```

Each specialist is a subclass of `BaseAgent` — just a system prompt and an optional flag to enable extra tools. The `BaseAgent` handles the full Claude agentic loop, tool execution, and workspace file management.

Adding a new specialist is ~15 lines:

```python
# src/agents/researcher.py
from .base import BaseAgent

class ResearcherAgent(BaseAgent):
    name = "researcher"
    description = "Deep researcher — literature reviews, technical summaries"
    color = "blue"
    emoji = "📚"
    system_prompt = "You are a meticulous researcher..."
```

Then register it in `src/agents/__init__.py` and it's immediately available to the orchestrator.

---

## Requirements

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

---

*Part of the [claude-mirror](https://github.com/JipSanders/claude-mirror) ecosystem — tools for working better with AI.*
