import sys, asyncio, re
sys.path.insert(0, ".")
from app.services.pdf_parser import extract_text_from_pdf_url as f

CASES = {
  "unk_07 HuBERT":        ("2106.07447", "v100"),
  "unk_09 Atari DQN":     ("1312.5602",  "gtx 580"),
  "unk_11 AdamW":         ("1711.05101", "titan x"),
  "unk_12 Scaling laws":  ("2001.08361", "v100"),
}
for name, (aid, kw) in CASES.items():
    t = asyncio.run(f(f"https://arxiv.org/pdf/{aid}.pdf")).replace("\n", " ")
    print(f"\n=== {name}  expected '{kw}'  ({len(t)} chars)")
    hits = [m.start() for m in re.finditer(re.escape(kw), t, re.I)]
    print(f"  '{kw}' found {len(hits)}x in full text")
    for h in hits[:2]:
        print("   >", t[max(0, h-150):h+150])
    other = [m.start() for m in re.finditer(r"\b(GPUs?|TPUs?|V100|A100|P100|Titan|GTX|Tesla)\b", t)]
    print(f"  any hardware words: {len(other)}x")
    for h in other[:3]:
        print("   -", t[max(0, h-100):h+120])
