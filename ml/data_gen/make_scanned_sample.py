import io
from pathlib import Path

import pymupdf
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "samples" / "sample_digital_en.pdf"
OUT = ROOT / "samples" / "sample_scanned_en.pdf"
DPI = 200


def degrade(img: Image.Image) -> Image.Image:
    """Mimic a mediocre scan: grayscale, slight tilt, soft blur."""
    img = img.convert("L")
    img = img.rotate(1.0, resample=Image.Resampling.BICUBIC, fillcolor=255)
    return img.filter(ImageFilter.GaussianBlur(0.6))


with pymupdf.open(SRC) as src, pymupdf.open() as out:
    for page in src:
        pix = page.get_pixmap(dpi=DPI)
        img = degrade(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=buf.getvalue())
    out.save(OUT)

print(f"saved {OUT}")
