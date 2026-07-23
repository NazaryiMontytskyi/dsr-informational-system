from fastapi import HTTPException
from fastapi.responses import Response

from app.services.pdf import order_docx_to_pdf_bytes, regulation_docx_to_pdf_bytes


def _respond(pdf_bytes_factory) -> Response:
    try:
        pdf_bytes = pdf_bytes_factory()
    except RuntimeError as exc:
        raise HTTPException(503, f"Не вдалося сформувати PDF: {exc}") from exc
    return Response(pdf_bytes, media_type="application/pdf")


def order_pdf_response(doc) -> Response:
    return _respond(lambda: order_docx_to_pdf_bytes(doc))


def regulation_pdf_response(doc) -> Response:
    return _respond(lambda: regulation_docx_to_pdf_bytes(doc))
