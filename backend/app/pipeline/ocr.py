from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

from app.pipeline.extract import Word

OCR_DPI = 300  # Tesseract works best at roughly 300 DPI


def render_page(
    page: pymupdf.Page, dpi: int = OCR_DPI, clip: pymupdf.Rect | None = None
) -> Image.Image:
    """Render a page, or only the `clip` region of it, to an image."""
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def preprocess(image: Image.Image) -> Image.Image:
    """Grayscale and stretch contrast. Heavier cleanup comes later, if needed."""
    return ImageOps.autocontrast(image.convert("L"))


def ocr_page(
    image: Image.Image, page_number: int, dpi: int = OCR_DPI, lang: str = "eng"
) -> list[Word]:
    data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)
    scale = 72.0 / dpi  # pixels -> PDF points
    words: list[Word] = []
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:  # conf is -1 for layout rows that are not words
            continue
        left, top = data["left"][i], data["top"][i]
        width, height = data["width"][i], data["height"][i]
        words.append(
            Word(
                page_number,
                text,
                left * scale,
                top * scale,
                (left + width) * scale,
                (top + height) * scale,
                conf,
            )
        )
    return words


def extract_words_ocr(
    pdf_path: str | Path, lang: str = "eng", dpi: int = OCR_DPI
) -> list[Word]:
    words: list[Word] = []
    with pymupdf.open(pdf_path) as doc:
        for page_number, page in enumerate(doc):
            image = preprocess(render_page(page, dpi))
            words.extend(ocr_page(image, page_number, dpi, lang))
    return words