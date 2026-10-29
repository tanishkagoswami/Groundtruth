"""Does the 0-100 feasibility score order papers the way a student would?

No Groq tokens, no network: it only reads a results file that run_eval.py already saved.

    python test_ranking.py                      # uses the newest results/run_*.json
    python test_ranking.py results/baseline.json
    python test_ranking.py --mine my_ranking.txt

Three checks:
  1. PAIRWISE RULES   "paper A needs far more compute than paper B, so score(A) must be lower".
  2. COMPUTE TREND    Spearman correlation between the score and the GPU/TPU-hours the tool itself extracted.
  3. YOUR RANKING     optional: a text file, one case id per line, easiest first. Spearman against the score.
"""
import glob, json, math, os, re, sys

# (harder, easier, why). The harder paper must score LOWER than the easier one.
RULES = [
    ("big_02", "gpu_04", "PaLM (huge compute) vs YOLO (small compute)"),
    ("big_03", "gpu_12", "Llama 2 (huge compute) vs QLoRA (small compute)"),
    ("big_05", "gpu_03", "GPT-3 (huge compute) vs Faster R-CNN (small compute)"),
    ("big_01", "unk_04", "LLaMA (huge compute) vs DDIM (small compute)"),
    ("tpu_03", "tpu_04", "T5 (huge compute) vs DDPM (small compute)"),
    ("gpu_13", "gpu_02", "CLIP (huge compute) vs VGG (small compute)"),
    ("gpu_13", "gpu_11", "CLIP (huge compute) vs Latent Diffusion (small compute)"),
    ("gpu_10", "unk_01", "SAM (huge compute) vs ResNet (small compute)"),
    ("gpu_10", "gpu_04", "SAM (huge compute) vs YOLO (small compute)"),
    ("unk_07", "unk_04", "HuBERT (huge compute) vs DDIM (small compute)"),
]

# Papers that state no hardware at all must not look harder than any heavy-compute paper.
HEAVY = ["big_01", "big_02", "big_03", "big_04", "big_05", "tpu_03", "gpu_13", "gpu_14", "gpu_10"]
LIGHT = ["none_01", "none_02", "none_03", "none_04", "none_06", "none_07", "none_08"]


def load(path):
    data = json.load(open(path, encoding="utf-8"))
    out = {}
    for res in data:
        run = res["runs"][0]
        resp = run.get("response") or {}
        if run.get("status") == 200 and isinstance(resp, dict) and resp.get("student_feasibility_score") is not None:
            out[res["case"]["id"]] = resp
    return out


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    r = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    if len(a) < 3:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = math.sqrt(sum((x - ma) ** 2 for x in ra))
    vb = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return cov / (va * vb) if va and vb else None


def hours_of(resp):
    for flag in resp.get("hardware_flags", []):
        m = re.match(r"([\d,]+)\s+(?:GPU|TPU|accelerator)-hours", flag)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def main():
    args = sys.argv[1:]
    mine = None
    if "--mine" in args:
        i = args.index("--mine")
        mine = args[i + 1]
        del args[i:i + 2]
    path = args[0] if args else sorted(glob.glob(os.path.join(os.path.dirname(__file__) or ".", "results", "run_*.json")))[-1]
    scores = {k: v["student_feasibility_score"] for k, v in load(path).items()}
    print(f"results file: {path}  ({len(scores)} scored cases)\n")

    print("== 1. pairwise rules (harder paper must score lower) ==")
    bad = 0
    for hard, easy, why in RULES:
        if hard not in scores or easy not in scores:
            print(f"  SKIP  {hard} < {easy}   (missing result)   {why}")
            continue
        ok = scores[hard] < scores[easy]
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {hard}={scores[hard]:<3} < {easy}={scores[easy]:<3}   {why}")

    heavy = [scores[c] for c in HEAVY if c in scores]
    light = [scores[c] for c in LIGHT if c in scores]
    if heavy and light:
        mh, ml = sum(heavy) / len(heavy), sum(light) / len(light)
        ok = mh < ml
        bad += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  mean score of heavy-compute papers ({mh:.0f}) is below mean of no-hardware papers ({ml:.0f})")

    print("\n== 2. compute trend (score vs the tool's own extracted accelerator-hours) ==")
    pts = [(scores[k], math.log10(h)) for k, v in load(path).items() if k in scores and (h := hours_of(v))]
    rho = spearman([p[0] for p in pts], [p[1] for p in pts]) if pts else None
    if rho is None:
        print("  not enough cases with extracted hours")
    else:
        print(f"  {len(pts)} cases with hours, Spearman(score, log10 hours) = {rho:+.2f}   (strongly negative is good; below -0.6 expected)")

    if mine:
        print(f"\n== 3. your ranking ({mine}) ==")
        order = [l.strip() for l in open(mine, encoding="utf-8") if l.strip() and not l.startswith("#")]
        common = [c for c in order if c in scores]
        rho = spearman([order.index(c) for c in common], [-scores[c] for c in common])
        # order index 0 = easiest; -score so that a high score also means "easy" (rank 0)
        print(f"  {len(common)} cases ranked by you, Spearman = {rho:+.2f}   (1.0 = identical order)")
        worst = sorted(common, key=lambda c: abs(ranks([order.index(x) for x in common])[common.index(c)]
                                                 - ranks([-scores[x] for x in common])[common.index(c)]), reverse=True)[:5]
        print("  biggest disagreements:", ", ".join(f"{c} (you {order.index(c)+1}, tool score {scores[c]})" for c in worst))

    print(f"\n{'ALL RULES HOLD' if not bad else str(bad) + ' RULE(S) FAILED'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
