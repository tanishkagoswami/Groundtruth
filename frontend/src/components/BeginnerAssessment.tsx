import { CheckCircle2, AlertCircle } from "lucide-react";

export default function BeginnerAssessment({ score, datasetValidity }: { score: number, datasetValidity: boolean }) {
  return (
    <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-sm shadow-lg relative w-full">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-amber-500 to-orange-500"></div>
      <h3 className="text-slate-400 text-xs tracking-widest font-bold mb-6 flex items-center gap-2">
        <CheckCircle2 className="w-4 h-4 text-amber-400" /> BEGINNER ASSESSMENT
      </h3>
      
      <div className="space-y-6">
        <div>
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <span className="text-slate-400 text-sm">Dataset Availability</span>
            <span className={datasetValidity ? "text-emerald-400 font-bold text-sm" : "text-rose-400 font-bold text-sm"}>
              {datasetValidity ? "VERIFIED" : "MISSING"}
            </span>
          </div>
        </div>

        <div>
          <div className="flex justify-between items-center border-b border-slate-800 pb-3">
            <span className="text-slate-400 text-sm">Student Feasibility</span>
            <span className="text-amber-400 font-mono font-bold text-lg">
              {score} / 100
            </span>
          </div>
        </div>

        <div className="bg-slate-950/80 border border-slate-800/80 p-4 rounded text-sm text-slate-300">
          {score > 60 
            ? "Verdict: Recommended for undergraduate projects. Good documentation and reasonable compute." 
            : "Verdict: High friction. Requires advanced architectural knowledge or heavy hardware allocation."}
        </div>
      </div>
    </div>
  );
}