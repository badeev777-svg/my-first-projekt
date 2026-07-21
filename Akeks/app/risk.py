# app/risk.py
import re

_RISKY_BASH_PATTERNS = [
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+commit\b.*--amend"),
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bdocker\b"),
    re.compile(r"\bsystemctl\s+(restart|stop)\b"),
    re.compile(r"deploy"),
]

_RISKY_PATH_PATTERNS = [
    re.compile(r"\.env(\.|$)"),
    re.compile(r"credentials", re.IGNORECASE),
    re.compile(r"secrets", re.IGNORECASE),
    re.compile(r"\.pem$"),
]

_RISKY_WRITE_TOOLS = {"Write", "Edit"}


def is_risky(tool_name: str, tool_input: dict) -> bool:
    """Decide whether a tool call needs Telegram confirmation before running."""
    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        return any(pattern.search(command) for pattern in _RISKY_BASH_PATTERNS)
    if tool_name in _RISKY_WRITE_TOOLS:
        path = str(tool_input.get("file_path", ""))
        return any(pattern.search(path) for pattern in _RISKY_PATH_PATTERNS)
    return False
