import pymupdf


class InvalidPdf(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_pdf(data: bytes, max_bytes: int, max_pages: int) -> int:
    """Return the page count, or raise InvalidPdf with a message safe to show users."""
    if len(data) > max_bytes:
        raise InvalidPdf("File is too large", 413)
    if b"%PDF-" not in data[:1024]:
        raise InvalidPdf("File is not a PDF")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:  # untrusted input: any parser failure means "not usable"
        raise InvalidPdf("File could not be read as a PDF")
    with doc:
        if doc.needs_pass or doc.is_encrypted:
            raise InvalidPdf("Password-protected PDFs are not supported")
        if doc.page_count == 0:
            raise InvalidPdf("PDF has no pages")
        if doc.page_count > max_pages:
            raise InvalidPdf(f"PDF has more than {max_pages} pages")
        return doc.page_count