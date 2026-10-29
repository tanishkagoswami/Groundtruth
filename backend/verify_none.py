import sys, asyncio, re, json
sys.path.insert(0, ".")
from app.services.pdf_parser import extract_text_from_pdf_url as f

cases = [json.loads(l) for l in open("eval/golden_set.jsonl", encoding="utf-8") if l.strip()]
for c in cases:
    if not c["id"].startswith("none_"):
        continue
    m = re.search(r"(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})", c["arxiv_url"])
    aid = m.group(1)
    t = asyncio.run(f(f"https://arxiv.org/pdf/{aid}.pdf")).replace("\n", " ")
    hits = [x.start() for x in re.finditer(r"\b(GPUs?|TPUs?|V100|A100|P100|H100|Titan|GTX|Tesla|accelerators?)\b", t)]
    print(f"\n=== {c['id']}  {aid}  hardware words: {len(hits)}")
    for h in hits[:3]:
        print("   -", t[max(0, h-120):h+140])
