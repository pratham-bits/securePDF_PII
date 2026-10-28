from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parents[2] / "samples" / "sample_digital_en.pdf"

LINES = [
    "RENT AGREEMENT",
    "",
    "This agreement is made between Mr. Rahul Verma (Landlord) and Ms. Anita Sharma (Tenant).",
    "Landlord PAN: ABCDE1234F",
    "Landlord Aadhaar: 2345 6789 0123",
    "Phone: +91 98765 43210    Email: rahul.verma@example.com",
    "Address: 12/4 Station Road, Patna, Bihar 800001",
    "Bank account: 123456789012 (IFSC: SBIN0001234)",
]

doc = pymupdf.open()
page = doc.new_page()
y = 72
for line in LINES:
    page.insert_text((72, y), line, fontsize=11)
    y += 18

OUT.parent.mkdir(exist_ok=True)
doc.save(OUT)
print(f"saved {OUT}")