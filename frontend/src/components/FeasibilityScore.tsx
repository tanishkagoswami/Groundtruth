import { Server } from "lucide-react";

interface FeasibilityProps {
  score: number;
}

export default function FeasibilityScore({ score }: FeasibilityProps) {
  const colorClass = 
    score >= 70 ? "text-green-400" : 
    score >= 40 ? "text-yellow-400" : 
    "text-red-400";

  return (
    <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-sm shadow-lg relative overflow-hidden">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 to-blue-500"></div>
      <h3 className="text-slate-400 text-xs tracking-widest font-bold mb-6 flex items-center gap-2">
        <Server className="w-4 h-4 text-cyan-400" /> COMPUTE FEASIBILITY
      </h3>
      
      <div className="flex items-end gap-4">
        <span className={`text-6xl font-black ${colorClass}`}>
          {score}
        </span>
        <span className="text-slate-500 pb-2">/ 100</span>
      </div>
    </div>
  );
}