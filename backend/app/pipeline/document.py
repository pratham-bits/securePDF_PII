from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.pipeline.extract import Word, extract_page_words, open_pdf
from app.pipeline.locate import Box
from app.pipeline.ocr import OCR_DPI, ocr_page, preprocess, render_page
from app.pipeline.redact import verify_redaction

MIN_TEXT_WORDS = 5  # fewer words than this on a page means "treat it as a scan"
MIN_LEAK_CONF = 50  # junk that OCR reads on black boxes scored 22-31 in our samples
LEAK_OVERLAP = 0.5  # a word counts as a leak if this much of it lies inside a box


@dataclass
class Extraction:
    words: list[Word]
    modes: list[str]  # one entry per page: "digital" or "ocr"


def extract_document(source: str | Path | bytes, lang: str = "eng") -> Extraction:
    words: list[Word] = []
    modes: list[str] = []
    with open_pdf(source) as doc:
        for number, page in enumerate(doc):
            page_words = extract_page_words(page, number)
            if len(page_words) >= MIN_TEXT_WORDS:
                modes.append("digital")
            else:
                image = preprocess(render_page(page))
                page_words = ocr_page(image, number, OCR_DPI, lang)
                modes.append("ocr")
            words.extend(page_words)
    return Extraction(words, modes)


def inside_fraction(word: Word, box: Box) -> float:
    """Share of the word's area that lies inside the box (0 to 1)."""
    ix = max(0.0, min(word.x1, box.x1) - max(word.x0, box.x0))
    iy = max(0.0, min(word.y1, box.y1) - max(word.y0, box.y0))
    area = (word.x1 - word.x0) * (word.y1 - word.y0)
    return (ix * iy) / area if area > 0 else 0.0


_inside_fraction = inside_fraction  # alias for backward compatibility

def _could_be_leaked_text(word: Word) -> bool:
    return (word.conf or 0) >= MIN_LEAK_CONF and any(c.isalnum() for c in word.text)

def _ocr_leaks(source: str | Path | bytes, boxes: list[Box], lang: str) -> list[Box]:
    """Re-OCR the saved file; a confident word inside a box means a leak."""
    surviving: dict[int, list[Word]] = {}
    with open_pdf(source) as doc:
        for page_number in sorted({b.page for b in boxes}):
            image = preprocess(render_page(doc[page_number]))
            words = ocr_page(image, page_number, OCR_DPI, lang)
            surviving[page_number] = [w for w in words if _could_be_leaked_text(w)]
        return [
            b for b in boxes
            if any(inside_fraction(w, b) >= LEAK_OVERLAP for w in surviving.get(b.page, []))
        ]


def verify_output(
    source: str | Path | bytes, boxes: list[Box], modes: list[str], lang: str = "eng"
) -> list[Box]:
    """Check the saved file: text check on digital pages, OCR check on scans."""
    digital = [b for b in boxes if modes[b.page] == "digital"]
    scanned = [b for b in boxes if modes[b.page] == "ocr"]
    leaks = verify_redaction(source, digital)
    if scanned:
        leaks += _ocr_leaks(source, scanned, lang)
    return leaks


__all__ = [
    "Extraction",
    "extract_document",
    "verify_output",
    "inside_fraction",
    "_inside_fraction",
]
