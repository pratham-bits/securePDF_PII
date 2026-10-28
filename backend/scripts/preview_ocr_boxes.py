from pathlib import Path

import pymupdf

from app.pipeline.locate import find_pii
from app.pipeline.ocr import extract_words_ocr

SCANNED = Path(__file__).resolve().parents[2] / "samples" / "sample_scanned_en.pdf"
OUT = Path(__file__).resolve().parents[1] / "storage" / "preview_ocr_boxes.pdf"

words = extract_words_ocr(SCANNED)
findings = find_pii(words)

with pymupdf.open(SCANNED) as doc:
    for f in findings:
        for b in f.boxes:
            rect = pymupdf.Rect(b.x0, b.y0, b.x1, b.y1)
            doc[b.page].draw_rect(rect, color=(1, 0, 0), width=1)
        print(f.detection.entity_type, f.detection.score, f"{len(f.boxes)} box(es)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)

confs = [w.conf for w in words if w.conf is not None]
mean_conf = sum(confs) / len(confs) if confs else 0.0
print(f"OCR words: {len(words)}, mean confidence: {mean_conf:.1f}")
print(f"saved {OUT}")
