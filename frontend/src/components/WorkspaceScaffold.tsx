import { useState } from "react";
import { generateScaffold } from "../lib/api";
import { Terminal, Copy, CheckCircle2 } from "lucide-react";

export default function WorkspaceScaffold({ 
  githubUrl, 
  hardwareFlags, 
  dependencyFlags 
}: { 
  githubUrl: string; 
  hardwareFlags: string[]; 
  dependencyFlags: string[]; 
}) {
  const [loading, setLoading] = useState(false);
  const [scaffold, setScaffold] = useState<{setup_script: string, explanation: string} | null>(null);
  const [copied, setCopied] = useState(false);

  if (!githubUrl) return null;

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const data = await generateScaffold(githubUrl, hardwareFlags, dependencyFlags);
      setScaffold(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (scaffold) {
      navigator.clipboard.writeText(scaffold.setup_script);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-sm shadow-lg relative w-full mt-6">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-purple-500"></div>
      
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-slate-400 text-xs tracking-widest font-bold flex items-center gap-2">
          <Terminal className="w-4 h-4 text-indigo-400" /> ENVIRONMENT SCAFFOLD
        </h3>
        
        {!scaffold && (
          <button 
            onClick={handleGenerate}
            disabled={loading}
            className="border border-indigo-700/50 text-indigo-400 bg-indigo-950/40 hover:bg-indigo-900/80 hover:text-indigo-100 hover:shadow-[0_0_15px_rgba(99,102,241,0.4)] transition-all duration-300 text-xs px-4 py-1.5 tracking-widest font-bold uppercase rounded-sm disabled:opacity-50"
          >
            {loading ? "GENERATING..." : "GENERATE WORKSPACE"}
          </button>
        )}
      </div>

      {scaffold && (
        <div className="space-y-4 animate-in fade-in slide-in-from-top-4 duration-500">
          <p className="text-slate-400 text-xs italic">{scaffold.explanation}</p>
          
          <div className="relative group">
            <div className="absolute right-2 top-2 z-10">
              <button 
                onClick={copyToClipboard}
                className="p-2 bg-slate-800 rounded hover:bg-slate-700 text-slate-300 transition-colors"
                title="Copy to clipboard"
              >
                {copied ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
            <pre className="bg-slate-950 border border-slate-800 p-4 rounded overflow-x-auto text-xs text-slate-300 font-mono custom-scrollbar">
              <code>{scaffold.setup_script}</code>
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}