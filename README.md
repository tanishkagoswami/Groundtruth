🔍 Groundtruth // Telemetry
Academic Code Reproducibility Diagnostics

Groundtruth is a full-stack AI dashboard designed to bridge the gap between complex academic research and reproducible engineering. It ingests research papers (via arXiv) and linked repositories (via GitHub) to generate a comprehensive, real-time audit of hardware constraints, dependency health, and beginner accessibility.

🚀 Core Features
Compute Feasibility: Extracts hidden hardware requirements (GPUs, CUDA versions, training nodes) directly from the paper's methodology using decoupled LLM inference.

Repository Health: Audits GitHub repositories for stale dependencies, missing environment files, and setup friction.

Literature Context: Maps foundational papers and downstream influence using the OpenAlex citation graph.

Beginner Assessment: Evaluates dataset availability against open-access platforms and computes a 0-100 student feasibility score.

Zero-Shot Environment Scaffolding: Automatically generates plug-and-play Dockerfile or bash setup scripts based on extracted hardware flags and missing repository assets.

🛠️ Architecture & Tech Stack
Frontend: Next.js, TypeScript, Tailwind CSS (Stateful UI, reactive telemetry widgets).

Backend: FastAPI microservice architecture running on Uvicorn.

Inference Engine: Groq API (openai/gpt-oss-20b) utilizing resilient, fault-tolerant Python-side parsing to bypass fragile strict-mode JSON validation.

Integrations: arXiv XML, PyMuPDF, GitHub REST API, OpenAlex.

⚙️ Local Development Setup
1. Environment Variables
Create a .env file in the backend directory (this is git-ignored for security):

Code snippet
GROQ_API_KEY=your_groq_api_key_here
2. Backend (FastAPI)
Bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
3. Frontend (Next.js)
Bash
cd frontend
npm install
npm run dev
Access the dashboard at http://localhost:3000