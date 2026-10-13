import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "live_acceptance.py"


def load():
    spec = importlib.util.spec_from_file_location("live_acceptance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_report_replaces_only_live_block(tmp_path):
    live = load()
    path = tmp_path / "report.md"
    path.write_text(f"вступление\n{live.START}\nстарое\n{live.END}\nконец\n", encoding="utf-8")
    live.write_report(path, "новое")
    text = path.read_text(encoding="utf-8")
    assert "вступление" in text and "конец" in text and "новое" in text and "старое" not in text


def test_write_report_creates_missing_file(tmp_path):
    live = load()
    path = tmp_path / "report.md"
    live.write_report(path, "таблица")
    text = path.read_text(encoding="utf-8")
    assert text.index(live.START) < text.index("таблица") < text.index(live.END)
