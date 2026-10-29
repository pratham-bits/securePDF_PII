from pathlib import Path

import pymupdf

from app.pipeline.locate import Box

PAD = 1.0  # points of padding so glyph edges are fully covered
PDF_REDACT_IMAGE_PIXELS = 2  # blank out overlapping image pixels (default in PyMuPDF)


def redact_pdf(src: str | Path, dst: str | Path, boxes: list[Box]) -> None:
    """Remove the content under each box and write a scrubbed copy to dst."""
    with pymupdf.open(src) as doc:
        for box in boxes:
            rect = pymupdf.Rect(
                box.x0 - PAD, box.y0 - PAD, box.x1 + PAD, box.y1 + PAD
            )
            doc[box.page].add_redact_annot(rect, fill=(0, 0, 0))
        for page in doc:
            page.apply_redactions(images=PDF_REDACT_IMAGE_PIXELS)
        doc.scrub()  # metadata, attachments, hidden text, javascript, thumbnails
        doc.save(dst, garbage=4, deflate=True)


def verify_redaction(path: str | Path, boxes: list[Box]) -> list[Box]:
    """Re-read the saved file; return the boxes where text is still extractable."""
    leaks: list[Box] = []
    with pymupdf.open(path) as doc:
        for box in boxes:
            m = min(1.0, (box.x1 - box.x0) / 4, (box.y1 - box.y0) / 4)
            clip = pymupdf.Rect(box.x0 + m, box.y0 + m, box.x1 - m, box.y1 - m)
            if doc[box.page].get_text("words", clip=clip):
                leaks.append(box)
    return leaks
