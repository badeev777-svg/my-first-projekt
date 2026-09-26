from io import BytesIO

import docx
from fpdf import FPDF


def make_pdf(pages: list[str]) -> bytes:
    """ASCII-only: встроенный шрифт fpdf не поддерживает кириллицу."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for text in pages:
        pdf.add_page()
        if text:
            pdf.cell(text=text)
    return bytes(pdf.output())


def make_docx(paragraphs: list[str]) -> bytes:
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buf = BytesIO()
    document.save(buf)
    return buf.getvalue()
