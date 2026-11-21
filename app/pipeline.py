"""Native-PDF extraction and deterministic invoice fields; OCR is an explicit extension point."""
import re
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass
from typing import Any
import fitz

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 25

@dataclass
class PageText:
    page: int
    text: str
    method: str


def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    if len(pdf_bytes) > MAX_BYTES:
        raise ValueError("PDF exceeds 10 MB")
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("File must be a PDF")
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError("Unable to open PDF") from exc
    try:
        if doc.needs_pass:
            raise ValueError("Encrypted PDFs are unsupported")
        if len(doc) > MAX_PAGES:
            raise ValueError("PDF exceeds 25 pages")
        pages = []
        for i, page in enumerate(doc):
            native = page.get_text("text", sort=True).strip()
            # Scanned pages are NOT silently sent to an external OCR service.
            pages.append(PageText(i + 1, native, "native" if native else "ocr_required"))
        return pages
    finally:
        doc.close()


def _money(pattern: str, text: str) -> str | None:
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        return str(Decimal(raw).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def parse_invoice(pages: list[PageText]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    evidence: dict[str, Any] = {}
    patterns = {
        "invoice_number": r"(?:invoice\s*(?:number|no\.?|#))\s*[:#]?\s*([A-Z0-9-]+)",
        "invoice_date": r"(?:invoice\s*date|date)\s*:\s*(\d{4}-\d{2}-\d{2})",
    }
    for name, pattern in patterns.items():
        for page in pages:
            m = re.search(pattern, page.text, re.IGNORECASE)
            if m:
                fields[name] = m.group(1)
                evidence[name] = {"page": page.page, "source": m.group(0)}
                break
    for name, pattern in {
        "total": r"^\s*(?:grand\s+total|total\s+due)\s*:\s*\$?\s*([\d,]+\.\d{2})\s*$",
        "subtotal": r"^\s*subtotal\s*:\s*\$?\s*([\d,]+\.\d{2})\s*$",
        "tax": r"^\s*(?:tax|vat)\s*:\s*\$?\s*([\d,]+\.\d{2})\s*$",
    }.items():
        for page in pages:
            value = _money(pattern, page.text)
            if value is not None:
                fields[name] = value
                evidence[name] = {"page": page.page, "source": "matching text line"}
                break
    checks = []
    if all(k in fields for k in ("subtotal", "tax", "total")):
        expected = Decimal(fields["subtotal"]) + Decimal(fields["tax"])
        checks.append({"rule": "subtotal_plus_tax_equals_total", "passed": expected == Decimal(fields["total"])})
    return {"fields": fields, "evidence": evidence, "checks": checks,
            "review_required": any(p.method == "ocr_required" for p in pages)
            or "total" not in fields or any(not c["passed"] for c in checks)}
