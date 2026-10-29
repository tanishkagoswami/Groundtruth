import argparse, json, time, datetime, statistics, concurrent.futures as cf
from collections import defaultdict
import requests, config
from graders import grade_case, field

def call(case, retries=2):
    for attempt in range(retries + 1):
        t = time.time()
        try:
            # ONLY send the exact two fields the FastAPI PaperRequest schema expects
            a_url = case.get("arxiv_url", "")
            
            # Send exactly what the Pydantic schema demands
            payload = {
                "arxiv_url": a_url,
                "github_url": case.get("github_url", "") or "",
                "arxiv_id": a_url.split("/")[-1].replace(".pdf", "")  # Extract ID to satisfy Pydantic!
            }
            r = requests.post(config.API_URL, json=payload, timeout=config.TIMEOUT_S)
            
            try: body = r.json()
            except Exception: body = {"_raw": r.text[:500]}

            # ADD THIS DEBUG LINE:
            if r.status_code == 422:
                print(f"\n[!] 422 Validation Error on {case['id']}: {body}")
                
            return r.status_code, body, time.time() - t
            
        except requests.Timeout:
            return 599, {"_raw": "timeout"}, time.time() - t
        except Exception as e:
            return 598, {"_raw": str(e)}, time.time() - t
def run_one(case, repeat):
    time.sleep(3)  # <--- ADD THIS to respect Groq's rate limits
    runs = []
    for _ in range(repeat):
        status, body, lat = call(case)
        runs.append({"status": status, "latency": round(lat, 1), "response": body,
                     "grades": grade_case(case, status, body, lat)})
    return {"case": case, "runs": runs}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", default="golden_set.jsonl")
    ap.add_argument("--repeat", type=int, default=1, help="runs per case (use 3 to measure flakiness)")
    ap.add_argument("--only", help="comma list of ids or category names")
    ap.add_argument("--verified-only", action="store_true")
    a = ap.parse_args()

    cases = []
    # Try reading the file, and if it crashes, print the raw invisible bytes
    with open(a.golden, 'rb') as f:  # Read as raw binary to bypass Windows encoding
        for i, raw_line in enumerate(f):
            if not raw_line.strip(): continue
            
            # Decode and clean
            try:
                line = raw_line.decode('utf-8').strip()
                cases.append(json.loads(line))
            except Exception as e:
                print(f"\n[!] CRASH ON LINE {i+1}")
                print(f"RAW BYTES: {raw_line}")
                print(f"TEXT SEEN BY PYTHON: {repr(line if 'line' in locals() else raw_line)}")
                print(f"ERROR: {e}\n")
                exit(1)
    if a.only:
        keys = set(a.only.split(","))
        cases = [c for c in cases if c["id"] in keys or c["category"] in keys]
    if a.verified_only:
        cases = [c for c in cases if c.get("verified")]

    results = []
    # Change config.MAX_WORKERS to 1 to run sequentially
    with cf.ThreadPoolExecutor(1) as ex:
        for i, res in enumerate(ex.map(lambda c: run_one(c, a.repeat), cases), 1):
            fails = [k for r in res["runs"] for k, v in r["grades"].items() if v["passed"] is False]
            print(f"[{i}/{len(cases)}] {res['case']['id']:<9} {'FAIL ' + ','.join(sorted(set(fails))) if fails else 'ok'}")
            results.append(res)

    out = f"results/run_{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
    json.dump(results, open(out, "w"), indent=1, default=str)

    # ---- report: pass rate per category, per check ----
    cat = defaultdict(lambda: defaultdict(list))
    for res in results:
        for r in res["runs"]:
            for k, v in r["grades"].items():
                if v["passed"] is not None:
                    cat[res["case"]["category"]][k].append(v["passed"])
    print("\n== pass rate by category / check ==")
    for c, checks in sorted(cat.items()):
        print(f"\n{c}")
        for k, v in sorted(checks.items()):
            print(f"  {k:<18} {sum(v)}/{len(v)}  ({100*sum(v)/len(v):.0f}%)")

    # ---- aggregate sanity: do scores separate hard from easy papers? ----
    def mean_score(pred):
        s = [field(r["response"], "score") for res in results if pred(res["case"]) for r in res["runs"]
             if r["status"] == 200 and field(r["response"], "score") is not None]
        return statistics.mean(s) if s else None
    big, none_ = mean_score(lambda c: c["category"] == "big_compute"), mean_score(lambda c: c["category"] == "no_hardware")
    print(f"\nmean score  big_compute={big}  no_hardware={none_}  (big_compute should be clearly lower)")
    lat = [r["latency"] for res in results for r in res["runs"]]
    print(f"latency  median={statistics.median(lat):.1f}s  max={max(lat):.1f}s")
    print(f"\nsaved {out}")

if __name__ == "__main__":
    main()