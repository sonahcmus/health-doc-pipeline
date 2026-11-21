import fitz
from fastapi.testclient import TestClient
from app.main import app
from app.pipeline import extract_pages, parse_invoice

def pdf_of(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    raw = doc.tobytes()
    doc.close()
    return raw

def test_fields_and_balancing_rule():
    pdf = pdf_of("Invoice Number: INV-2026-001\nInvoice Date: 2026-11-21\nSubtotal: 100.00\nTax: 8.00\nTotal Due: 108.00")
    result = parse_invoice(extract_pages(pdf))
    assert result["fields"]["invoice_number"] == "INV-2026-001"
    assert result["fields"]["total"] == "108.00"
    assert result["checks"][0]["passed"]
    assert not result["review_required"]

def test_bad_total_requires_review():
    result = parse_invoice(extract_pages(pdf_of("Subtotal: 100.00\nTax: 8.00\nTotal Due: 999.00")))
    assert result["review_required"]
    assert not result["checks"][0]["passed"]

def test_scanned_pdf_is_flagged():
    doc = fitz.open()
    doc.new_page()
    raw = doc.tobytes()
    doc.close()
    result = parse_invoice(extract_pages(raw))
    assert result["review_required"]
    assert extract_pages(raw)[0].method == "ocr_required"

def test_endpoint():
    c = TestClient(app)
    r = c.post("/v1/extract/invoice", files={"file": ("sample.pdf", pdf_of("Total Due: 15.00"), "application/pdf")})
    assert r.status_code == 200
    assert r.json()["fields"]["total"] == "15.00"

def test_invalid_file():
    c = TestClient(app)
    r = c.post("/v1/extract/invoice", files={"file": ("bad.pdf", b"garbage", "application/pdf")})
    assert r.status_code == 422
