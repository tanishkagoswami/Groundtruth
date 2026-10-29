import json, sys
from graders import field

for p in sys.argv[1:]:
    r = json.load(open(p, encoding="utf-8"))[0]["runs"][0]
    resp = r["response"]
    print("=====", p, f"({r['latency']}s, HTTP {r['status']})")
    print("gpu_match:", r["grades"].get("gpu_match"))
    print("text_source:", resp.get("text_source"))
    print("gpus:", field(resp, "gpus"))
    print("compute_text:", json.dumps(field(resp, "compute_text"), indent=1, ensure_ascii=False)[:1500])