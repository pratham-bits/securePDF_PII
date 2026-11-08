"""Generate a labelled synthetic set for the ML phase (names, addresses, organisations, dates).

Every document is built piece by piece, so each entity span is exact by construction.
Run:  python ml/data_gen/make_synthetic_ner.py          -> ml/data/synthetic_v1.jsonl
All people, addresses and organisations are invented. No real personal data is used.
"""

import json
import random
from pathlib import Path

SEED = 42
DOCS_PER_COMBO = 40  # per (doc type, language): 3 types x 2 languages x 40 = 240 documents

# (English, Devanagari) pairs, so both languages describe the same invented people.
FIRST = [("Ramesh", "रमेश"), ("Sunita", "सुनीता"), ("Amit", "अमित"), ("Priya", "प्रिया"),
         ("Rajesh", "राजेश"), ("Anita", "अनीता"), ("Vikram", "विक्रम"), ("Neha", "नेहा"),
         ("Suresh", "सुरेश"), ("Kavita", "कविता"), ("Manoj", "मनोज"), ("Pooja", "पूजा"),
         ("Deepak", "दीपक"), ("Meena", "मीना"), ("Arjun", "अर्जुन"), ("Sanjay", "संजय")]
LAST = [("Kumar", "कुमार"), ("Singh", "सिंह"), ("Sharma", "शर्मा"), ("Verma", "वर्मा"),
        ("Gupta", "गुप्ता"), ("Yadav", "यादव"), ("Mishra", "मिश्रा"), ("Prasad", "प्रसाद"),
        ("Das", "दास"), ("Mahto", "महतो"), ("Jha", "झा"), ("Pandey", "पांडेय")]
LOCALITY = [("Shanti Nagar", "शांति नगर"), ("Gandhi Road", "गांधी रोड"),
            ("Lake View Colony", "लेक व्यू कॉलोनी"), ("Station Road", "स्टेशन रोड"),
            ("Ram Nagar", "राम नगर"), ("Civil Lines", "सिविल लाइंस")]
CITY = [("Dhanbad", "धनबाद", "Jharkhand", "झारखंड"), ("Ranchi", "रांची", "Jharkhand", "झारखंड"),
        ("Patna", "पटना", "Bihar", "बिहार"), ("Lucknow", "लखनऊ", "Uttar Pradesh", "उत्तर प्रदेश"),
        ("Jaipur", "जयपुर", "Rajasthan", "राजस्थान"), ("Pune", "पुणे", "Maharashtra", "महाराष्ट्र")]
ORG = [("Bharat Textiles Pvt Ltd", "भारत टेक्सटाइल्स प्रा. लि."),
       ("Sharma and Sons Traders", "शर्मा एंड संस ट्रेडर्स"),
       ("City Care Hospital", "सिटी केयर हॉस्पिटल"),
       ("Eastern Coal Services Ltd", "ईस्टर्न कोल सर्विसेज लि."),
       ("Sunrise Public School", "सनराइज पब्लिक स्कूल"),
       ("Apex Infra Solutions LLP", "एपेक्स इन्फ्रा सॉल्यूशंस एलएलपी")]
MONTH = [("January", "जनवरी"), ("February", "फरवरी"), ("March", "मार्च"), ("April", "अप्रैल"),
         ("May", "मई"), ("June", "जून"), ("July", "जुलाई"), ("August", "अगस्त"),
         ("September", "सितंबर"), ("October", "अक्टूबर"), ("November", "नवंबर"),
         ("December", "दिसंबर")]
NOISE_EN = ["The parties agree to the terms set out below.", "This statement is system generated.",
            "Please retain this document for your records.", "All amounts are in Indian Rupees."]
NOISE_HI = ["पक्षकार नीचे दी गई शर्तों से सहमत हैं।", "यह विवरण कंप्यूटर द्वारा बनाया गया है।",
            "कृपया इस दस्तावेज़ को अपने रिकॉर्ड में रखें।", "सभी राशियाँ भारतीय रुपये में हैं।"]
DEVANAGARI_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


class Doc:
    """Builds text and records the exact span of every entity added."""

    def __init__(self, lang):
        self.lang, self.parts, self.ents, self.pos = lang, [], [], 0

    def t(self, text):
        self.parts.append(text)
        self.pos += len(text)
        return self

    def e(self, label, text):
        self.ents.append({"label": label, "start": self.pos, "end": self.pos + len(text), "text": text})
        return self.t(text)

    def result(self, doc_id, doc_type):
        return {"id": doc_id, "doc_type": doc_type, "lang": self.lang,
                "text": "".join(self.parts), "entities": self.ents}


