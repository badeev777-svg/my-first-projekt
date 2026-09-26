"""Приёмка на живом cloud.ru: 7 вопросов с ответом в документах, 3 — без ответа."""
import sys
from pathlib import Path

from app.chunker import chunk_units
from app.cloudru import CloudRuClient
from app.config import Settings
from app.extract import extract
from app.rag import NOT_FOUND, answer
from app.session_store import SessionStore

DEMO = Path(__file__).resolve().parent.parent / "demo_docs"

CASES: list[tuple[str, str | None]] = [
    ("Сколько календарных дней длится ежегодный отпуск?", "28"),
    ("За сколько дней нужно подать заявление на отпуск?", "14"),
    ("Сколько стоит тариф «Расширенный»?", "25000"),
    ("Какая скидка при оплате за год?", "10%"),
    ("В какой срок заказчик должен оплатить счёт?", "5"),
    ("За сколько дней нужно уведомить о расторжении договора?", "30"),
    ("Какая гарантия на выполненные работы?", "6"),
    ("Какой размер ДМС у сотрудников?", None),
    ("Сколько стоит обслуживание сервера 1С?", None),
    ("Кто генеральный директор компании?", None),
]


def norm(s: str) -> str:
    return s.replace("\u00a0", "").replace("\u202f", "").replace(" ", "")


def main() -> int:
    settings = Settings()
    client = CloudRuClient(settings)
    store = SessionStore(3600)
    session = store.create()
    for path in sorted(DEMO.glob("*.docx")):
        chunks = chunk_units(extract(path.name, path.read_bytes()))
        store.add_document(session, path.name, chunks, client.embed([c.text for c in chunks]))

    failed = 0
    for question, expected in CASES:
        result = answer(client, session, question)
        if expected is None:
            ok = result.text == NOT_FOUND
        else:
            ok = norm(expected) in norm(result.text) and bool(result.sources)
        failed += not ok
        print(("OK  " if ok else "FAIL"), question)
        print("     ", result.text)
        for s in result.sources:
            print("      ->", s.file, s.loc)
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
