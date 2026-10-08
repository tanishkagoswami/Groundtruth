import io
import httpx
import pdfplumber

async def extract_text_from_pdf_url(pdf_url: str) -> str:
    """
    Downloads a PDF from a URL in memory and extracts its text.
    Used for Unpaywall results.
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(pdf_url, timeout=15.0)
            if response.status_code == 200:
                # Load the PDF bytes directly into memory
                return extract_text_from_bytes(response.content)
        except Exception as e:
            print(f"DEBUG: Failed to download PDF: {e}")
            
    return ""

def extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """
    Parses a PDF file and extracts text from the first 3 pages.
    Used for both Unpaywall downloads and direct frontend uploads.
    """
    extracted_text = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # We only need the first 2-3 pages (Abstract & Introduction) 
            # to figure out hardware/dataset constraints.
            for i, page in enumerate(pdf.pages):
                if i >= 3: 
                    break
                text = page.extract_text()
                if text:
                    extracted_text.append(text)
                    
        return "\n".join(extracted_text)
    except Exception as e:
        print(f"DEBUG: PDF parsing failed: {e}")
        return ""