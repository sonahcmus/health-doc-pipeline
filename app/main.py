from fastapi import FastAPI, File, HTTPException, UploadFile
from .pipeline import MAX_BYTES, extract_pages, parse_invoice

app = FastAPI(title="Evidence-backed Document Extraction MVP", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/extract/invoice")
async def extract_invoice(file: UploadFile = File(...)):
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(415, "PDF required")
    raw = await file.read(MAX_BYTES + 1)
    try:
        pages = extract_pages(raw)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    result = parse_invoice(pages)
    return {**result, "pages": [{"page": p.page, "method": p.method, "characters": len(p.text)} for p in pages]}
