"use client";
import RepositoryHealth from "../components/RepositoryHealth";
// NEW: Import the two new components
import LiteratureContext from "../components/LiteratureContext";
import BeginnerAssessment from "../components/BeginnerAssessment";

import { useEffect, useState, useRef } from "react";
import { analyzeUrl, uploadPdf } from "../lib/api";
import { AlertCircle, CheckCircle2, Server, GitFork, BookOpen } from "lucide-react"; 
import WorkspaceScaffold from "../components/WorkspaceScaffold";
export default function Home() {
  const [trail, setTrail] = useState<{ id: number; x: number; y: number }[]>([]);
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  
  // NEW: State for the GitHub URL
  const [githubUrl, setGithubUrl] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportData, setReportData] = useState<any>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const newParticle = { id: Date.now() + Math.random(), x: e.clientX, y: e.clientY };
      setTrail((prev) => [...prev, newParticle].slice(-20));
      setTimeout(() => {
        setTrail((prev) => prev.filter((p) => p.id !== newParticle.id));
      }, 400);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // Seconds since the request started, so we can tell the user what is going on.
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!loading) {
      setElapsed(0);
      return;
    }
    const started = Date.now();
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(id);
  }, [loading]);

  const loadingMessage =
    elapsed < 8
      ? "Analysing paper..."
      : elapsed < 40
      ? "Still working. If the server was idle, it can take up to a minute to wake up."
      : "Large papers can take over a minute. Hang tight...";

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setUrl(""); 
    }
  };

  const clearFile = () => {
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleInitialize = async () => {
    if (!file && !url) return;
    
    setLoading(true);
    setError(null);
    setReportData(null);

    try {
      let data;
      if (file) {
        data = await uploadPdf(file);
      } else {
        // NEW: Pass the githubUrl state to the API
        data = await analyzeUrl(url, githubUrl);
      }
      setReportData(data);
    } catch (err: any) {
      setError(err.message || "Failed to connect to the backend engine.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 relative overflow-hidden flex flex-col pt-24 px-8 font-mono">
      
      {/* YOUR UNTOUCHED PARTICLE TRAIL */}
      {trail.map((p) => (
        <div
          key={p.id}
          className="pointer-events-none fixed z-50 w-2 h-2 bg-cyan-300 rounded-full shadow-[0_0_12px_#22d3ee] sparkle-trail"
          style={{ left: p.x, top: p.y }}
        />
      ))}

      {/* YOUR UNTOUCHED BACKGROUNDS */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f15_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f15_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none"></div>
      <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.25)_50%)] bg-[size:100%_4px] pointer-events-none"></div>
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-cyan-900/20 rounded-full blur-[120px] pointer-events-none animate-pulse"></div>

      <div className="relative z-10 max-w-5xl w-full mx-auto flex flex-col items-center">
        
        <div className="mb-16 border-b border-slate-800/80 pb-6 relative w-full text-center sm:text-left">
          <h1 className="text-3xl font-bold text-slate-100 flex items-center justify-center sm:justify-start gap-3 tracking-wider drop-shadow-[0_0_8px_rgba(34,211,238,0.3)]">
            <span className="text-cyan-400 animate-pulse">{">_"}</span> 
            GROUNDTRUTH <span className="text-slate-600">//</span> TELEMETRY
          </h1>
          <p className="text-cyan-500/70 mt-2 text-sm tracking-widest uppercase font-semibold">
            Academic Code Reproducibility Diagnostics
          </p>
          <div className="absolute bottom-[-1px] left-0 right-0 sm:right-auto w-full sm:w-32 h-[2px] bg-cyan-400 shadow-[0_0_10px_#22d3ee]"></div>
        </div>

        <div className="w-full max-w-3xl relative flex flex-col gap-4">
          
          {/* TARGET INPUT (Your original box) */}
          <div className="relative group w-full">
            <div className="absolute -top-2 -left-2 w-4 h-4 border-t-2 border-l-2 border-cyan-500/30 group-focus-within:border-cyan-400 transition-colors duration-300"></div>
            <div className="absolute -bottom-2 -right-2 w-4 h-4 border-b-2 border-r-2 border-cyan-500/30 group-focus-within:border-cyan-400 transition-colors duration-300"></div>

            <div className="absolute -top-3 left-4 bg-slate-950 px-2 text-xs text-cyan-400 tracking-widest z-10 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]">
              {file ? "LOCAL_FILE_SELECTED" : "TARGET_INPUT"}
            </div>

            <div className="relative flex items-center">
              <svg className="w-5 h-5 text-cyan-800 absolute left-4 group-focus-within:text-cyan-300 group-focus-within:drop-shadow-[0_0_5px_rgba(34,211,238,0.8)] transition-all duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {file ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                )}
              </svg>

              <input 
                type="text" 
                value={file ? `[PDF ATTACHED] ${file.name}` : url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter arXiv, IEEE URL..." 
                readOnly={!!file}
                className={`w-full border text-sm py-4 pl-12 pr-12 focus:outline-none transition-all duration-300 shadow-[inset_0_0_20px_rgba(0,0,0,0.5)] 
                  ${file 
                    ? "bg-slate-900/80 border-cyan-500/50 text-cyan-300" 
                    : "bg-slate-900/60 border-slate-700/50 text-cyan-50 focus:border-cyan-400/80 focus:bg-slate-900/80 focus:ring-1 focus:ring-cyan-400/50 group-focus-within:shadow-[inset_0_0_15px_rgba(34,211,238,0.15)]"
                  }`}
              />

              <input type="file" accept=".pdf" ref={fileInputRef} onChange={handleFileChange} className="hidden"/>

              <div className="absolute right-4 flex items-center">
                {file ? (
                  <button onClick={clearFile} className="text-red-400 hover:text-red-300 transition-colors p-2" title="Remove PDF">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                  </button>
                ) : (
                  <button onClick={() => fileInputRef.current?.click()} className="text-cyan-700 hover:text-cyan-300 hover:drop-shadow-[0_0_5px_rgba(34,211,238,0.8)] transition-all p-2" title="Upload PDF">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"></path></svg>
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* NEW: REPO INPUT (Styled to match your aesthetic exactly) */}
          <div className="relative group w-full">
            <div className="absolute -top-3 left-4 bg-slate-950 px-2 text-xs text-fuchsia-400 tracking-widest z-10 drop-shadow-[0_0_5px_rgba(217,70,239,0.8)]">
              GITHUB_LINK
            </div>
            <div className="relative flex items-center">
              <GitFork className="w-5 h-5 text-fuchsia-800 absolute left-4 group-focus-within:text-fuchsia-300 group-focus-within:drop-shadow-[0_0_5px_rgba(217,70,239,0.8)] transition-all duration-300" />
              <input 
                type="text" 
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                placeholder="https://github.com/... (Optional)" 
                disabled={!!file}
                className="w-full border text-sm py-4 pl-12 pr-44 focus:outline-none transition-all duration-300 shadow-[inset_0_0_20px_rgba(0,0,0,0.5)] bg-slate-900/60 border-slate-700/50 text-fuchsia-50 focus:border-fuchsia-400/80 focus:bg-slate-900/80 focus:ring-1 focus:ring-fuchsia-400/50 group-focus-within:shadow-[inset_0_0_15px_rgba(217,70,239,0.15)] disabled:opacity-50"
              />
              <button 
                onClick={handleInitialize}
                disabled={loading || (!file && !url)}
                className="absolute right-2 top-1/2 -translate-y-1/2 border border-cyan-700/50 text-cyan-400 bg-cyan-950/40 hover:bg-cyan-900/80 hover:text-cyan-100 hover:shadow-[0_0_20px_rgba(34,211,238,0.4)] hover:border-cyan-300 transition-all duration-300 text-xs px-6 py-2 tracking-widest font-bold uppercase rounded-sm disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none"
              >
                {loading ? "Processing..." : "Initialize"}
              </button>
            </div>
          </div>
        </div>

        {/* NEW: progress message while the request is running */}
        {loading && (
          <p className="mt-8 w-full max-w-3xl text-sm text-cyan-400/80 tracking-wide">
            {loadingMessage} <span className="text-slate-500">({elapsed}s)</span>
          </p>
        )}

        {/* NEW: visible error message */}
        {error && !loading && (
          <div className="mt-8 w-full max-w-3xl flex items-start gap-3 border border-red-500/40 bg-red-950/30 text-red-300 text-sm p-4 rounded-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        )}

        {/* Backend report */}
        {reportData && (
          <div className="w-full max-w-5xl mt-12 flex flex-col gap-6 pb-24">
            
            {/* ROW 1: Compute and Repo */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-sm shadow-lg relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 to-blue-500"></div>
                <h3 className="text-slate-400 text-xs tracking-widest font-bold mb-6 flex items-center gap-2">
                  <Server className="w-4 h-4 text-cyan-400" /> COMPUTE FEASIBILITY
                </h3>
                
                <div className="flex items-end gap-4 mb-6">
                  <span className={`text-6xl font-black ${
                    reportData.student_feasibility_score >= 70 ? "text-green-400" : 
                    reportData.student_feasibility_score >= 40 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {reportData.student_feasibility_score}
                  </span>
                  <span className="text-slate-500 pb-2">/ 100</span>
                </div>

                <div className="space-y-2">
                  <p className="text-xs text-slate-400 uppercase">Hardware Flags Detected:</p>
                  <div className="flex flex-wrap gap-2">
                    {reportData.hardware_flags.length > 0 ? (
                      reportData.hardware_flags.map((flag: string, i: number) => (
                        <span key={i} className="bg-slate-800 text-cyan-300 border border-cyan-800/50 text-xs px-3 py-1 rounded-full">
                          {flag}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-500 text-sm">No specific hardware constraints detected.</span>
                    )}
                  </div>
                </div>
              </div>

              <RepositoryHealth metrics={reportData.github_metrics} />
            </div>

            {/* ROW 2: Context and Beginner Assessment */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <LiteratureContext citations={reportData.citations} />
              <BeginnerAssessment 
                score={reportData.student_feasibility_score} 
                datasetValidity={reportData.dataset_validity} 
              />
            </div>

            {/* NEW ROW 3: Environment Generation (Only renders if a GitHub URL was provided) */}
            {reportData.github_metrics && (
              <WorkspaceScaffold 
                githubUrl={reportData.github_metrics.repo_url}
                hardwareFlags={reportData.hardware_flags}
                dependencyFlags={reportData.github_metrics.dependency_flags}
              />
            )}

          </div>
        )}
      </div>
    </main>
  );
}