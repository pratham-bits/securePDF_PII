"""The content of 32 invented documents: legal papers, ID cards and forms, bank documents.

Everything here is made up: people, addresses, organisations and numbers. Names, addresses,
organisations and dates are wrapped in markers so the labels are exact:
    [[P:name]]  person      [[A:address]]  address      [[O:org]]  organisation      [[D:date]]  date
Honorifics (Mr., श्री) stay outside the marker: they are not personal data.
Numbers such as PAN, phone and e-mail are left unmarked on purpose: other rules own them.
"""

import re
from dataclasses import dataclass

MARKER = re.compile(r"\[\[([PAOD]):(.+?)\]\]")
LABEL_OF = {"P": "PERSON", "A": "ADDRESS", "O": "ORGANIZATION", "D": "DATE"}


@dataclass(frozen=True)
class Spec:
    name: str       # file name without .pdf; the prefix tells the document type
    doc_type: str   # legal | id_card | bank_statement
    lang: str       # en | hi
    scan: bool      # True: delivered as a degraded scan (image only, so OCR is needed)
    html: str


def P(x): return f"[[P:{x}]]"
def A(x): return f"[[A:{x}]]"
def O(x): return f"[[O:{x}]]"
def D(x): return f"[[D:{x}]]"


def p(text): return f"<p>{text}</p>"
def h(text, n=1): return f"<h{n}>{text}</h{n}>"
def kv(rows): return "<table class='kv'>" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"
def tbl(head, rows):
    top = "".join(f"<th>{c}</th>" for c in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='grid'><tr>{top}</tr>{body}</table>"


DOCS: list[Spec] = []


def add(name, doc_type, lang, scan, *parts, cls="letter"):
    DOCS.append(Spec(name, doc_type, lang, scan, f"<div class='{cls}'>" + "".join(parts) + "</div>"))


# ============================== LEGAL ==============================
add("legal_01", "legal", "en", False,
    h("RENT AGREEMENT"),
    p(f"This Rent Agreement is executed on {D('12th March 2024')} between Mr. {P('Arvind Narayanan Iyer')}, "
      f"residing at {A('45, 2nd Cross, Indiranagar, Bengaluru, Karnataka 560038')} (hereinafter the Landlord) and "
      f"Ms. {P('Meenakshi Subramanian')}, presently residing at {A('B-204, Shivalik Heights, Baner Road, Pune, Maharashtra 411045')} "
      f"(hereinafter the Tenant)."),
    p(f"1. The Landlord lets the first floor of the premises at {A('45, 2nd Cross, Indiranagar, Bengaluru, Karnataka 560038')} "
      f"to the Tenant for eleven months from {D('01/04/2024')} to {D('28/02/2025')} at a monthly rent of Rs. 28,000."),
    p(f"2. The Tenant shall pay a refundable deposit of Rs. 84,000. Maintenance is payable to {O('Indiranagar Residents Welfare Association')}."),
    p(f"Witnesses: 1. {P('Kiran Rao')}  2. {P('Sheikh Abdul Rahim')}.   Landlord PAN: ABCPI4321K   Phone: 98450 11223"))

add("legal_02", "legal", "en", False,
    h("AFFIDAVIT"),
    p(f"I, {P('Gurpreet Singh Sandhu')}, son of {P('Harbhajan Singh Sandhu')}, aged 41 years, resident of "
      f"{A('House No. 221, Model Town, Ludhiana, Punjab 141002')}, do hereby solemnly affirm and declare as under:"),
    p(f"1. That I am employed with {O('Kaveri Textiles Pvt Ltd')} as a Senior Manager since {D('15 June 2016')}."),
    p(f"2. That my name was wrongly recorded as \"Gurpeet Singh\" in the school certificate issued by {O('Government Senior Secondary School, Model Town')} "
      f"on {D('30 April 1999')}, and that both names refer to one and the same person."),
    p(f"Deponent: {P('Gurpreet Singh Sandhu')}.  Sworn before me, Advocate {P('Navjot Kaur')}, Notary Public, on {D('2 February 2024')}."))

add("legal_03", "legal", "en", True,
    h("SALE DEED"),
    p(f"This Deed of Sale is made on this {D('8th day of August 2023')} BETWEEN {P('Debashish Chatterjee')}, son of late {P('Amalendu Chatterjee')}, "
      f"residing at {A('Flat 3C, Lakeview Apartments, Salt Lake, Kolkata, West Bengal 700091')} (the Vendor) AND "
      f"{P('Ritika Banerjee')}, wife of {P('Soumitra Banerjee')}, residing at {A('27/1, Hazra Road, Kolkata, West Bengal 700029')} (the Purchaser)."),
    p(f"The Vendor sells the property situated at {A('Plot 14, Sector III, Bidhannagar, Kolkata, West Bengal 700106')} for Rs. 62,50,000. "
      f"Possession was handed over on {D('21/08/2023')}."),
    p(f"Witness: {P('Tapan Kumar Dey')}    Witness: {P('Mousumi Sen')}"), cls="letter")

add("legal_04", "legal", "en", False,
    f"<div class='head'><b>{O('Orion Logistics Pvt Ltd')}</b><br>Registered Office: {A('Unit 7, Hosur Road Industrial Estate, Bengaluru, Karnataka 560068')}</div>",
    p(f"Date: {D('3 January 2024')}"),
    p(f"To,<br>{P('Lakshmi Priya Reddy')}<br>{A('Door No. 12-4-67, Gandhi Nagar, Vijayawada, Andhra Pradesh 520003')}"),
    p(f"Subject: Offer of Employment"),
    p(f"Dear {P('Lakshmi')},"),
    p(f"We are pleased to offer you the position of Operations Analyst at {O('Orion Logistics Pvt Ltd')}. Your date of joining will be {D('1 February 2024')} "
      f"and your annual compensation will be Rs. 7,20,000. Please confirm by replying to hr@orionlogistics.example."),
    p(f"Sincerely,<br>{P('Faisal Ahmed Khan')}<br>Head, Human Resources"))

add("legal_05", "legal", "en", False,
    h("LEGAL NOTICE"),
    p(f"Ref: LN/2024/118 &nbsp;&nbsp; Date: {D('18-Mar-2024')}"),
    p(f"To: {P('Sunil Kumar Mahto')}, {A('Village Rampur, Post Baliapur, Dhanbad, Jharkhand 828201')}."),
    p(f"Under instructions from my client {O('Damodar Coal Services Ltd')}, through its Director {P('Prakash Chandra Mohanty')}, "
      f"I hereby call upon you to repay the sum of Rs. 3,40,000 advanced to you on {D('5 September 2022')}, failing which proceedings shall be initiated against you."),
    p(f"Adv. {P('Shabnam Begum')}<br>Counsel for the Noticer<br>Chamber: {A('Room 12, Civil Court Complex, Dhanbad, Jharkhand 826001')}"))

add("legal_06", "legal", "en", False,
    h("LOAN AGREEMENT"),
    p(f"This agreement dated {D('2024-04-09')} is between {O('Punjab National Bank')}, Branch {A('Sector 17, Chandigarh 160017')} (the Lender) "
      f"and {P('Harleen Kaur')} of {A('SCO 45, Phase 7, Mohali, Punjab 160061')} (the Borrower)."),
    p(f"The Lender grants a personal loan of Rs. 5,00,000 repayable in 36 monthly instalments. {P('Jaspreet Singh Gill')} stands as guarantor "
      f"and has signed on {D('9 April 2024')}."),
    p("The Borrower's PAN is BKLPK8821Q and registered mobile number is 98765 43210."))

add("legal_07", "legal", "hi", True,
    h("किराया समझौता"),
    p(f"यह किराया समझौता दिनांक {D('१२ मार्च २०२४')} को श्री {P('रमेश चंद्र गुप्ता')}, निवासी {A('मकान नं. २२१/बी, कंकड़बाग कॉलोनी, पटना, बिहार ८००००२')} "
      f"(मकान मालिक) और श्रीमती {P('सुनीता देवी')}, निवासी {A('ग्राम रामपुर, पोस्ट बलियापुर, धनबाद, झारखंड ८२८२०१')} (किरायेदार) के बीच हुआ।"),
    p(f"मासिक किराया ८,००० रुपये होगा और सुरक्षा राशि १६,००० रुपये होगी। गवाह: {P('अजय कुमार सिंह')} और {P('प्रियंका कुमारी')}।"))

add("legal_08", "legal", "hi", True,
    h("शपथ पत्र"),
    p(f"मैं, {P('देवेंद्र प्रसाद यादव')}, पुत्र श्री {P('रामलखन यादव')}, उम्र ४५ वर्ष, निवासी {A('मोहल्ला शिवपुरी, गोरखपुर, उत्तर प्रदेश २७३००१')}, "
      f"शपथपूर्वक कथन करता हूँ कि मैं {O('हिमालय एग्रो इंडस्ट्रीज')} में दिनांक {D('१५ जून २०१६')} से कार्यरत हूँ।"),
    p(f"मेरा नाम स्कूल प्रमाण पत्र में गलती से {P('देवेन्द्र यादव')} लिखा गया है। दोनों नाम एक ही व्यक्ति के हैं।"),
    p(f"हस्ताक्षर: {P('देवेंद्र प्रसाद यादव')}   दिनांक: {D('२ फ़रवरी २०२४')}"))

add("legal_09", "legal", "hi", True,
    h("वसीयतनामा"),
    p(f"मैं {P('कविता शर्मा')}, पत्नी स्व. {P('राजेश शर्मा')}, निवासी {A('बी-१२, अशोक विहार, दिल्ली ११००५२')}, अपने पूरे होश-हवास में यह वसीयत लिखती हूँ।"),
    p(f"मेरी मृत्यु के बाद मेरा मकान मेरे पुत्र {P('अनिल कुमार शर्मा')} को और मेरे गहने मेरी पुत्री {P('पूजा वर्मा')} को मिलेंगे। "
      f"गवाह: {P('राकेश मिश्रा')}, {P('मीनाक्षी पांडेय')}। दिनांक {D('१० अक्टूबर २०२३')}।"))

add("legal_10", "legal", "hi", True,
    h("कानूनी नोटिस"),
    p(f"प्रेषक: अधिवक्ता {P('संजय कुमार महतो')}, कार्यालय: {A('कचहरी परिसर, कमरा नं. ८, रांची, झारखंड ८३४००१')}"),
    p(f"सेवा में, {P('मोहम्मद इरफान')}, {A('२३, उर्दू बाज़ार, लखनऊ, उत्तर प्रदेश २२६००३')}"),
    p(f"मेरे मुवक्किल {O('कावेरी टेक्सटाइल्स प्राइवेट लिमिटेड')} के निदेशक {P('अरविंद अय्यर')} के निर्देश पर आपको सूचित किया जाता है कि "
      f"दिनांक {D('५ सितंबर २०२२')} को दिए गए ३,४०,००० रुपये {D('३० अप्रैल २०२४')} तक लौटा दें।"))

DSOUZA = "Anjali Mary D'Souza"
add("legal_11", "legal", "en", True,
    h("GENERAL POWER OF ATTORNEY"),
    p(f"I, {P('Joseph Thomas Kurian')}, aged 58, residing at {A('Kurian Villa, Market Road, Kottayam, Kerala 686001')}, do hereby appoint my son "
      f"{P('Abraham Joseph Kurian')} of {A('Flat 9B, Marina Towers, Marine Drive, Kochi, Kerala 682031')} as my attorney to manage my properties."),
    p(f"Executed at the office of {O('Kurian and Associates')} on {D('June 14, 2023')} in the presence of {P(DSOUZA)} and {P('Thomas Mathew')}."))

# ============================== ID CARDS AND FORMS ==============================
add("id_01", "id_card", "en", False,
    f"<div class='card'><div class='ctitle'>ELECTION COMMISSION OF INDIA — ELECTOR PHOTO IDENTITY CARD</div>",
    kv([("Name", P("Shabnam Begum")), ("Father's Name", P("Mohammed Yusuf Ansari")), ("Date of Birth", D("14/07/1985")),
        ("Address", A("H.No. 18, Jamia Nagar, New Delhi 110025")), ("EPIC No.", "XYZ1234567")]),
    "</div>", cls="cardpage")

add("id_02", "id_card", "en", True,
    "<div class='card'><div class='ctitle'>DRIVING LICENCE</div>",
    kv([("Holder", P("Sandeep Kumar Tiwari")), ("S/o", P("Ramashankar Tiwari")), ("DOB", D("03-Nov-1990")),
        ("Address", A("Gali No. 4, Shastri Nagar, Kanpur, Uttar Pradesh 208005")), ("Issued", D("19/01/2015")),
        ("Valid till", D("18/01/2035")), ("Issuing Authority", O("Regional Transport Office, Kanpur")), ("DL No.", "UP78 20150012345")]),
    "</div>", cls="cardpage")

add("id_03", "id_card", "en", False,
    f"<div class='card'><div class='ctitle'>{O('Greenfield Public School')}</div><div>Student Identity Card 2024-25</div>",
    kv([("Student", P("Rohit Agarwal")), ("Class", "VIII-B"), ("Guardian", P("Suresh Agarwal")), ("Contact", "98100 22334"),
        ("Residence", A("B-15, Vivek Vihar, Delhi 110095")), ("Valid till", D("31 March 2025"))]),
    "</div>", cls="cardpage")

add("id_04", "id_card", "en", False,
    h("EMPLOYEE IDENTITY CARD", 2),
    f"<div class='card'><div class='ctitle'>{O('Orion Logistics Pvt Ltd')}</div>",
    kv([("Employee", P("Pallavi Deshmukh")), ("Emp ID", "OL-20418"), ("Department", "Finance"), ("Joined", D("11 July 2021")),
        ("Reporting to", P("Nitin Joshi")), ("Emergency contact", f"{P('Sanjay Deshmukh')} (father), 98220 56789")]),
    "</div>", cls="cardpage")

add("id_05", "id_card", "en", True,
    h("PATIENT REGISTRATION FORM", 2), f"<div class='head'>{O('Lotus Care Hospital')}, {A('Station Road, Jamshedpur, Jharkhand 831001')}</div>",
    kv([("Patient name", P("Imran Ansari")), ("Age / Sex", "34 / M"), ("Date of visit", D("22/05/2024")),
        ("Attendant", f"{P('Nazia Ansari')} (wife)"), ("Address", A("Plot 77, Bistupur Main Road, Jamshedpur, Jharkhand 831001")),
        ("Consulting doctor", f"Dr. {P('Rajiv Menon')}"), ("Referred by", O("Tata Main Hospital"))]), cls="form")

add("id_06", "id_card", "en", False,
    h("KYC APPLICATION FORM", 2),
    kv([("Applicant", P("Bhavna Patel")), ("Date of birth", D("09-Feb-1992")), ("Mother's name", P("Hansaben Patel")),
        ("Present address", A("12, Sunrise Society, Satellite Road, Ahmedabad, Gujarat 380015")),
        ("Employer", O("Gujarat Agro Exports Ltd")), ("Nominee", f"{P('Jayesh Patel')} (husband)"),
        ("PAN", "AKLPP5566M"), ("Mobile", "99090 12345"), ("Signature date", D("30 June 2024"))]), cls="form")

add("id_07", "id_card", "hi", True,
    "<div class='card'><div class='ctitle'>निर्वाचन आयोग — मतदाता फोटो पहचान पत्र</div>",
    kv([("नाम", P("शबनम बेगम")), ("पिता का नाम", P("मोहम्मद यूसुफ अंसारी")), ("जन्म तिथि", D("१४/०७/१९८५")),
        ("पता", A("मकान नं. १८, जामिया नगर, नई दिल्ली ११००२५")), ("मतदाता सं.", "XYZ1234567")]),
    "</div>", cls="cardpage")

add("id_08", "id_card", "hi", True,
    h("प्रवेश आवेदन पत्र", 2), f"<div class='head'>{O('सनराइज पब्लिक स्कूल')}, {A('स्टेशन रोड, हजारीबाग, झारखंड ८२५३०१')}</div>",
    kv([("छात्र का नाम", P("आदित्य कुमार झा")), ("पिता का नाम", P("अनिल कुमार झा")), ("माता का नाम", P("रीना देवी")),
        ("जन्म तिथि", D("५ अगस्त २०१५")), ("पता", A("मोहल्ला कदमा, हजारीबाग, झारखंड ८२५३०१")), ("आवेदन की तिथि", D("१० अप्रैल २०२४"))]), cls="form")

add("id_09", "id_card", "hi", True,
    h("रोगी पंजीकरण फॉर्म", 2), f"<div class='head'>{O('लोटस केयर हॉस्पिटल')}, {A('स्टेशन रोड, जमशेदपुर, झारखंड ८३१००१')}</div>",
    kv([("रोगी का नाम", P("मीनाक्षी पांडेय")), ("उम्र", "३८ वर्ष"), ("भर्ती की तिथि", D("२२/०५/२०२४")),
        ("परिजन", f"{P('राकेश पांडेय')} (पति)"), ("पता", A("प्लॉट ७७, बिष्टुपुर, जमशेदपुर, झारखंड ८३१००१")), ("चिकित्सक", f"डॉ. {P('राजीव मेनन')}")]), cls="form")

add("id_10", "id_card", "en", False,
    h("CERTIFICATE OF REGISTRATION (VEHICLE)", 2),
    kv([("Registered owner", P("Tenzin Dorjee")), ("Son/Wife/Daughter of", P("Pema Dorjee")), ("Address", A("Tibetan Colony, Majnu ka Tilla, New Delhi 110054")),
        ("Registration date", D("05-Jun-2019")), ("Valid upto", D("04-Jun-2034")), ("Registration No.", "DL 01 AB 4321"),
        ("Hypothecated to", O("HDFC Bank Ltd"))]), cls="form")

add("id_11", "id_card", "en", True,
    h("PASSPORT APPLICATION — PERSONAL PARTICULARS", 2),
    kv([("Given name", P("Anjali Mary")), ("Surname", P("D'Souza")), ("Date of birth", D("17/12/1994")),
        ("Place of birth", "Mangaluru"), ("Present address", A("Rosario Apartments, Hampankatta, Mangaluru, Karnataka 575001")),
        ("Father's name", P("Francis D'Souza")), ("Mother's name", P("Rita D'Souza")), ("Employer", O("Sahyadri Hospital"))]), cls="form")

# ============================== BANK DOCUMENTS ==============================
add("bank_01", "bank_statement", "en", False,
    f"<div class='head'><b>{O('State Bank of India')}</b> &nbsp; Account Statement</div>",
    kv([("Account holder", P("Arvind Narayanan Iyer")), ("Address", A("45, 2nd Cross, Indiranagar, Bengaluru, Karnataka 560038")),
        ("Statement period", f"{D('01/03/2024')} to {D('31/03/2024')}"), ("Account No.", "30112345678")]),
    tbl(["Date", "Narration", "Debit", "Credit", "Balance"], [
        [D("02/03/2024"), f"UPI/{P('Meenakshi Subramanian')}/rent", "28,000.00", "", "1,42,310.50"],
        [D("05/03/2024"), f"NEFT-{O('Orion Logistics Pvt Ltd')}-salary", "", "95,000.00", "2,37,310.50"],
        [D("11/03/2024"), f"UPI/{P('Kiran Rao')}/dinner", "1,850.00", "", "2,35,460.50"],
        [D("19/03/2024"), f"ATM WDL {A('MG Road, Bengaluru')}", "10,000.00", "", "2,25,460.50"]]), cls="mono")

add("bank_02", "bank_statement", "en", True,
    f"<div class='head'><b>{O('Punjab National Bank')}</b> — Savings Passbook Entries</div>",
    kv([("Name", P("Harleen Kaur")), ("Address", A("SCO 45, Phase 7, Mohali, Punjab 160061"))]),
    tbl(["Date", "Particulars", "Withdrawn", "Deposited"], [
        [D("03 Apr 2024"), f"By transfer {P('Jaspreet Singh Gill')}", "", "15,000.00"],
        [D("07 Apr 2024"), f"To {O('Mohali Electricity Board')}", "2,310.00", ""],
        [D("21 Apr 2024"), f"NEFT {P('Gurpreet Singh Sandhu')}", "", "8,500.00"]]), cls="mono")

add("bank_03", "bank_statement", "en", False,
    f"<div class='head'><b>{O('HDFC Bank')}</b> Credit Card Statement</div>",
    kv([("Card holder", P("Pallavi Deshmukh")), ("Billing address", A("B-204, Shivalik Heights, Baner Road, Pune, Maharashtra 411045")),
        ("Statement date", D("15 May 2024")), ("Payment due", D("04 June 2024")), ("Card", "XXXX XXXX XXXX 4417")]),
    tbl(["Date", "Merchant", "Amount"], [
        [D("02/05/2024"), O("Reliance Digital"), "18,990.00"], [D("09/05/2024"), O("Zomato"), "640.00"],
        [D("12/05/2024"), O("IndiGo Airlines"), "7,420.00"]]), cls="mono")

add("bank_04", "bank_statement", "en", False,
    f"<div class='head'><b>{O('Kaveri Finance Ltd')}</b> — Loan Account Statement</div>",
    kv([("Borrower", P("Sandeep Kumar Tiwari")), ("Co-borrower", P("Kavita Rani")), ("Address", A("Gali No. 4, Shastri Nagar, Kanpur, Uttar Pradesh 208005")),
        ("Loan No.", "LN00918273"), ("Sanctioned on", D("14 January 2022"))]),
    tbl(["Due date", "EMI", "Paid on", "Status"], [
        [D("05/02/2024"), "12,450", D("05/02/2024"), "Paid"], [D("05/03/2024"), "12,450", D("07/03/2024"), "Paid late"],
        [D("05/04/2024"), "12,450", "-", "Due"]]), cls="mono")

add("bank_05", "bank_statement", "en", False,
    f"<div class='head'><b>{O('Greenfield Public School')}</b> — Salary Slip for {D('April 2024')}</div>",
    kv([("Employee", P("Rohit Agarwal")), ("Designation", "Teacher"), ("Employee code", "GPS-114"), ("Pay date", D("30/04/2024")),
        ("Bank", O("Bank of Baroda")), ("A/c", "0412 0100 5566")]),
    tbl(["Earnings", "Amount", "Deductions", "Amount"], [["Basic", "32,000", "PF", "3,840"], ["HRA", "12,800", "Tax", "1,200"]]), cls="mono")

add("bank_06", "bank_statement", "en", True,
    "<div class='head'><b>UPI Transaction History</b> — registered mobile 98100 22334</div>",
    tbl(["Date", "Paid to / Received from", "Amount"], [
        [D("01/06/2024"), P("Suresh Agarwal"), "+ 5,000"], [D("03/06/2024"), O("BigBasket"), "- 1,284"],
        [D("04/06/2024"), P("Nitin Joshi"), "- 750"], [D("08/06/2024"), P("Hansaben Patel"), "+ 2,100"]]), cls="mono")

add("bank_07", "bank_statement", "hi", True,
    f"<div class='head'><b>{O('भारतीय स्टेट बैंक')}</b> — खाता विवरण</div>",
    kv([("खाताधारक", P("सुनीता देवी")), ("पता", A("ग्राम रामपुर, पोस्ट बलियापुर, धनबाद, झारखंड ८२८२०१")), ("अवधि", f"{D('०१/०५/२०२४')} से {D('३१/०५/२०२४')}")]),
    tbl(["तारीख", "विवरण", "जमा", "निकासी"], [
        [D("०३/०५/२०२४"), f"यूपीआई/{P('रमेश चंद्र गुप्ता')}", "८,०००", ""], [D("१०/०५/२०२४"), f"चेक/{P('अजय कुमार सिंह')}", "", "२,५००"],
        [D("२१/०५/२०२४"), f"एनईएफटी/{O('हिमालय एग्रो इंडस्ट्रीज')}", "१५,०००", ""]]), cls="mono")

add("bank_08", "bank_statement", "hi", True,
    h("जमा पर्ची", 2), f"<div class='head'>{O('पंजाब नेशनल बैंक')}, शाखा {A('हजारीबाग रोड, रांची, झारखंड ८३४००१')}</div>",
    kv([("दिनांक", D("१२ जून २०२४")), ("खाताधारक का नाम", P("संजय कुमार महतो")), ("जमाकर्ता", P("पूजा वर्मा")),
        ("राशि", "२५,००० रुपये"), ("मोबाइल", "९८७६५ ४३२१०")]), cls="form")

add("bank_09", "bank_statement", "en", False,
    h("DEMAND DRAFT APPLICATION", 2), f"<div class='head'>{O('Canara Bank')}, {A('Brigade Road Branch, Bengaluru, Karnataka 560001')}</div>",
    kv([("Applicant", P("Lakshmi Priya Reddy")), ("Pay to", "Registrar, " + O("Anna University")), ("Amount", "Rs. 45,000"),
        ("Purpose", f"Tuition fee of {P('Karthik Reddy')}"), ("Date", D("2024-07-15")),
        ("Address", A("Door No. 12-4-67, Gandhi Nagar, Vijayawada, Andhra Pradesh 520003"))]), cls="form")

add("bank_10", "bank_statement", "en", True,
    f"<div class='head'><b>{O('Axis Bank')}</b> &nbsp; Account Opening Confirmation</div>",
    p(f"Dear {P('Imran Ansari')},"),
    p(f"We are pleased to confirm that a savings account has been opened in your name on {D('29 July 2024')} at our branch at "
      f"{A('Bistupur Main Road, Jamshedpur, Jharkhand 831001')}. Your relationship manager is Ms. {P('Debjani Roy')}. "
      f"Your joint holder {P('Nazia Ansari')} has also been registered."),
    p("Customer ID: 118827364. For support write to care@axisexample.test."), cls="letter")

assert len({d.name for d in DOCS}) == len(DOCS)


def split_markers(html: str):
    """Return (html without markers, [(label, value), ...] in order of appearance)."""
    found = [(LABEL_OF[m.group(1)], m.group(2)) for m in MARKER.finditer(html)]
    return MARKER.sub(lambda m: m.group(2), html), found
