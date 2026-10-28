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


def extract_words(pdf_path: str | Path) -> list[Word]:
    """Return every word in the PDF with its page number and bounding box."""
    words: list[Word] = []
    with pymupdf.open(pdf_path) as doc:
        for page_number, page in enumerate(doc):
            for x0, y0, x1, y1, text, *_ in page.get_text("words"):
                words.append(
                    Word(
                        page=page_number,
                        text=str(text),
                        x0=float(x0),
                        y0=float(y0),
                        x1=float(x1),
                        y1=float(y1),
                    )
                )
    return words
