# Context Excavator

> Stop drowning in your own code when asking AI for help.

When your project grows beyond 3-4 files, copy-pasting everything into an LLM stops working. The AI gets lost in boilerplate, loses track of how files connect, and gives you vague or wrong answers.

Context Excavator fixes this. It X-rays your Python project and produces a single architecture map — `CONTEXT.md` — that gives an LLM everything it needs to understand your codebase without reading every line.

An agent then uses that map to either audit your architecture for risks, or trace a specific error through your file dependency chain.

---

## The Problem
```
You: *pastes 400 lines into ChatGPT*
LLM: *gets confused, gives wrong fix, breaks something else*
```

The LLM doesn't know that `database.py` is called from `utils.py` which is called from `main.py`. It only sees the file you pasted. So its fix works in isolation but breaks the chain.

---

## The Solution
```
You: python agent.py your-project "TypeError in database.py line 47"
Agent: *scans architecture, traces error chain, deep dives flagged file*
You: *opens AGENT_REPORT.md with exact file, exact line, exact fix*
```

---

## How It Works

### 1. The Scanner (`pruner.py`)
Uses Python's built-in `ast` (Abstract Syntax Tree) library to X-ray every `.py` file. Instead of reading code as plain text, AST understands structure. It extracts only:
- Class names
- Function signatures (name + arguments)
- Import relationships between files

It ignores everything inside function bodies — the repetitive logic, the long strings, the boilerplate. What remains is the skeleton.

### 2. The Output (`CONTEXT.md`)
A single markdown file — your project's cheat sheet. Shows every file, what's inside it, and what it depends on. This is what gets sent to the LLM instead of your entire codebase.

### 3. The Agent (`agent.py`)
Runs in 3 modes based on what you provide:

| Mode | Trigger | What happens |
|------|---------|--------------|
| General Scan | No error provided | LLM audits architecture, finds risky functions |
| Manual Debug | Error typed in command | LLM traces error through file dependency chain |
| Auto Debug | `error.log` exists | Agent detects error automatically, same as above |

After the first LLM response, the agent scans which filenames were mentioned. If a specific file was flagged, the agent reads that file fully and calls the LLM a second time for a deeper analysis. This second action based on the first result is what makes it an agent, not just a script.

### 4. Cursor Integration
The `.cursorrules` file acts as a permanent system prompt for Cursor AI. Every time you ask Cursor a question about your code, it reads `CONTEXT.md` first — giving it architectural awareness before it even sees your question.

---

## Performance Metric — Context Leverage Factor (CLF)

The CLF score measures how effectively the tool compresses your codebase:
```
reduction_ratio = 1 - (skeletal_chars / original_chars)
CLF_score = int(reduction_ratio * 10,000)
```

A score of 9230/10,000 means the tool reduced your codebase to 7.7% of its original size while preserving all structural information the LLM needs.

Higher score = more noise removed = better LLM performance.

---

## Benchmark

**Task:** "Find the bug causing TypeError in this project"

| | Without Context Excavator | With Context Excavator |
|--|--------------------------|----------------------|
| Input to LLM | 3 files, ~400 lines | CONTEXT.md + 1 file, ~80 lines |
| Tokens used | ~1800 | ~380 |
| LLM traced full chain | No — saw only pasted file | Yes — knew all dependencies |
| Answer quality | Generic, missed root cause | Traced to exact upstream function |
| Follow-up prompts needed | 3 | 1 |

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/architect-agent
cd architect-agent
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set your Groq API key**

Get a free key at [console.groq.com](https://console.groq.com)
```bash
# Windows PowerShell:
$env:GROQ_API_KEY="your-key-here"

# Mac/Linux:
export GROQ_API_KEY="your-key-here"
```

---

## Usage

### Mode 1 — General architecture scan
```bash
python agent.py path/to/your/project
```
No error? Agent proactively scans for risky functions and missing error handling.

### Mode 2 — Debug a specific error
```bash
python agent.py path/to/your/project "paste your full error message here"
```
Agent traces the error through your architecture and identifies the root cause.

### Mode 3 — Automatic error detection
```bash
# Step 1: Run your project and capture errors
python your_project/main.py 2> error.log

# Step 2: Run agent — it finds error.log automatically
python agent.py path/to/your/project
```

### Output
All findings are written to `AGENT_REPORT.md` in your project root. The report includes:
- Which mode ran
- LLM's full analysis
- Deep dive on the flagged file (if any)

---

## Project Structure
```
architect-agent/
├── agent_engine/
│   └── pruner.py          # Core scanner — AST extraction engine
├── demo_repo/             # Sample project for testing
│   ├── sub_logic/
│   │   └── database.py
│   ├── main.py
│   └── utils.py
├── tests/
│   └── test_engine.py     # Tests for pruner
├── agent.py               # Main agent — orchestrates everything
├── requirements.txt       # Dependencies
├── .env.example           # Environment variable template
├── .cursorrules           # Cursor AI system prompt
└── README.md
```

---

## Why This Problem

When I started building multi-file Python projects, I kept hitting the same wall. I'd get an error, paste my entire codebase into an LLM, and get a generic answer that fixed the error on one line but broke something upstream. The LLM had no map of how my files connected.

The real problem isn't that LLMs are bad at debugging. It's that they need architectural context, not raw code. Context Excavator gives them the map first, then the specific problem. That combination produces precise answers instead of guesses.

---

## Tech Stack

- **Python** — core engine
- **AST** — structural code analysis (built-in, no install needed)
- **Groq API** — LLM inference (free tier, Llama 3.3 70B)
- **Pathlib / os.walk** — file system crawler
- **Subprocess** — agent orchestration
- **Markdown** — CONTEXT.md and AGENT_REPORT.md output

---

## Quest Submission Notes

**Performance metric:** Context Leverage Factor (CLF) — measures structural compression ratio on a 0–10,000 scale. Calculation: `int((1 - skeletal_chars/original_chars) * 10000)`

**Benchmark comparison:** See Benchmark section above — tested against direct LLM prompting without context extraction on identical debugging tasks.

**Problem chosen:** Multi-file LLM context loss during debugging — chosen because it is a daily friction point for any developer using AI assistance on projects beyond toy size. Every extra file you add to a project makes raw copy-paste prompting worse. This problem only grows.

**Cursor integration:** `.cursorrules` configures Cursor AI to read `CONTEXT.md` before answering any code question — making Cursor architecturally aware of your project automatically.