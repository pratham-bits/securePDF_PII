"""Render the 32 invented documents in realistic_docs.py as PDFs, plus exact labels.

  python ml/data_gen/make_realistic_docs.py --font C:\\Windows\\Fonts\\mangal.ttf

Digital English documents keep a real text layer. Every other document (all Hindi, and the
English ones marked scan) is rendered, then degraded (slight rotation, blur, noise, JPEG) and
saved as an image-only PDF, so it has to be read by OCR like a real scan.

Hindi is delivered as scans only: a PDF text layer written for Devanagari by this route is not
reliable, so digital Hindi is not covered here.

Output goes to ml/real/ (gitignored): <name>.pdf files and labels.txt. Fake data only.
"""

import argparse
import io
import random
import shutil
import sys
import tempfile
from pathlib import Path

import pymupdf
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))

from realistic_docs import DOCS, split_markers  # noqa: E402

ML = Path(__file__).resolve().parents[1]
FONT_CANDIDATES = [
    "C:/Windows/Fonts/mangal.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
]
SCAN_DPI = 300

CSS = """
@font-face { font-family: dev; src: url(dev.ttf); }
body { font-family: %(body)s; font-size: 10.5pt; color: #111; }
.letter { font-family: %(serif)s; font-size: 11pt; line-height: 1.5; }
.form, .cardpage { font-size: 10.5pt; }
.head { font-size: 11.5pt; border-bottom: 1px solid #444; padding-bottom: 4px; margin-bottom: 8px; }
.card { border: 2px solid #333; padding: 10px; margin: 20px 0; }
.ctitle { font-weight: bold; font-size: 12pt; margin-bottom: 8px; }
.mono { font-family: %(mono)s; font-size: 9pt; }
table { width: 100%%; border-collapse: collapse; margin: 8px 0; }
th { text-align: left; padding: 3px 6px; }
.kv th { width: 140pt; font-weight: bold; }
.kv td, .kv th { border: 1px solid #999; padding: 4px 6px; }
.grid td, .grid th { border: 1px solid #777; padding: 3px 5px; }
h1 { text-align: center; font-size: 16pt; } h2 { font-size: 13pt; }
"""


def find_font(explicit):
    for candidate in ([explicit] if explicit else []) + FONT_CANDIDATES:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def render_digital(html, hindi, font_dir):
    families = {"body": "dev" if hindi else "sans-serif", "serif": "dev" if hindi else "serif",
                "mono": "dev" if hindi else "monospace"}
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    spare, _scale = page.insert_htmlbox(
        pymupdf.Rect(50, 50, 545, 792), html, css=CSS % families, archive=pymupdf.Archive(str(font_dir))
    )
    if spare < 0:
        raise RuntimeError("document does not fit on one page")
    return doc


def degrade(page, rng):
    """Rasterise a page and make it look like a mediocre scan. Returns JPEG bytes."""
    pix = page.get_pixmap(dpi=SCAN_DPI)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    image = image.rotate(rng.uniform(-0.8, 0.8), resample=Image.Resampling.BICUBIC, fillcolor=255)
    image = image.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.6)))
    noise = Image.frombytes("L", image.size, rng.randbytes(image.width * image.height))
    image = Image.blend(image, noise, 0.03)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=rng.randint(65, 80))
    return buffer.getvalue()


def to_scan(digital, seed):
    out = pymupdf.open()
    page = out.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=degrade(digital[0], random.Random(seed)))
    return out


def labels_block(spec, entities):
    lines = [f"== {spec.name} | {spec.doc_type} | {spec.lang}"]
    for label in ("PERSON", "ADDRESS", "ORGANIZATION", "DATE"):
        values = list(dict.fromkeys(v for l, v in entities if l == label))
        if any(";" in v for v in values):
            raise ValueError(f"{spec.name}: a value contains ';'")
        lines.append(f"{label}: " + " ; ".join(values))
    return "\n".join(lines)


def generate(out_dir, font=None, force=False):
    out_dir = Path(out_dir)
    labels_file = out_dir / "labels.txt"
    if labels_file.exists() and not force:
        raise SystemExit(f"{labels_file} already exists. Use --force to replace it.")
    out_dir.mkdir(parents=True, exist_ok=True)
    font_path = find_font(font)
    blocks, written, skipped = [], 0, []
    with tempfile.TemporaryDirectory() as tmp:
        if font_path:
            shutil.copy(font_path, Path(tmp) / "dev.ttf")
        for spec in DOCS:
            hindi = spec.lang == "hi"
            if hindi and not font_path:
                skipped.append(spec.name)
                continue
            html, entities = split_markers(spec.html)
            digital = render_digital(html, hindi, tmp)
            final = to_scan(digital, seed=spec.name) if (spec.scan or hindi) else digital
            final.save(out_dir / f"{spec.name}.pdf")
            blocks.append(labels_block(spec, entities))
            written += 1
    labels_file.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print(f"wrote {written} PDFs and {labels_file}")
    if skipped:
        print(f"skipped {len(skipped)} Hindi documents: no Devanagari font found (use --font)")
    return written, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=None, help="a Devanagari .ttf file (not .ttc); mangal.ttf on Windows")
    ap.add_argument("--out", default=str(ML / "real"))
    ap.add_argument("--force", action="store_true", help="replace an existing labels.txt")
    a = ap.parse_args()
    generate(a.out, a.font, a.force)


if __name__ == "__main__":
    main()
