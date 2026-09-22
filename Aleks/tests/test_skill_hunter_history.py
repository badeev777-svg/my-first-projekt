import json
import threading

from app.skill_hunter.history import filter_new, load_history, normalize_skill_url, record
from app.skill_hunter.models import SkillCandidate


def _candidate(url: str, title: str = "Some Skill") -> SkillCandidate:
    return SkillCandidate(title=title, url=url, description="desc")


def test_normalize_skill_url_strips_trailing_slash_query_and_case() -> None:
    assert normalize_skill_url("https://GitHub.com/foo/Bar/") == normalize_skill_url(
        "https://github.com/foo/bar"
    )


def test_load_history_missing_file_returns_empty(tmp_path) -> None:
    path = str(tmp_path / "history.json")

    history = load_history(path)

    assert history == {"skills": {}}


def test_load_history_corrupted_file_returns_empty(tmp_path) -> None:
    path = tmp_path / "history.json"
    path.write_text("{not valid json", encoding="utf-8")

    history = load_history(str(path))

    assert history == {"skills": {}}


def test_filter_new_excludes_known_and_within_batch_duplicates() -> None:
    known_url = "https://github.com/foo/known"
    history = {"skills": {normalize_skill_url(known_url): {"first_seen": "x", "niches": ["a"]}}}
    candidates = [
        _candidate(known_url),
        _candidate("https://github.com/foo/new"),
        _candidate("https://github.com/foo/new"),  # duplicate within this batch
    ]

    fresh = filter_new(history, candidates)

    assert [c.url for c in fresh] == ["https://github.com/foo/new"]


def test_record_is_noop_for_empty_candidates(tmp_path) -> None:
    path = str(tmp_path / "history.json")

    record(path, "niche-a", [], now_iso="2026-09-22T00:00:00+00:00")

    assert load_history(path) == {"skills": {}}


def test_record_merges_niches_for_same_skill_across_calls(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    url = "https://github.com/foo/bar"

    record(path, "niche-a", [_candidate(url)], now_iso="2026-09-22T00:00:00+00:00")
    record(path, "niche-b", [_candidate(url)], now_iso="2026-09-23T00:00:00+00:00")

    history = load_history(path)
    entry = history["skills"][normalize_skill_url(url)]
    assert entry["niches"] == ["niche-a", "niche-b"]
    assert entry["first_seen"] == "2026-09-22T00:00:00+00:00"  # unchanged on second call


def test_record_is_dedup_source_for_next_filter_new(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    url = "https://github.com/foo/bar"
    record(path, "niche-a", [_candidate(url)], now_iso="2026-09-22T00:00:00+00:00")

    history = load_history(path)
    fresh = filter_new(history, [_candidate(url)])

    assert fresh == []


def test_record_survives_concurrent_writes_from_two_threads(tmp_path) -> None:
    path = str(tmp_path / "history.json")
    barrier = threading.Barrier(2)

    def write(niche: str, url: str) -> None:
        barrier.wait()
        record(path, niche, [_candidate(url)], now_iso="2026-09-22T00:00:00+00:00")

    t1 = threading.Thread(target=write, args=("niche-a", "https://github.com/foo/one"))
    t2 = threading.Thread(target=write, args=("niche-b", "https://github.com/foo/two"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    history = load_history(path)
    assert len(history["skills"]) == 2  # neither write clobbered the other
