# app/risk.py
import re
import shlex

_RISKY_BASH_PATTERNS = [
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+commit\b.*--amend"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bdocker\b"),
    re.compile(r"\bsystemctl\s+(restart|stop)\b"),
    re.compile(r"\bdeploy\S*\.(sh|py)\b"),
]

_COMMAND_SEPARATORS = re.compile(r"[;&|]+")

_SHELL_BINARIES = {"bash", "sh", "zsh", "dash", "ksh"}


def _tokenize(segment: str) -> list[str]:
    """Tokenize a shell-like segment, honoring quotes so a construct like
    `bash -c "rm -rf /x"` keeps its nested command as one token instead of
    scattering it. Falls back to a plain whitespace split for fragments
    shlex can't parse (e.g. a `find -exec ... \\;` clause chopped mid-escape
    by the top-level `;` segment split)."""
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def _flags_have_recursive_force(flag_tokens: list[str]) -> bool:
    short_flags = ""
    long_flags = set()
    for token in flag_tokens:
        lowered = token.lower()
        if lowered.startswith("--"):
            long_flags.add(lowered)
        elif lowered.startswith("-"):
            short_flags += lowered[1:]
    recursive = "r" in short_flags or "--recursive" in long_flags
    force = "f" in short_flags or "--force" in long_flags
    return recursive and force


def _segment_has_recursive_force_rm(tokens: list[str]) -> bool:
    """Scan every token of an already-tokenized command segment (not just
    token[0]) for an `rm` invocation, since `rm` can appear anywhere: after
    `find -exec`, after `xargs`, after an env-var prefix like `FOO=bar`,
    after `eval`, or backgrounded with a trailing `&`. Also unwraps the
    nested command hidden inside `bash -c "..."` / `sh -c "..."` / `eval
    "..."`, whose quoted argument shlex keeps as a single token."""
    for index, token in enumerate(tokens):
        base = token.rsplit("/", 1)[-1].lower()
        if base == "rm" and _flags_have_recursive_force(tokens[index + 1 :]):
            return True
        if (
            base == "-c"
            and index > 0
            and tokens[index - 1].rsplit("/", 1)[-1].lower() in _SHELL_BINARIES
            and index + 1 < len(tokens)
            and _is_recursive_force_rm(tokens[index + 1])
        ):
            return True
        if base == "eval" and index + 1 < len(tokens):
            if _is_recursive_force_rm(" ".join(tokens[index + 1 :])):
                return True
    return False


def _is_recursive_force_rm(command: str) -> bool:
    """Detect `rm` invocations combining recursive + force semantics,
    regardless of flag order/case/short-vs-long form (-rf, -fr, -Rf, -RF,
    -r -f, --recursive --force, ...) and regardless of how `rm` is reached
    (directly, via `find -exec`, `xargs`, `eval`, `bash -c`/`sh -c`, an
    env-var prefix, or backgrounded with `&`). A plain regex on a fixed
    token order (e.g. `rm -rf`) is trivially bypassed by `rm -fr` or `rm
    -Rf`, so each `;`/`&`/`|`-separated command segment is tokenized and
    scanned for `rm` and its flags instead."""
    for segment in _COMMAND_SEPARATORS.split(command):
        if _segment_has_recursive_force_rm(_tokenize(segment)):
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
