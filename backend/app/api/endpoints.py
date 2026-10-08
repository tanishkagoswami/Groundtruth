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

@router.post("/analyze", response_model=FeasibilityReport)
async def analyze_paper(request: PaperRequest):
    # 1. Grab BOTH URLs from the new Pydantic schema
    url = request.arxiv_url
    repo_url = request.github_url 
    
    # ==========================================
    # SCENARIO A: User pasted a GitHub Repo in the FIRST box (Legacy fallback)
    # ==========================================
    if "github.com" in url:
        gh_data = await fetch_github_metrics(url)
        if not gh_data:
            raise HTTPException(status_code=404, detail="GitHub repository not found.")
            
        github_metrics = GitHubMetrics(
            repo_url=gh_data.get("repo_url", url) if isinstance(gh_data, dict) else gh_data.repo_url,
            friction_score=gh_data.get("friction_score", 0) if isinstance(gh_data, dict) else gh_data.friction_score,
            dependency_flags=gh_data.get("dependency_flags", []) if isinstance(gh_data, dict) else gh_data.dependency_flags,
            last_commit_date=gh_data.get("last_commit_date", "Unknown") if isinstance(gh_data, dict) else gh_data.last_commit_date
        )
        
        return FeasibilityReport(
            paper_title="No Paper Provided (Repository Only)",
            github_metrics=github_metrics
        )

    # ==========================================
    # SCENARIO B: User pasted a Research Paper
    # ==========================================
    if "arxiv.org" in url:
        arxiv_data = await fetch_paper_metadata(url)
        if arxiv_data.get("error"):
            raise HTTPException(status_code=404, detail="Could not retrieve arXiv paper.")
        
        paper_title = arxiv_data.get("title", "Unknown Title")
        extracted_text = arxiv_data.get("summary", "")
        paper_id = url.split("/")[-1].replace(".pdf", "")
    else:
        oa_data = await fetch_open_access_pdf(url)
        if oa_data.get("error") or not oa_data.get("pdf_url"):
            raise HTTPException(status_code=403, detail="Paper is paywalled. Please upload PDF.")
            
        paper_title = f"Document DOI: {oa_data.get('doi', 'Unknown')}"
        extracted_text = await extract_text_from_pdf_url(oa_data["pdf_url"])
        if not extracted_text:
            raise HTTPException(status_code=500, detail="Failed to read text from PDF.")
        paper_id = oa_data.get('doi', '')

    # 2. WAVE 1: Execute LLM and OpenAlex tasks
    llm_task = extract_engineering_constraints(extracted_text)
    openalex_task = fetch_citation_context(paper_id)
    llm_analysis, citations = await asyncio.gather(llm_task, openalex_task)

    # 3. NEW WAVE: Fetch GitHub metrics IF the user provided a repo link in the second box!
    parsed_github_metrics = None
    if repo_url and "github.com" in repo_url:
        gh_data = await fetch_github_metrics(repo_url)
        if gh_data:
            parsed_github_metrics = GitHubMetrics(
                repo_url=gh_data.get("repo_url", repo_url) if isinstance(gh_data, dict) else gh_data.repo_url,
                friction_score=gh_data.get("friction_score", 0) if isinstance(gh_data, dict) else gh_data.friction_score,
                dependency_flags=gh_data.get("dependency_flags", []) if isinstance(gh_data, dict) else gh_data.dependency_flags,
                last_commit_date=gh_data.get("last_commit_date", "Unknown") if isinstance(gh_data, dict) else gh_data.last_commit_date
            )

    # 4. Validate Dataset based on LLM extraction
    dataset_valid = False
    dataset_name = llm_analysis.get("dataset_mentioned")
    if dataset_name and dataset_name.lower() not in ["none", "unknown", "not specified"]:
        dataset_valid = await validate_dataset_access(dataset_name)

    # 5. Return the fully fused payload!
    return FeasibilityReport(
        paper_title=paper_title,
        github_metrics=parsed_github_metrics, # <--- NOW IT PASSES THE GITHUB DATA
        hardware_flags=llm_analysis.get("hardware_flags", []),
        dataset_validity=dataset_valid,
        student_feasibility_score=llm_analysis.get("student_feasibility_score", 50),
        citations=citations
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

    dataset_valid = False
    dataset_name = llm_analysis.get("dataset_mentioned")
    if dataset_name and dataset_name.lower() not in ["none", "unknown", "not specified"]:
        dataset_valid = await validate_dataset_access(dataset_name)

    return FeasibilityReport(
        paper_title=f"Uploaded Document: {file.filename}",
        github_metrics=None,
        hardware_flags=llm_analysis.get("hardware_flags", []),
        dataset_validity=dataset_valid,
        student_feasibility_score=llm_analysis.get("student_feasibility_score", 50),
        citations=[]
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