import re
import httpx

async def fetch_open_access_pdf(paper_url: str) -> dict:
    """
    Extracts a DOI from a paywalled URL and pings Unpaywall 
    for a legally free PDF download link.
    """
    # Regex to catch standard DOIs (e.g., 10.1109/TMECH.2023.3270742)
    doi_match = re.search(r'(10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+)', paper_url)
    if not doi_match:
        return {"error": "No DOI found in URL", "pdf_url": None}
        
    doi = doi_match.group(1)
    
    # Unpaywall requires an email for their free tier to track usage
    email = "guchuppu@vitap.ac.in" 
    api_url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(api_url, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if the paper is Open Access (is_oa)
                if data.get("is_oa") and data.get("best_oa_location"):
                    pdf_url = data["best_oa_location"].get("url_for_pdf")
                    return {"error": None, "pdf_url": pdf_url, "doi": doi}
                
                return {"error": "Paywall locked. No open access version found.", "pdf_url": None, "doi": doi}
                
        except Exception as e:
            print(f"DEBUG: Unpaywall API error: {e}")
            return {"error": str(e), "pdf_url": None}
            
    return {"error": "Failed to resolve DOI", "pdf_url": None}