"""Make samples/sample_scanned_hi.pdf: a Hindi and English page that looks scanned.

Needs a Devanagari font file and Pillow built with libraqm (it shapes the
letters). Usage, from the repo root:

    python ml/data_gen/make_hindi_sample.py path/to/DevanagariFont.ttf
"""

import io
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

ROOT = Path(__file__).resolve().parents[2]
FONT = sys.argv[1]
OUT = ROOT / "samples" / "sample_scanned_hi.pdf"
DPI = 200

if not features.check("raqm"):
    sys.exit("Pillow needs libraqm to shape Devanagari text")

LINES = [
    "किराया समझौता",
    "",
    "यह समझौता श्री राहुल वर्मा (मकान मालिक) और श्रीमती अनीता शर्मा (किरायेदार) के बीच हुआ है।",
    "पैन: ABCDE1234F",
    "आधार: २३४५ ६७८९ ०१२३",
    "फोन: +91 98765 43210    ईमेल: rahul.verma@example.com",
    "पता: १२/४ स्टेशन रोड, पटना, बिहार ८००००१",
    "बैंक खाता: 123456789012 (IFSC: SBIN0001234)",
]
W, H = int(8.27 * DPI), int(11.69 * DPI)
img = Image.new("L", (W, H), 255)
draw = ImageDraw.Draw(img)
font = ImageFont.truetype(FONT, int(11 * DPI / 72 * 1.25), layout_engine=ImageFont.Layout.RAQM)
y = int(72 * DPI / 72)
for line in LINES:
    draw.text((int(72 * DPI / 72), y), line, font=font, fill=0)
    y += int(18 * DPI / 72 * 1.25)
img = img.rotate(1.0, resample=Image.Resampling.BICUBIC, fillcolor=255).filter(ImageFilter.GaussianBlur(0.6))
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=60)
with pymupdf.open() as out:
    page = out.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=buf.getvalue())
    out.save(OUT)
print(f"saved {OUT}")