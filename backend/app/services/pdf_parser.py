import asyncio
import io

import httpx

# Prefer PyMuPDF (about 10x faster than pdfplumber); fall back to pdfplumber if it is not installed.
try:
    import pymupdf as _mupdf
except ImportError:
    try:
        import fitz as _mupdf  # older PyMuPDF releases
    except ImportError:
        _mupdf = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# The old parser stopped after page 3, so hardware details in the methods/appendix never reached the LLM.
# Most ML papers are under 40 pages; the cap only keeps 100-page technical reports bounded.
MAX_PAGES = 60

HEADERS = {"User-Agent": "Groundtruth/1.0 (research feasibility tool)"}
RETRY_STATUSES = (429, 500, 502, 503, 504)


def _extract_with_pymupdf(pdf_bytes: bytes) -> str:
    doc = _mupdf.open(stream=pdf_bytes, filetype="pdf")
    try:
        pages = []
        for i, page in enumerate(doc):
            if i >= MAX_PAGES:
                break
            pages.append(page.get_text())
        return "\n".join(pages)
    finally:
        doc.close()


def _extract_with_pdfplumber(pdf_bytes: bytes) -> str:
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            if i >= MAX_PAGES:
                break
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts text from up to MAX_PAGES pages of a PDF (it used to be only the first 3).
    Used for arXiv/Unpaywall downloads and for direct frontend uploads.
    """
    parsers = []
    if _mupdf is not None:
        parsers.append(("PyMuPDF", _extract_with_pymupdf))
    if pdfplumber is not None:
        parsers.append(("pdfplumber", _extract_with_pdfplumber))

    for name, parse in parsers:
        try:
            text = parse(pdf_bytes)
            if text.strip():
                return text
        except Exception as e:
            print(f"DEBUG: {name} failed to parse PDF: {e}")
    return ""


async def extract_text_from_pdf_url(pdf_url: str) -> str:
    """Downloads a PDF in memory and extracts its text. Returns "" on any failure."""
    async with httpx.AsyncClient(follow_redirects=True, headers=HEADERS) as client:
        for attempt in range(2):
            try:
                response = await client.get(pdf_url, timeout=60.0)
                if response.status_code == 200:
                    # parsing is CPU-bound: keep it off the event loop
                    return await asyncio.to_thread(extract_text_from_bytes, response.content)
                print(f"DEBUG: PDF download HTTP {response.status_code} for {pdf_url}")
                if response.status_code not in RETRY_STATUSES:
                    break
            except Exception as e:
                print(f"DEBUG: Failed to download PDF (attempt {attempt + 1}): {type(e).__name__}: {e}")
            if attempt == 0:
                await asyncio.sleep(3)
    return ""
