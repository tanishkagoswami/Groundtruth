"""python show_results.py [path]  -> one line per case from the latest (or given) run."""
import json, glob, sys
from graders import field

f = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("results/run_*.json"))[-1]
print(f"# {f}\n")
for r in json.load(open(f)):
    c, run = r["case"], r["runs"][0]
    resp = run["response"] if isinstance(run["response"], dict) else {}
    failed = {k: v["detail"] for k, v in run["grades"].items() if v["passed"] is False}
    print(f"{c['id']:<9} HTTP {run['status']}  title={str(resp.get('paper_title'))[:38]!r}")
    print(f"          gpus={field(resp, 'gpus')}  score={field(resp, 'score')}  {run['latency']}s")
    for k, d in failed.items():
        print(f"          FAIL {k}: {d}")
