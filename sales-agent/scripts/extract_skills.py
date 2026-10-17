"""Копирует 6 навыков из Приложения B ТЗ в skills/<name>/SKILL.md без изменений."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEF = ROOT / "ai-sales-build-brief.md"
NAMES = (
    "sales-discovery",
    "sales-product-match",
    "sales-objections",
    "sales-lead-capture",
    "sales-human-handoff",
    "sales-quality-check",
)
BLOCK = re.compile(r"^### skills/(?P<name>[a-z-]+)/SKILL\.md\n\n```markdown\n(?P<body>.*?)\n```$", re.S | re.M)


def extract(text: str) -> dict[str, str]:
    text = text.replace("\r\n", "\n")
    return {m["name"]: m["body"] + "\n" for m in BLOCK.finditer(text)}


def main() -> None:
    blocks = extract(BRIEF.read_text(encoding="utf-8"))
    missing = sorted(set(NAMES) - set(blocks))
    if missing:
        sys.exit(f"В ТЗ не найдены навыки: {missing}")
    for name in NAMES:
        path = ROOT / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(blocks[name], encoding="utf-8", newline="\n")
        print(f"записан {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
