import sys
sys.stdout.reconfigure(encoding='utf-8')
from groq import Groq
import subprocess
from pathlib import Path

# ── MODE DETECTION ────────────────────────────────────────────────────────

def get_error_from_log(log_path: str = "error.log") -> str:
    """
    Looks for error.log in current folder.
    If it exists and has content, reads it and returns the error text.
    If not found, returns None → agent falls back to general scan.
    """
    log_file = Path(log_path)
    if log_file.exists() and log_file.stat().st_size > 0:
        print("[Agent] Found error.log — reading automatically...")
        return log_file.read_text().strip()
    return None


def detect_mode(manual_error: str = None) -> tuple:
    """
    Checks which of 3 modes to run.
    Returns (mode_name, error_message).

    Priority:
    1. User typed error in terminal        → MANUAL DEBUG
    2. error.log exists with content       → AUTO DEBUG
    3. Neither                             → GENERAL SCAN
    """
    if manual_error:
        print("[Agent] Mode: MANUAL DEBUG — using error you provided")
        return "manual_debug", manual_error

    log_error = get_error_from_log()
    if log_error:
        print("[Agent] Mode: AUTO DEBUG — found error.log")
        return "auto_debug", log_error

    print("[Agent] Mode: GENERAL SCAN — no error found, scanning for risks")
    return "general", None


# ── CONTEXT GENERATION ────────────────────────────────────────────────────

def generate_context(target_path: str) -> str:
    """
    Calls pruner.py on the target folder using --path argument.
    Pruner generates CONTEXT.md, this function reads and returns it.
    """
    print(f"[Agent] Scanning project at: {target_path}")

    result = subprocess.run(
        ["python", "agent_engine/pruner.py", "--path", target_path],
        capture_output=True,
        text=True
    )
    # subprocess.run executes pruner.py exactly like typing it in terminal
    # capture_output=True means we capture what pruner prints
    # text=True means output comes back as string not bytes

    if result.stdout:
        print(result.stdout)  # show pruner's output to user

    if result.returncode != 0:
        # returncode != 0 means pruner crashed
        print(f"[Agent] Pruner failed: {result.stderr}")
        raise RuntimeError("pruner.py failed. See error above.")

    context_file = Path("CONTEXT.md")
    if not context_file.exists():
        raise FileNotFoundError("CONTEXT.md not generated. Check pruner.py.")

    return context_file.read_text(encoding='utf-8')


# ── PROMPT BUILDER ────────────────────────────────────────────────────────

def build_prompt(context: str, error_message: str = None) -> str:
    """
    Builds different prompts based on mode.
    Debug mode → trace the specific error through the architecture.
    General mode → proactively find risks.
    """
    if error_message:
        return f"""You are a senior Python debugger.

I will give you two things:
1. An architecture map of my Python project
   (shows all files, functions, and how they connect)
2. An error message I got when running the project

Your job:
1. Use the architecture map to trace WHERE this error is coming from
2. Name the exact file and function that is causing it
3. Explain WHY in simple terms
4. Give the fix in one or two lines of code

Architecture map:
{context}

Error message:
{error_message}"""

    else:
        return f"""You are a senior code reviewer.

I will give you an architecture map of a Python project.
It shows every file, classes, functions, and how files import each other.

Your job:
1. Find the 3 riskiest functions most likely to break
2. Find files with no error handling
3. Tell me which file to look at first and why

Architecture map:
{context}"""


# ── LLM CALL ─────────────────────────────────────────────────────────────

def call_llm(prompt: str) -> str:
    """
    Sends prompt to Groq. Returns response text.
    Groq() automatically reads GROQ_API_KEY from your environment.
    """
    client = Groq()
    print("[Agent] Calling LLM...")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
    # Groq uses .choices[0].message.content
    # This is different from Anthropic which uses .content[0].text


# ── REPORT WRITING ────────────────────────────────────────────────────────

def write_report(findings: str, mode: str, error_message: str = None):
    """Saves LLM findings to AGENT_REPORT.md with mode label in header."""

    labels = {
        "manual_debug": "Debug Report — Manual Error Input",
        "auto_debug":   "Debug Report — Auto Detected from error.log",
        "general":      "General Risk Analysis"
    }

    error_line = f"\n**Error Analyzed:** `{error_message}`\n" if error_message else ""

    content = f"""# Context Excavator — Agent Report
## Mode: {labels[mode]}
{error_line}
---

{findings}
"""
    Path("AGENT_REPORT.md").write_text(content)
    print("[Agent] Report written to AGENT_REPORT.md")


# ── DEEP DIVE (THE AGENTIC LOOP) ──────────────────────────────────────────

def deep_dive(target_path: str, findings: str, error_message: str = None):
    """
    This is what makes it an agent not just a script.

    After first LLM response, agent scans which filenames were mentioned.
    If LLM said 'look at utils.py', agent reads utils.py fully.
    Then asks LLM a second, deeper question about just that file.

    Second action based on first result = agent behavior.
    """
    print("\n[Agent] Checking if LLM flagged a specific file...")

    py_files = list(Path(target_path).rglob("*.py"))
    flagged_file = None

    for py_file in py_files:
        if py_file.name in findings:
            # LLM mentioned this filename in its response
            flagged_file = py_file
            print(f"[Agent] {py_file.name} was flagged — deep scanning...")
            break

    if not flagged_file:
        print("[Agent] No file flagged. Agent complete.")
        return

    file_content = flagged_file.read_text()

    if error_message:
        deep_prompt = f"""You said {flagged_file.name} is connected to this error:
{error_message}

Here is the full file:
{file_content}

Now tell me:
1. Exact line number causing the issue
2. Why that line breaks
3. One line fix"""
    else:
        deep_prompt = f"""You flagged {flagged_file.name} as risky.

Here is the full file:
{file_content}

Now tell me:
1. Exact line most likely to cause a bug
2. Why it breaks
3. One line fix"""

    deep_findings = call_llm(deep_prompt)

    # Append to existing report — does not overwrite, adds below
    with open("AGENT_REPORT.md", "a") as f:
        f.write(f"\n\n---\n## Deep Dive: {flagged_file.name}\n\n{deep_findings}")

    print(f"[Agent] Deep dive on {flagged_file.name} added to report.")


# ── ENTRY POINT ───────────────────────────────────────────────────────────

def agent_loop(target_path: str, manual_error: str = None):
    mode, error_message = detect_mode(manual_error)
    context = generate_context(target_path)
    prompt = build_prompt(context, error_message)
    findings = call_llm(prompt)
    write_report(findings, mode, error_message)
    deep_dive(target_path, findings, error_message)
    print("\n[Agent] Done. Open AGENT_REPORT.md to see full results.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nContext Excavator Agent")
        print("─" * 40)
        print("Mode 1 - General scan:")
        print("  python agent.py demo_repo")
        print("\nMode 2 - Manual error debug:")
        print("  python agent.py demo_repo \"paste your error here\"")
        print("\nMode 3 - Auto error detection:")
        print("  python demo_repo/main.py 2> error.log")
        print("  python agent.py demo_repo")
        print("─" * 40)
        sys.exit(1)

    project_path = sys.argv[1]
    manual_error = sys.argv[2] if len(sys.argv) > 2 else None
    # sys.argv[1] → first thing you type after agent.py = project path
    # sys.argv[2] → second thing you type = error message (optional)

    agent_loop(project_path, manual_error)