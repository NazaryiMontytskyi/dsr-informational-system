"""
PDF-подання наказів і Положення про гурток.

Пряма конвертація вже заповненого .docx у PDF через headless
LibreOffice (app.services.docx_convert). У production (Linux-контейнер,
див. Dockerfile) це дає результат, візуально ідентичний офіційному
.docx -- той самий рушій верстки, без жодного власного/проміжного
рендера, що міг би спотворити документ.
"""

from __future__ import annotations

from io import BytesIO

from app.services.docx_convert import convert_docx_bytes_to_pdf


def docx_to_bytes(doc) -> bytes:
    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def order_docx_to_pdf_bytes(doc) -> bytes:
    return convert_docx_bytes_to_pdf(docx_to_bytes(doc))


def regulation_docx_to_pdf_bytes(doc) -> bytes:
    return convert_docx_bytes_to_pdf(docx_to_bytes(doc))
