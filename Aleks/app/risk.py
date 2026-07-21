# app/risk.py
import re

_RISKY_BASH_PATTERNS = [
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+commit\b.*--amend"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bdocker\b"),
    re.compile(r"\bsystemctl\s+(restart|stop)\b"),
    re.compile(r"deploy"),
]

_COMMAND_SEPARATORS = re.compile(r"[;&|]+")


def _is_recursive_force_rm(command: str) -> bool:
    """Detect `rm` invocations combining recursive + force semantics,
    regardless of flag order/case/short-vs-long form (-rf, -fr, -Rf, -RF,
    -r -f, --recursive --force, ...). A plain regex on a fixed token order
    (e.g. `rm -rf`) is trivially bypassed by `rm -fr` or `rm -Rf`, so each
    `;`/`&`/`|`-separated command segment is tokenized and its `rm` flags
    are inspected individually instead."""
    for segment in _COMMAND_SEPARATORS.split(command):
        tokens = segment.split()
        if not tokens or tokens[0].rsplit("/", 1)[-1].lower() != "rm":
            continue
        short_flags = ""
        long_flags = set()
        for token in tokens[1:]:
            lowered = token.lower()
            if lowered.startswith("--"):
                long_flags.add(lowered)
            elif lowered.startswith("-"):
                short_flags += lowered[1:]
        recursive = "r" in short_flags or "--recursive" in long_flags
        force = "f" in short_flags or "--force" in long_flags
        if recursive and force:
            return True
    return False


_RISKY_PATH_PATTERNS = [
    re.compile(r"\.env(\.|$)"),
    re.compile(r"credentials", re.IGNORECASE),
    re.compile(r"secrets", re.IGNORECASE),
    re.compile(r"\.pem$"),
]

_RISKY_WRITE_TOOLS = {"Write", "Edit", "MultiEdit"}


def is_risky(tool_name: str, tool_input: dict) -> bool:
    """Decide whether a tool call needs Telegram confirmation before running."""
    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        if _is_recursive_force_rm(command):
            return True
        return any(pattern.search(command) for pattern in _RISKY_BASH_PATTERNS)
    if tool_name in _RISKY_WRITE_TOOLS:
        path = str(tool_input.get("file_path", ""))
        return any(pattern.search(path) for pattern in _RISKY_PATH_PATTERNS)
    return False
