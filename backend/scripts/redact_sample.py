from pathlib import Path

from app.pipeline.extract import extract_words
from app.pipeline.locate import find_pii
from app.pipeline.redact import redact_pdf, verify_redaction

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"
OUT = Path(__file__).resolve().parents[1] / "storage" / "redacted_sample.pdf"

boxes = [b for f in find_pii(extract_words(SAMPLE)) for b in f.boxes]
OUT.parent.mkdir(parents=True, exist_ok=True)
redact_pdf(SAMPLE, OUT, boxes)
leaks = verify_redaction(OUT, boxes)
print(f"redacted {len(boxes)} box(es); leaks found: {len(leaks)}")
print(f"saved {OUT}")