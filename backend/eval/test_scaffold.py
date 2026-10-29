"""Checks /api/scaffold output quality. Needs the server running; costs ~1.5K Groq tokens per case.

    python test_scaffold.py
"""
import subprocess, sys, tempfile, os
import requests

URL = "http://localhost:8000/api/scaffold"
REPO = "https://github.com/pytorch/examples"

CASES = [
    ("gpu flags -> CUDA", dict(github_url=REPO, hardware_flags=["8x A100 GPU", "672 GPU-hours"], missing_files=["Dockerfile", "requirements.txt"]), "cuda"),
    ("single gpu -> CUDA", dict(github_url=REPO, hardware_flags=["1x 48GB GPU"], missing_files=["Dockerfile"]), "cuda"),
    ("no hardware -> not CUDA", dict(github_url=REPO, hardware_flags=[], missing_files=["requirements.txt", "Dockerfile"]), "nocuda"),
    ("cpu only -> not CUDA", dict(github_url=REPO, hardware_flags=["CPU only"], missing_files=["Dockerfile"]), "nocuda"),
    ("no missing files", dict(github_url=REPO, hardware_flags=["1x GPU"], missing_files=[]), None),
]
FALLBACK = "# Error generating scaffold"


def check(name, payload, cuda):
    problems = []
    r = requests.post(URL, json=payload, timeout=90)
    if r.status_code != 200:
        return [f"HTTP {r.status_code}: {r.text[:150]}"], ""
    body = r.json()
    script = body.get("setup_script", "")
    low = script.lower()
    if not script.strip():
        problems.append("empty script")
    if FALLBACK in script:
        problems.append("returned the error-fallback text")
    if "```" in script:
        problems.append("markdown fences left in output")
    first = next((l.strip() for l in script.splitlines() if l.strip()), "")
    if first.upper().startswith(("HERE", "SURE", "CERTAINLY", "BELOW")):
        problems.append(f"chat preamble: {first[:50]}")
    if cuda == "cuda" and "cuda" not in low and "nvidia" not in low:
        problems.append("GPU hardware but no CUDA/NVIDIA reference")
    if cuda == "nocuda" and ("nvidia/cuda" in low or "cudatoolkit" in low):
        problems.append("no GPU needed but script installs CUDA")
    if first.upper().startswith("FROM") or "\nFROM " in script:
        pass
    elif first.startswith("#!"):
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
            f.write(script)
        res = subprocess.run(["bash", "-n", f.name], capture_output=True, text=True)
        os.unlink(f.name)
        if res.returncode:
            problems.append("bash syntax error: " + res.stderr.strip()[:100])
    else:
        problems.append(f"not recognisably a Dockerfile or bash script (starts: {first[:40]})")
    return problems, script


def main():
    bad = 0
    for name, payload, cuda in CASES:
        try:
            problems, script = check(name, payload, cuda)
        except Exception as e:
            problems, script = [f"request failed: {e}"], ""
        bad += bool(problems)
        print(f"{'ok  ' if not problems else 'FAIL'}  {name}")
        for p in problems:
            print("        -", p)
        if problems and script:
            print("        first lines:", " | ".join(script.splitlines()[:3])[:150])
    r = requests.post(URL, json=dict(github_url="", hardware_flags=[], missing_files=[]), timeout=30)
    ok = r.status_code == 400
    bad += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  empty github_url -> 400 (got {r.status_code})")
    print(f"\n{len(CASES) + 1 - bad}/{len(CASES) + 1} passed")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
