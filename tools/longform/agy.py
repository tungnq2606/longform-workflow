"""agy (Gemini, Google Ultra plan) as a Studio job: the argv, and reading what headless agy refused to do.

Headless agy cannot ask for permission: one shell command or MCP call is denied and ends the run, and a --settings
allowlist did not apply (tested 2026-10-31). So prompts forbid both, and agy runs with --sandbox, never with
--dangerously-skip-permissions.
"""
import json
import os

AGY = os.path.expanduser("~/.local/bin/agy")
MODEL = "gemini-4-argon-high"
NO_TOOLS = ("Never run shell commands. Never call MCP tools; use only built-in search_web, URL reading and file "
            "tools. Write only inside the current folder.")


def argv(prompt):
    return [AGY, "-p", prompt, "--model", MODEL, "--sandbox", "--output-format", "json", "--print-timeout", "0"]


def denied(output):
    """Names of the actions agy's JSON output says were denied (empty when none or unreadable)."""
    names = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("{") or "denied_actions" not in line:
            continue
        try:
            data = json.loads(line)
        except ValueError:
            continue
        names += [d.get("display_name") or d.get("action") or "?" for d in data.get("denied_actions") or []]
    return names
