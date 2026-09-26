from app.chunker import Chunk, chunk_units
from app.extract import Unit


def u(num, text, file="a.docx", kind="абз."):
    return Unit(file, kind, num, text)


def test_short_units_packed_with_loc_range():
    chunks = chunk_units([u(1, "a" * 300), u(2, "b" * 300), u(3, "c" * 300)], size=800, overlap=100)
    assert chunks == [
        Chunk("a.docx", "абз. 1–2", "a" * 300 + "\n" + "b" * 300),
        Chunk("a.docx", "абз. 3", "c" * 300),
    ]


def test_files_are_not_mixed():
    chunks = chunk_units([u(1, "x", file="a.docx"), u(1, "y", file="b.docx")])
    assert [(c.file, c.text) for c in chunks] == [("a.docx", "x"), ("b.docx", "y")]


def test_long_unit_split_with_overlap():
    text = "".join(chr(ord("a") + i % 26) for i in range(1000))
    chunks = chunk_units([u(7, text, kind="стр.")], size=800, overlap=150)
    assert [c.loc for c in chunks] == ["стр. 7", "стр. 7"]
    assert chunks[0].text == text[:800]
    assert chunks[1].text == text[650:]
    assert all(len(c.text) <= 800 for c in chunks)


def test_long_unit_flushes_pending_buffer_first():
    chunks = chunk_units([u(1, "short"), u(2, "z" * 900)], size=800, overlap=100)
    assert chunks[0] == Chunk("a.docx", "абз. 1", "short")
    assert all(c.loc == "абз. 2" for c in chunks[1:])
