import json, re, requests
import config

TIER_RANGES = {"extreme": (0, 40), "high": (10, 60), "medium": (35, 80), "low": (60, 100)}
INGEST_FAIL_TITLES = {"paper not found", "no paper provided"}
ORACLE_ERRORS = {}  # github_url -> why the GitHub lookup failed


def get(d, path, default=None):
    for k in path.split("."):
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d


def field(resp, name):
    return get(resp, config.FIELDS[name])


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def repo_oracle(github_url):
    """Ground truth straight from GitHub (no hand labels). Returns None and records why if it cannot."""
    owner_repo = github_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    h = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    try:
        r = requests.get(f"https://api.github.com/repos/{owner_repo}/contents", headers=h, timeout=30)
    except requests.RequestException as e:
        ORACLE_ERRORS[github_url] = f"network error: {type(e).__name__}"
        return None
    if r.status_code != 200:
        remaining = r.headers.get("X-RateLimit-Remaining")
        ORACLE_ERRORS[github_url] = (f"HTTP {r.status_code} (rate-limit remaining={remaining}, "
                                     f"token={'set' if config.GITHUB_TOKEN else 'NOT set'}): {r.text[:100]}")
        return None
    listing = r.json()
    if not isinstance(listing, list):
        ORACLE_ERRORS[github_url] = "unexpected response (not a directory listing)"
        return None
    names = {x["name"].lower() for x in listing}
    return {"requirements_txt": "requirements.txt" in names,
            "dockerfile": "dockerfile" in names,
            "environment_yml": bool(names & {"environment.yml", "environment.yaml"}),
            "pyproject": "pyproject.toml" in names}


def check_ingest(resp):
    title = str(resp.get("paper_title", "")).strip().lower()
    if title in INGEST_FAIL_TITLES:
        cites = resp.get("citations") or []
        extra = f"; also returned {len(cites)} unrelated citation(s)" if cites else ""
        return False, f"paper_title={resp.get('paper_title')!r} (arXiv fetch failed){extra}"
    src = resp.get("text_source", "full_text")
    if src != "full_text":
        return False, f"only the abstract was analysed (text_source={src}): the PDF text did not load"
    return True, ""


def check_schema(resp):
    missing = [f for f in config.REQUIRED_FIELDS if field(resp, f) is None]
    s = field(resp, "score")
    if missing: return False, f"missing {missing}"
    if not isinstance(s, (int, float)) or not 0 <= s <= 100: return False, f"bad score {s!r}"
    return True, ""


def check_gpu_match(resp, case):
    kws = case.get("gpu_keywords")
    if not kws: return None, ""
    hw = field(resp, "compute_text") or []
    blob = _norm(json.dumps(hw, default=str))
    miss = [k for k in kws if _norm(k) not in blob]
    return (not miss), (f"Expected {kws}, Got: {hw}" if miss else "")


def check_no_hallucination(resp, case):
    if case.get("gpu_mentioned") is not False: return None, ""
    gpus = field(resp, "gpus") or []
    ignore = {"", "unknown", "none", "not specified", "n/a", "extraction failed"}
    real = [g for g in gpus if str(g).strip().lower() not in ignore]
    return (not real), (f"Invented hardware {real}" if real else "")


def check_tier(resp, case):
    t = case.get("tier")
    if not t: return None, ""
    lo, hi = TIER_RANGES[t]; s = field(resp, "score")
    return (s is not None and lo <= s <= hi), f"score {s} outside {lo}-{hi} for {t}"


def check_repo_flags(resp, oracle):
    if not oracle: return None, ""
    if resp.get("github_metrics") is None:
        return False, "github_metrics is null although a repo URL was sent (the backend's GitHub lookup failed: check GITHUB_TOKEN in backend/.env)"
    deps_str = str(field(resp, "repo_requirements_txt") or []).lower()
    has_req, has_dock = "requirements.txt" in deps_str, "dockerfile" in deps_str
    bad = []
    if has_req != oracle["requirements_txt"]:
        bad.append(f"requirements_txt: tool={has_req} github={oracle['requirements_txt']}")
    if has_dock != oracle["dockerfile"]:
        bad.append(f"dockerfile: tool={has_dock} github={oracle['dockerfile']}")
    return (not bad), "; ".join(bad)


def check_scaffold(resp, oracle):
    # Scaffold lives on /api/scaffold, tested separately.
    return None, ""


def grade_case(case, status, resp, latency):
    g = {}
    if case["expect_error"]:
        ok_codes = {400, 403, 404, 422} | ({500} if getattr(config, "ALLOW_500_AS_ERROR", False) else set())
        body_err = isinstance(resp, dict) and ("error" in resp or str(resp.get("paper_title", "")).strip().lower() in INGEST_FAIL_TITLES)
        graceful = status in ok_codes or (status == 200 and body_err)
        g["graceful_error"] = {"passed": bool(graceful), "detail": f"HTTP {status}"}
        return g

    detail = f"HTTP {status}"
    if status != 200 and isinstance(resp, dict):
        detail += f": {resp.get('detail') or resp.get('_raw') or ''}"
    g["http_ok"] = {"passed": status == 200, "detail": detail}
    if status != 200 or not isinstance(resp, dict):
        return g

    p, d = check_ingest(resp)
    g["ingest"] = {"passed": p, "detail": d}
    if not p:
        return g  # downstream checks would only re-measure the fetch failure

    oracle = None
    if case.get("expect_no_repo_metrics"):
        # valid paper + nonexistent repo: the tool should still analyse the paper and report no repo metrics
        ok = resp.get("github_metrics") is None
        g["degrades_gracefully"] = {"passed": ok, "detail": "" if ok else "returned repo metrics for a repo that does not exist"}
    elif case.get("github_url"):
        oracle = repo_oracle(case["github_url"])
        if oracle is None:
            g["oracle"] = {"passed": False, "detail": f"GitHub lookup failed: {ORACLE_ERRORS.get(case['github_url'], 'unknown')}"}

    for name, (p, d) in {
        "schema": check_schema(resp),
        "gpu_match": check_gpu_match(resp, case),
        "no_hallucination": check_no_hallucination(resp, case),
        "tier_score": check_tier(resp, case),
        "repo_flags": check_repo_flags(resp, oracle),
        "scaffold": check_scaffold(resp, oracle),
    }.items():
        g[name] = {"passed": p, "detail": d}
    return g