class Maker:
    def __init__(self, rng, lang):
        self.r, self.lang, self.i = rng, lang, (0 if lang == "en" else 1)

    def person(self, honorific=True):
        f, l = self.r.choice(FIRST), self.r.choice(LAST)
        name = f"{f[self.i]} {l[self.i]}"
        if self.r.random() < 0.3:  # sometimes with a middle name
            name = f"{f[self.i]} {self.r.choice(FIRST)[self.i]} {l[self.i]}"
        if honorific and self.r.random() < 0.4:
            name = ("Mr. " if self.lang == "en" else "श्री ") + name
        return name

    def address(self):
        c = self.r.choice(CITY)
        city, state = (c[0], c[2]) if self.i == 0 else (c[1], c[3])
        pin = str(self.r.randint(800000, 842999))
        flat = f"{self.r.choice(['Flat', 'House No.']) if self.i == 0 else self.r.choice(['फ्लैट', 'मकान नं.'])} {self.r.randint(1, 99)}"
        text = f"{flat}, {self.r.choice(LOCALITY)[self.i]}, {city}, {state} {pin}"
        return text.translate(DEVANAGARI_DIGITS) if self.i and self.r.random() < 0.3 else text

    def org(self):
        return self.r.choice(ORG)[self.i]

    def date(self):
        d, m, y = self.r.randint(1, 28), self.r.randint(1, 12), self.r.randint(1995, 2026)
        if self.r.random() < 0.5:
            text = f"{d:02d}/{m:02d}/{y}"
        else:
            text = f"{d} {MONTH[m - 1][self.i]} {y}"
        return text.translate(DEVANAGARI_DIGITS) if self.i and self.r.random() < 0.3 else text

    def noise(self):
        return self.r.choice(NOISE_EN if self.i == 0 else NOISE_HI)


def legal(m, n):
    d = Doc(m.lang)
    en = m.lang == "en"
    d.t("RENT AGREEMENT\n" if en else "किराया अनुबंध\n")
    d.t("This agreement is made on " if en else "यह अनुबंध दिनांक ").e("DATE", m.date())
    d.t(" between " if en else " को ").e("PERSON", m.person())
    d.t(", residing at " if en else ", निवासी ").e("ADDRESS", m.address())
    d.t(", and " if en else ", और ").e("PERSON", m.person())
    d.t(", director of " if en else ", निदेशक, ").e("ORGANIZATION", m.org())
    d.t(".\n" + m.noise() + "\n")
    d.t("Signed by " if en else "हस्ताक्षरकर्ता: ").e("PERSON", m.person(False))
    d.t(" on " if en else " दिनांक ").e("DATE", m.date()).t(".\n")
    return d.result(f"legal-{m.lang}-{n}", "legal")


def id_card(m, n):
    d = Doc(m.lang)
    en = m.lang == "en"
    d.t("Name: " if en else "नाम: ").e("PERSON", m.person(False))
    d.t("\nFather's Name: " if en else "\nपिता का नाम: ").e("PERSON", m.person(False))
    d.t("\nDate of Birth: " if en else "\nजन्म तिथि: ").e("DATE", m.date())
    d.t("\nAddress: " if en else "\nपता: ").e("ADDRESS", m.address())
    d.t("\nIssued by: " if en else "\nजारीकर्ता: ").e("ORGANIZATION", m.org())
    d.t("\n")
    return d.result(f"idcard-{m.lang}-{n}", "id_card")


def bank_statement(m, n):
    d = Doc(m.lang)
    en = m.lang == "en"
    d.t("Account Holder: " if en else "खाताधारक: ").e("PERSON", m.person())
    d.t("\nAddress: " if en else "\nपता: ").e("ADDRESS", m.address())
    d.t("\nEmployer: " if en else "\nनियोक्ता: ").e("ORGANIZATION", m.org())
    d.t("\nStatement period: " if en else "\nविवरण अवधि: ").e("DATE", m.date())
    d.t(" to " if en else " से ").e("DATE", m.date()).t("\n" + m.noise() + "\n")
    for _ in range(m.r.randint(3, 5)):
        d.e("DATE", m.date()).t("  UPI/" if en else "  यूपीआई/")
        d.e("PERSON", m.person(False)).t(f"  {m.r.randint(100, 90000):,}.00\n")
    return d.result(f"bank-{m.lang}-{n}", "bank_statement")


def generate():
    rng = random.Random(SEED)
    docs = []
    for lang in ("en", "hi"):
        m = Maker(rng, lang)
        for build in (legal, id_card, bank_statement):
            docs += [build(m, n) for n in range(DOCS_PER_COMBO)]
    return docs


def main():
    out = Path(__file__).resolve().parents[1] / "data" / "synthetic_v1.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    docs = generate()
    out.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in docs) + "\n", encoding="utf-8")
    counts = {}
    for d in docs:
        for e in d["entities"]:
            counts[e["label"]] = counts.get(e["label"], 0) + 1
    print(f"wrote {len(docs)} documents to {out}")
    print("entities:", counts)


if __name__ == "__main__":
    main()