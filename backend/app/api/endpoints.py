import asyncio
from fastapi import APIRouter, HTTPException, File, UploadFile

# Data Schemas
from app.models.schemas import (
    PaperRequest,
    FeasibilityReport,
    GitHubMetrics,
    ScaffoldRequest,
    ScaffoldResponse
)

# External Services & Processing
from app.services.arxiv import fetch_paper_metadata
from app.services.github import fetch_github_metrics
from app.services.llm import (
    extract_engineering_constraints,
    generate_environment_scaffold
)
from app.services.semantic import fetch_citation_context
from app.services.dataset import validate_dataset_access
from app.services.unpaywall import fetch_open_access_pdf
from app.services.pdf_parser import extract_text_from_pdf_url, extract_text_from_bytes

# Initialize Router
router = APIRouter()


def _metrics_from(gh_data, fallback_url):
    """
    Returns GitHubMetrics, or None when the lookup failed.
    fetch_github_metrics returns {"error": ...} on failure; that used to be turned into
    "empty" metrics (no flags), which looked like a repo with no setup files.
    """
    if not gh_data:
        return None
    if isinstance(gh_data, dict):
        if gh_data.get("error"):
            print(f"DEBUG: GitHub lookup failed for {fallback_url}: {gh_data['error']}")
            return None
        return GitHubMetrics(
            repo_url=gh_data.get("repo_url", fallback_url),
            friction_score=gh_data.get("friction_score", 0),
            dependency_flags=gh_data.get("dependency_flags", []),
            last_commit_date=gh_data.get("last_commit_date", "Unknown"),
        )
    return gh_data  # already a GitHubMetrics


@router.post("/analyze", response_model=FeasibilityReport)
async def analyze_paper(request: PaperRequest):
    # 1. Grab BOTH URLs from the Pydantic schema
    url = request.arxiv_url
    repo_url = request.github_url

    # ==========================================
    # SCENARIO A: User pasted a GitHub Repo in the FIRST box (Legacy fallback)
    # ==========================================
    if "github.com" in url:
        github_metrics = _metrics_from(await fetch_github_metrics(url), url)
        if github_metrics is None:
            raise HTTPException(status_code=404, detail="GitHub repository not found.")

        return FeasibilityReport(
            paper_title="No Paper Provided (Repository Only)",
            github_metrics=github_metrics
        )

    # ==========================================
    # SCENARIO B: User pasted a Research Paper
    # ==========================================
    text_source = "full_text"
    title_hint = None

    if "arxiv.org" in url:
        arxiv_data = await fetch_paper_metadata(url)
        if arxiv_data.get("error"):
            # fetch_paper_metadata returns {"error": ...} on every failure path
            raise HTTPException(status_code=404, detail=arxiv_data["error"])

        paper_title = arxiv_data["title"]
        title_hint = paper_title
        paper_id = arxiv_data["arxiv_id"]  # clean ID: handles /pdf/ links, versions, old-style IDs

        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        extracted_text = await extract_text_from_pdf_url(pdf_url)
        print(f"DEBUG: PDF text length={len(extracted_text or '')} for {pdf_url}")

        # Fallback to the abstract if the PDF cannot be read. The abstract rarely states hardware,
        # so the response is marked "abstract_only": an empty hardware list then means "unknown".
        if not extracted_text:
            extracted_text = arxiv_data.get("summary", "")
            text_source = "abstract_only"
    else:
        oa_data = await fetch_open_access_pdf(url)
        if oa_data.get("error") or not oa_data.get("pdf_url"):
            raise HTTPException(status_code=403, detail="Paper is paywalled. Please upload PDF.")

        paper_title = f"Document DOI: {oa_data.get('doi', 'Unknown')}"
        pdf_url = oa_data["pdf_url"]
        extracted_text = await extract_text_from_pdf_url(pdf_url)
        print(f"DEBUG: PDF text length={len(extracted_text or '')} for {pdf_url}")
        if not extracted_text:
            raise HTTPException(status_code=500, detail="Failed to read text from PDF.")
        paper_id = oa_data.get("doi", "")

    # 2. WAVE 1: Execute LLM and OpenAlex tasks.
    # No character cut here: extract_engineering_constraints picks the hardware-related passages itself.
    llm_task = extract_engineering_constraints(extracted_text)
    openalex_task = fetch_citation_context(paper_id, title_hint)
    llm_analysis, citations = await asyncio.gather(llm_task, openalex_task, return_exceptions=True)

    if isinstance(citations, Exception):
        print(f"DEBUG: OpenAlex failed: {citations}")
        citations = []
    if isinstance(llm_analysis, Exception) or llm_analysis.get("error"):
        reason = llm_analysis if isinstance(llm_analysis, Exception) else llm_analysis["error"]
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {reason}")

    # 3. Fetch GitHub metrics IF the user provided a repo link in the second box
    parsed_github_metrics = None
    if repo_url and "github.com" in repo_url:
        parsed_github_metrics = _metrics_from(await fetch_github_metrics(repo_url), repo_url)

    # 4. Validate Dataset based on LLM extraction
    dataset_valid = False
    dataset_name = llm_analysis.get("dataset_mentioned")
    if dataset_name and dataset_name.lower() not in ["none", "unknown", "not specified"]:
        dataset_valid = await validate_dataset_access(dataset_name)

    # 5. Return the fully fused payload
    return FeasibilityReport(
        paper_title=paper_title,
        github_metrics=parsed_github_metrics,
        hardware_flags=llm_analysis.get("hardware_flags", []),
        dataset_validity=dataset_valid,
        student_feasibility_score=llm_analysis["student_feasibility_score"],
        citations=citations,
        text_source=text_source,
        text_chars=len(extracted_text or ""),
    )


@router.post("/upload", response_model=FeasibilityReport)
async def analyze_uploaded_pdf(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        extracted_text = extract_text_from_bytes(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

    if not extracted_text or not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract readable text from this PDF.")

    llm_analysis = await extract_engineering_constraints(extracted_text)
    if llm_analysis.get("error"):
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {llm_analysis['error']}")

    dataset_valid = False
    dataset_name = llm_analysis.get("dataset_mentioned")
    if dataset_name and dataset_name.lower() not in ["none", "unknown", "not specified"]:
        dataset_valid = await validate_dataset_access(dataset_name)

    return FeasibilityReport(
        paper_title=f"Uploaded Document: {file.filename}",
        github_metrics=None,
        hardware_flags=llm_analysis.get("hardware_flags", []),
        dataset_validity=dataset_valid,
        student_feasibility_score=llm_analysis["student_feasibility_score"],
        citations=[],
        text_source="full_text",
        text_chars=len(extracted_text),
    )


@router.post("/scaffold", response_model=ScaffoldResponse)
async def create_environment_scaffold(request: ScaffoldRequest):
    """
    Decoupled endpoint: Generates custom setup files (Dockerfile/Conda)
    using the extracted hardware constraints and missing repo flags.
    """
    if not request.github_url:
        raise HTTPException(status_code=400, detail="A GitHub repository URL is required.")

    result = await generate_environment_scaffold(
        github_url=request.github_url,
        hardware_flags=request.hardware_flags,
        missing_files=request.missing_files
    )

    return ScaffoldResponse(
        setup_script=result.get("setup_script", "# Error generating setup script"),
        explanation=result.get("explanation", "Unable to generate environment configuration.")
    )
