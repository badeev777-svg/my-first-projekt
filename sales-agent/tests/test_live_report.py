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


def test_request_ids_are_not_counted_as_digits():
    live = load()
    assert live.strip_request_ids("Запрос №12 передан. Цену уточнит Александр.") == "Запрос  передан. Цену уточнит Александр."
    assert live.strip_request_ids("Стоит 90 000 ₽, заявка № 7") == "Стоит 90 000 ₽, заявка "


def test_failed_check_keeps_transcript_passed_does_not():
    live = load()

    class Fake:
        transcript = ["Клиент: привет", "Бот [200, new]: здравствуйте"]

    assert live.check(False, "n", Fake()) == (live.FAIL, "n", Fake.transcript)
    assert live.check(True, "n", Fake()) == (live.PASS, "n", None)
    assert live.check(False, "n") == (live.FAIL, "n", None)
