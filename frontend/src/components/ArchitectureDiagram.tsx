import { GitMerge } from "lucide-react";

export default function ArchitectureDiagram() {
  return (
    <div className="bg-slate-900/50 border border-slate-700/50 p-6 rounded-sm shadow-lg relative w-full mt-6">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-orange-500 to-amber-500"></div>
      <h3 className="text-slate-400 text-xs tracking-widest font-bold mb-6 flex items-center gap-2">
        <GitMerge className="w-4 h-4 text-orange-400" /> SYSTEM ARCHITECTURE
      </h3>
      <div className="h-48 flex items-center justify-center border-2 border-dashed border-slate-800 rounded">
        <p className="text-slate-500 text-sm italic">Diagram rendering coming in v2.0...</p>
      </div>
    </div>
  );
}