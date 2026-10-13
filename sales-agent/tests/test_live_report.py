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


def test_render_masks_phone_in_transcripts_and_has_manual_line():
    live = load()
    out = live.render([(1, "t", live.MANUAL, "n")], [(1, "t", ["Клиент: +7 900 123-45-67"])], "m")
    assert "900 123-45-67" not in out and "+7*** ***-**-67" in out
    assert live.MANUAL_LINE in out
