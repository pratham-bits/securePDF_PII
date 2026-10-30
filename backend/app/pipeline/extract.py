from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass
class Word:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float | None = None  # OCR confidence 0-100; None for digital text


def open_pdf(source: str | Path | bytes) -> pymupdf.Document:
    """Open a PDF from a path or from bytes held in memory (nothing written to disk)."""
    if isinstance(source, bytes):
        return pymupdf.open(stream=source, filetype="pdf")
    return pymupdf.open(source)


def extract_page_words(page: pymupdf.Page, page_number: int) -> list[Word]:
    return [
        Word(
            page=page_number,
            text=str(text),
            x0=float(x0),
            y0=float(y0),
            x1=float(x1),
            y1=float(y1),
        )
        for x0, y0, x1, y1, text, *_ in page.get_text("words")
    ]


def extract_words(pdf_path: str | Path) -> list[Word]:
    """Return every word in the PDF with its page number and bounding box."""
    words: list[Word] = []
    with open_pdf(pdf_path) as doc:
        for page_number, page in enumerate(doc):
            words.extend(extract_page_words(page, page_number))
    return words
