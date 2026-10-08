import os
from dotenv import load_dotenv

# 1. Force Python to find the .env file exactly one folder up from /app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.services.pdf_parser import extract_text_from_bytes
from app.services.llm import extract_engineering_constraints
from app.api.endpoints import router as api_router

app = FastAPI(
    title="GroundTruth Engine API",
    description="Backend services for academic code reproducibility.",
    version="1.0.0"
)

# CRITICAL UPDATE: Add CORS middleware so Next.js can communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js local development URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# This registers your endpoints
app.include_router(api_router, prefix="/api")
@app.get("/")
async def root():
    return {
        "message": "Welcome to the GroundTruth Engine API. Visit /docs for the interactive API documentation."
    }
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "GroundTruth Engine is running."}
# @app.post("/api/upload")
# async def analyze_uploaded_pdf(file: UploadFile = File(...)):
#     """Accepts a direct PDF upload, parses first 3 pages, and passes text to Groq."""
#     pdf_bytes = await file.read()
#     extracted_text = extract_text_from_bytes(pdf_bytes)
    
#     if not extracted_text:
#         return {"error": "Could not extract text from the provided PDF."}
        
#     llm_analysis = await extract_engineering_constraints(extracted_text)
    
#     return {
#         "filename": file.filename,
#         "paper_title": f"Uploaded File: {file.filename}",
#         "hardware_flags": llm_analysis.get("hardware_flags", ["Extraction failed"]),
#         "student_feasibility_score": llm_analysis.get("student_feasibility_score", 0),
#         "dataset_validity": True,
#         "github_metrics": None
#     }