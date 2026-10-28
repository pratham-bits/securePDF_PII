from pathlib import Path

import pymupdf

from app.pipeline.extract import extract_words
from app.pipeline.locate import find_pii

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"
OUT = Path(__file__).resolve().parents[1] / "storage" / "preview_boxes.pdf"

findings = find_pii(extract_words(SAMPLE))

with pymupdf.open(SAMPLE) as doc:
    for f in findings:
        for b in f.boxes:
            rect = pymupdf.Rect(b.x0, b.y0, b.x1, b.y1)
            doc[b.page].draw_rect(rect, color=(1, 0, 0), width=1)
        # Log types and counts only, never the detected text itself.
        print(f.detection.entity_type, f.detection.score, f"{len(f.boxes)} box(es)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)

print(f"saved {OUT}")