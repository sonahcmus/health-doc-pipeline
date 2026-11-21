# Evidence-backed healthcare document extraction (MVP)

Minimal, runnable **technical proof** for a broader healthcare document intelligence system. This is not production-ready and does not currently run OCR or LLMs. Use synthetic or permitted sample documents only.

## Implemented
- FastAPI PDF-upload endpoint (`POST /v1/extract/invoice`)
- PDF signature check, file-size and page limits, encrypted-PDF rejection
- Native text extraction with PyMuPDF and explicit scanned-page detection
- Deterministic invoice number/date/amount extraction, with page evidence
- Subtotal + tax cross-check; review flags for missing totals, mismatches and image-only pages
- pytest tests, including API upload and synthetic PDF generation

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
uvicorn app.main:app --reload
```

Test manually:
```bash
curl -F 'file=@your-synthetic-invoice.pdf' http://localhost:8000/v1/extract/invoice
```

## Design and next milestones
`upload -> validation -> native PDF parse -> OCR required flag -> deterministic extraction -> evidence + accounting validation -> review queue`

1. **OCR adapter:** render image-only pages locally, integrate PaddleOCR (pinned model version), and preserve word bounding boxes and per-page provenance.
2. **Evaluation harness:** versioned synthetic invoice set, exact-match field scoring, hallucination/error taxonomy, latency and CPU/GPU costs.
3. **Durable jobs:** Celery + Redis, PostgreSQL job states, S3-compatible private object store, idempotency keys and retry policies.
4. **Structured VLM fallback:** schema-constrained extraction only when simpler approaches fail, with human review and a traceable cost budget.
5. **Security:** authentication, tenant isolation, malware scanning, log redaction, retention limits and threat modeling before any sensitive-document handling.

## Known limitations
- Regex is English-only and intentionally brittle; it is a baseline, not a benchmark result.
- `evidence` reports a page and matched text/line, not OCR bounding boxes.
- No OCR, no production data privacy controls, no authentication, and no claims of accuracy on real datasets.
- Real OCR and multi-language/multi-layout support are the engineering goals, not finished functionality.
