from pathlib import Path

from app.pipeline.document import extract_document, verify_output
from app.pipeline.locate import find_pii
from app.pipeline.redact import redact_pdf

SAMPLES = Path(__file__).resolve().parents[2] / "samples"
OUT_DIR = Path(__file__).resolve().parents[1] / "storage"
OUT_DIR.mkdir(parents=True, exist_ok=True)

for name in ["sample_digital_en.pdf", "sample_scanned_en.pdf"]:
    src = SAMPLES / name
    extraction = extract_document(src)
    findings = find_pii(extraction.words)
    boxes = [b for f in findings for b in f.boxes]
    out = OUT_DIR / f"redacted_{name}"
    redact_pdf(src, out, boxes)
    leaks = verify_output(out, boxes, extraction.modes)
    print(
        f"{name}: modes={extraction.modes}, findings={len(findings)}, "
        f"boxes={len(boxes)}, leaks={len(leaks)}"
    )
    print(f"  saved {out}")