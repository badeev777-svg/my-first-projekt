import json
import os
from urllib.parse import urlsplit, urlunsplit

from filelock import FileLock

from app.skill_hunter.models import SkillCandidate


def normalize_skill_url(url: str) -> str:
    parts = urlsplit(url.strip().lower())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def load_history(path: str) -> dict:
    if not os.path.exists(path):
        return {"skills": {}}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"skills": {}}
    if not isinstance(data, dict) or not isinstance(data.get("skills"), dict):
        return {"skills": {}}
    return data


def filter_new(history: dict, candidates: list[SkillCandidate]) -> list[SkillCandidate]:
    known = history.get("skills", {})
    seen_in_batch: set[str] = set()
    fresh: list[SkillCandidate] = []
    for candidate in candidates:
        key = normalize_skill_url(candidate.url)
        if key in known or key in seen_in_batch:
            continue
        seen_in_batch.add(key)
        fresh.append(candidate)
    return fresh


def record(path: str, niche: str, candidates: list[SkillCandidate], now_iso: str) -> None:
    if not candidates:
        return
    lock = FileLock(f"{path}.lock")
    with lock:
        history = load_history(path)
        for candidate in candidates:
            key = normalize_skill_url(candidate.url)
            entry = history["skills"].setdefault(key, {"first_seen": now_iso, "niches": []})
            if niche not in entry["niches"]:
                entry["niches"].append(niche)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
