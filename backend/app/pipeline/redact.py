from pathlib import Path

import pymupdf

from app.pipeline.extract import open_pdf
from app.pipeline.locate import Box

PAD = 1.0  # points of padding so glyph edges are fully covered
PDF_REDACT_IMAGE_PIXELS = 2  # blank out overlapping image pixels (default in PyMuPDF)


def _apply_redactions(doc: pymupdf.Document, boxes: list[Box]) -> None:
    # Flatten form fields and annotations first. Left alone, a fillable field
    # keeps its value and a comment keeps its text after redaction. As plain page
   # content they are redacted like any other text, and the hidden data is gone.
    doc.bake(annots=True, widgets=True)
    for box in boxes:
        rect = pymupdf.Rect(box.x0 - PAD, box.y0 - PAD, box.x1 + PAD, box.y1 + PAD)
        doc[box.page].add_redact_annot(rect, fill=(0, 0, 0))
    for page in doc:
        page.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)
    doc.scrub()  # metadata, attachments, hidden text, javascript, thumbnails


def redact_pdf(src: "str | Path | bytes", dst: "str | Path", boxes: list[Box]) -> None:
    """Remove the content under each box and write a scrubbed copy to dst."""
    with open_pdf(src) as doc:
        _apply_redactions(doc, boxes)
        doc.save(dst, garbage=4, deflate=True)


def redact_bytes(data: bytes, boxes: list[Box]) -> bytes:
    """Redact in memory: the redacted file never touches the disk unencrypted."""
    with open_pdf(data) as doc:
        _apply_redactions(doc, boxes)
        return doc.tobytes(garbage=4, deflate=True)


def verify_redaction(source: "str | Path | bytes", boxes: list[Box]) -> list[Box]:
    """Re-read the saved file; return the boxes where text is still extractable."""
    leaks: list[Box] = []
    with open_pdf(source) as doc:
        for box in boxes:
            m = min(1.0, (box.x1 - box.x0) / 4, (box.y1 - box.y0) / 4)
            clip = pymupdf.Rect(box.x0 + m, box.y0 + m, box.x1 - m, box.y1 - m)
            if doc[box.page].get_text("words", clip=clip):
                leaks.append(box)
    return leaks
