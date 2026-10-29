import os
import json
import re
import ast
import hashlib
from pathlib import Path
from groq import AsyncGroq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# max_retries lets the SDK back off and retry on Groq 429 / 5xx by itself
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY"), max_retries=4)
MODEL = "openai/gpt-oss-20b"

# Optional on-disk cache of the LLM's parsed answer (OFF by default, meant for development/eval runs).
# Groq's free tier allows 200k tokens/day, a full 50-paper eval uses most of that; with the cache, re-running the
# eval (or tuning the scoring formula, which now lives in Python) costs zero tokens.
# Turn on with:  $env:GT_LLM_CACHE = "1"   before starting uvicorn.
# The key includes the model, the prompt and the selected text, so changing any of them re-queries the LLM.
USE_CACHE = os.environ.get("GT_LLM_CACHE", "") == "1"
CACHE_DIR = Path(__file__).resolve().parents[2] / ".llm_cache"  # backend/.llm_cache


def _cache_key(focused: str) -> str:
    return hashlib.sha256((MODEL + "\n" + SYSTEM_PROMPT + "\n" + focused).encode("utf-8")).hexdigest()[:32]


def _cache_get(key: str):
    try:
        return json.loads((CACHE_DIR / f"{key}.json").read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_put(key: str, data: dict) -> None:
    try:
        CACHE_DIR.mkdir(exist_ok=True)
        (CACHE_DIR / f"{key}.json").write_text(json.dumps(data), encoding="utf-8")
    except Exception as e:
        print(f"DEBUG: could not write LLM cache: {e}")


def parse_llm_json(raw_content: str) -> dict | None:
    """
    Extracts JSON blocks from conversational text, fixes trailing commas/single quotes,
    and gracefully returns None on complete failure.
    """
    content = raw_content.strip()

    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    match = re.search(r'\{.*\}', content, re.DOTALL)
    if not match:
        return None

    content = match.group(0)

    try:
        result = json.loads(content)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    try:
        result = ast.literal_eval(content)
        if isinstance(result, dict):
            return result
    except (SyntaxError, ValueError):
        pass

    return None


# ---------------------------------------------------------------------------
# 1. Pick the passages that talk about compute instead of cutting the paper at N chars
# ---------------------------------------------------------------------------
STRONG = re.compile(r"gpu|tpu|a100|v100|h100|p100|a6000|rtx|nvidia|cuda|accelerator", re.I)
WEAK = re.compile(
    r"\b(?:nodes?|cluster|hardware|vram|tflops|petaflops?|trained on|training time|wall[- ]clock|days|weeks|memory)\b",
    re.I,
)


def select_relevant_text(text: str, max_chars: int = 14000, head_chars: int = 3500, max_sentence: int = 600) -> str:
    """Keeps the title/abstract/intro, then adds the sentences (plus neighbours) that mention hardware."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text

    head, body = text[:head_chars], text[head_chars:]
    sentences = [s[:max_sentence] for s in re.split(r"(?<=[.!?])\s+", body)]
    scores = [3 * len(STRONG.findall(s)) + len(WEAK.findall(s)) for s in sentences]

    budget = max_chars - len(head)
    keep, used = set(), 0
    for idx in sorted(range(len(sentences)), key=lambda i: -scores[i]):
        if scores[idx] == 0 or used >= budget:
            break
        for j in (idx - 1, idx, idx + 1):
            if 0 <= j < len(sentences) and j not in keep:
                used += len(sentences[j]) + 1
                keep.add(j)

    picked = " ".join(sentences[i] for i in sorted(keep))
    return f"{head}\n\n[Passages mentioning compute/hardware]\n{picked}"


# ---------------------------------------------------------------------------
# 2. Score in Python from extracted facts (the LLM no longer picks the number)
# ---------------------------------------------------------------------------
HIGH_END = re.compile(r"h100|h200|a100|a800|mi250|mi300")
MID_RANGE = re.compile(r"v100|p100|a6000|a40|l40|rtx ?(?:3090|4090)|titan|k80|k40")


def compute_feasibility(f: dict) -> int:
    """
    0-100, higher = easier for an undergraduate to reproduce.
    Starting formula: every number below is a knob, tune it against your golden set.
    """
    if not (f["models"] or f["count"] or f["hours"] or f["params_b"]):
        return 75  # nothing stated: unknown, not proven easy

    score = 90
    blob = (" ".join(f["models"]) + " " + f["kind"]).lower()

    # accelerator class
    if "tpu" in blob:
        score -= 25
    elif HIGH_END.search(blob):
        score -= 20
    elif MID_RANGE.search(blob):
        score -= 8
    elif f["models"] or f["count"]:
        score -= 5

    # how many accelerators
    n = f["count"] or 0
    if n >= 1000:
        score -= 40
    elif n >= 100:
        score -= 30
    elif n >= 16:
        score -= 22
    elif n >= 8:
        score -= 15
    elif n >= 2:
        score -= 6

    if f["multi_node"] and (f["models"] or f["count"]):
        score -= 10

    # total compute
    h = f["hours"] or 0
    if h >= 100_000:
        score -= 20
    elif h >= 10_000:
        score -= 12
    elif h >= 1_000:
        score -= 6

    # model size (papers state this even when they never state a GPU count)
    p = f["params_b"] or 0
    if p >= 100:
        score -= 35
    elif p >= 30:
        score -= 25
    elif p >= 10:
        score -= 15
    elif p >= 3:
        score -= 8
    elif p >= 1:
        score -= 4

    # pretraining a big model from scratch is out of reach, fine-tuning/inference is a different story
    if f["from_scratch"] and p >= 10:
        score -= 15

    return max(5, min(100, int(score)))


def _as_list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip().lower() not in {"", "none", "null", "n/a", "unknown"}:
        return [v.strip()]
    return []


def _as_num(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        n = float(str(v).replace(",", "").strip())
    except ValueError:
        return None
    return n if n > 0 else None


def _as_str(v) -> str:
    s = str(v).strip() if v is not None else ""
    return "" if s.lower() in {"", "none", "null", "n/a", "unknown", "not stated"} else s


def _as_bool(v) -> bool:
    return v is True or str(v).strip().lower() == "true"


_WORD_NUMS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
              "nine": 9, "ten": 10}
_DURATION = re.compile(
    r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\s*(?:[-–—]|to)?\s*(\d+(?:\.\d+)?)?\s*"
    r"(hours?|hrs?|days?|weeks?)\b", re.I)


def _duration_hours(text: str):
    """'3.5 days' -> 84, '2-3 weeks' -> 504 (upper end), 'approximately one day' -> 24. None if not parseable."""
    m = _DURATION.search(text or "")
    if not m:
        return None
    def num(s):
        return _WORD_NUMS.get(s.lower()) if s and s.lower() in _WORD_NUMS else float(s)
    a = num(m.group(1))
    b = num(m.group(2)) if m.group(2) else None
    value = max(a, b) if b is not None else a
    unit = m.group(3).lower()
    per = 1 if unit.startswith(("h")) else 24 if unit.startswith("d") else 168
    return value * per


_NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                 7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
_CITATION = re.compile(r"et al\.?,?\s*\(?(?:19|20)\d{2}|\([^()]*\b(?:19|20)\d{2}[a-z]?\)", re.I)
_FIRST_PERSON = re.compile(r"\b(we|our|ours|us)\b", re.I)


def _count_is_third_party(count: float, text: str) -> bool:
    """True only when the evidence for `count` accelerators is clearly someone else's work.

    Looks at every sentence that puts the number right next to a GPU/TPU word. The count is rejected only
    if there is at least one such sentence AND every one of them cites another paper ("(Amodei et al., 2015)")
    AND none of them speaks in the first person ("we train ... on 16 GPUs").
    If no sentence matches (for example a count the model derived from "2 16-GPU nodes"), the count is left
    alone, so this guard can only remove a claim, never invent or change one.
    """
    if not text or not count:
        return False
    n = int(count)
    forms = [str(n)] + ([_NUMBER_WORDS[n]] if n in _NUMBER_WORDS else [])
    pat = re.compile(r"\b(?:" + "|".join(forms) + r")[\s\-]*(?:x\s*)?(?:\w+\s+){0,2}(?:gpus?|tpus?|accelerators?|chips?)\b", re.I)
    sentences = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    hits = [s for s in sentences if pat.search(s)]
    if not hits:
        return False
    return all(_CITATION.search(s) and not _FIRST_PERSON.search(s) for s in hits)


_ACCEL_NAME = re.compile(
    r"\b(H100|H200|A100|A800|V100|P100|K80|K40|A6000|A40|L40|RTX ?(?:3090|4090)|Titan(?: [XV])?)\b", re.I)


def _own_accelerator_names(text: str) -> list[str]:
    """Accelerator names in first-person, non-citing sentences ("we train ... on a single A100")."""
    names = []
    for s in re.split(r"(?<=[.!?])\s+", (text or "").replace("\n", " ")):
        if _FIRST_PERSON.search(s) and not _CITATION.search(s):
            for m in _ACCEL_NAME.finditer(s):
                n = re.sub(r"\s+", " ", m.group(1)).upper()
                if n not in names:
                    names.append(n)
    return names


def _build_result(d: dict, source_text: str = "") -> dict:
    raw_kind = _as_str(d.get("accelerator_kind")).upper()
    models = _as_list(d.get("accelerator_models"))
    count = _as_num(d.get("accelerator_count"))
    hours = _as_num(d.get("accelerator_hours"))
    memory_gb = _as_num(d.get("accelerator_memory_gb"))
    multi_node_claim = _as_bool(d.get("multi_node"))
    if raw_kind == "CPU":  # CPU-only training is not an accelerator requirement
        models, count, hours, memory_gb = [], None, None, None
    elif count and not models and not memory_gb and _count_is_third_party(count, source_text):
        # Count-only claim whose only support is a cited sentence about another paper's setup
        # (e.g. Whisper's related work describing Deep Speech 2 on 16 GPUs). Treat as not stated.
        print(f"[DEBUG] Dropped ungrounded accelerator count {count:g}: only supported by cited third-party sentences")
        count, hours, multi_node_claim = None, None, False

    if count and not models and not memory_gb and raw_kind != "CPU":
        # The model reported a count but left the model name out. If the text names exactly one accelerator in a
        # first-person, non-citing sentence, recover it. Ambiguous (several names) -> leave it alone.
        found = _own_accelerator_names(source_text)
        if len(found) == 1:
            print(f"[DEBUG] Model omitted the accelerator name; recovered {found[0]} from a first-person sentence")
            models = found

    kind = raw_kind if raw_kind in {"GPU", "TPU"} else ""
    if any("tpu" in m.lower() for m in models):
        kind = "TPU"
    elif models and not kind:
        kind = "GPU"
    if not kind and (count or memory_gb):
        # The model left the type empty. Infer it only from the text itself: if the paper mentions
        # GPUs but never TPUs (or the other way round), that is what the count refers to.
        says_gpu = re.search(r"\bgpus?\b", source_text, re.I)
        says_tpu = re.search(r"\btpus?\b", source_text, re.I)
        if says_gpu and not says_tpu:
            kind = "GPU"
        elif says_tpu and not says_gpu:
            kind = "TPU"
    if memory_gb and not models and kind != "TPU":
        # e.g. "finetune a 65B model on a single 48GB GPU": no model name, only a memory size
        models = [f"{memory_gb:g}GB GPU"]
        kind = kind or "GPU"

    multi_node = multi_node_claim
    training_time = _as_str(d.get("training_time"))

    # The model sometimes reports the wall-clock training time as "accelerator hours" (e.g. 4 days -> 96,
    # with 16 chips). Real accelerator-hours = count x wall-clock. If the reported hours equal the stated
    # training time and several accelerators were used, scale by the count.
    wall_h = _duration_hours(training_time)
    if count and count > 1 and hours and wall_h and abs(hours - wall_h) / wall_h <= 0.05:
        print(f"[DEBUG] accelerator_hours {hours:g} equals wall-clock time; scaling by count {count:g}")
        hours = hours * count

    # hardware_flags is built from the structured facts only, so vague statements such as
    # "low memory footprint" or "computationally efficient" can never end up in it.
    flags: list[str] = []
    if models or count:
        device = ", ".join(models) if models else (kind or "accelerator")
        if models and not re.search(r"gpu|tpu", device, re.I):
            device = f"{device} {kind or 'GPU'}"
        flags.append(f"{int(count)}x {device}" if count else device)
    if hours:
        flags.append(f"{hours:,.0f} {kind or 'accelerator'}-hours")
    if (models or count) and training_time:
        flags.append(f"training time: {training_time}")
    if (models or count) and multi_node:
        flags.append("multi-node cluster")

    facts = {
        "models": models,
        "kind": kind,
        "count": count,
        "hours": hours,
        "multi_node": multi_node,
        "params_b": _as_num(d.get("largest_model_params_billions")),
        "from_scratch": _as_bool(d.get("trains_from_scratch")),
    }
    dataset = d.get("dataset_mentioned")
    dataset = dataset.strip() if isinstance(dataset, str) and dataset.strip() else "None"

    return {
        "hardware_flags": flags,
        "dataset_mentioned": dataset,
        "student_feasibility_score": compute_feasibility(facts),
        "facts": facts,
    }


SYSTEM_PROMPT = """You are an expert AI engineering assistant analyzing research papers for undergraduate students.
Extract ONLY compute facts that the paper explicitly states. Never guess, never infer hardware from the model
size or from common practice, never fill in typical values. If a fact is not stated, use null (or an empty list).
Statements such as "low memory footprint", "computationally efficient", "real-time speed", or "requires large
compute" are NOT hardware facts and must not be reported. If several experiments are described, report the largest
training run.
Only report hardware that the authors of THIS paper used for their own experiments. Ignore hardware that was used
to train third-party models the paper merely evaluates, prompts, or builds on (a paper that prompts PaLM does not
inherit the TPUs that PaLM was trained on).
Use the paper's own words: "a single GPU" means accelerator_count 1; if only a memory size is given (for example
"a single 48GB GPU") put 48 in accelerator_memory_gb. Whenever you report a model, a count, or a memory size,
also set accelerator_kind to what the paper says it is (GPU, TPU or CPU).
If the text names the accelerator model that this paper's authors used (for example "NVIDIA A100"), always put it in
accelerator_models, even when the count is stated in a different sentence. Do not leave accelerator_models empty when such a name appears.
Respond with ONLY a JSON object: no markdown, no backticks, no explanation.

Format:
{
    "accelerator_models": ["specific GPU/TPU models the paper names, e.g. 'A100', 'V100', 'TPU v3', 'Titan X'; [] if none"],
    "accelerator_kind": "GPU", "TPU", "CPU", or null,
    "accelerator_count": integer number of GPUs or TPU chips used for one training run, or null,
    "accelerator_memory_gb": memory per GPU in GB if the paper gives a memory size instead of a model name, or null,
    "accelerator_hours": total GPU/TPU hours as a number, or null,
    "training_time": "wall-clock training time as written in the paper, e.g. '3.5 days', or null",
    "multi_node": true if the paper states training across multiple machines/nodes/pods, otherwise false,
    "largest_model_params_billions": number, the largest model the paper trains or evaluates in billions of parameters (110M = 0.11), or null,
    "trains_from_scratch": true only if the paper itself pretrains/trains that model from scratch (not fine-tuning, not API use),
    "dataset_mentioned": "Name of the primary dataset used, or 'None'"
}"""


async def extract_engineering_constraints(paper_text: str) -> dict:
    """Returns the extracted fields, or {"error": "..."} if the LLM step failed."""
    focused = select_relevant_text(paper_text)
    last_error = "unknown error"

    key = _cache_key(focused) if USE_CACHE else None
    if key:
        cached = _cache_get(key)
        if cached is not None:
            print("[DEBUG] LLM cache hit (no tokens used)")
            return _build_result(cached, focused)

    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract constraints from this text:\n\n{focused}"},
                ],
                model=MODEL,
                temperature=0.0,
                max_tokens=4000,  # gpt-oss is a reasoning model: reasoning tokens count against this
                extra_body={"reasoning_effort": "low"},
            )
            choice = response.choices[0]
            raw = (choice.message.content or "").strip()
            print(f"\n[DEBUG] RAW LLM OUTPUT (attempt {attempt + 1}, finish_reason={choice.finish_reason}):\n{raw[:800]}\n")

            data = parse_llm_json(raw)
            if data is None:
                last_error = f"unparseable LLM output (finish_reason={choice.finish_reason}, empty={not raw})"
                continue
            print(f"[DEBUG] LLM raw facts: {json.dumps(data)[:600]}")
            if key:
                _cache_put(key, data)
            return _build_result(data, focused)
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"DEBUG: Groq API Error (attempt {attempt + 1}): {last_error}")

    return {"error": last_error}


async def generate_environment_scaffold(github_url: str, hardware_flags: list, missing_files: list) -> dict:
    """Generates the missing setup files by asking for plain text and wrapping it in Python."""

    hw_context = ", ".join(hardware_flags) if hardware_flags else "Standard CPU/GPU compute"
    files_context = ", ".join(missing_files) if missing_files else "requirements.txt and Dockerfile"

    system_prompt = """You are an AI DevOps Engineer. Write the required setup script (Dockerfile or bash).
CRITICAL: Output ONLY the raw code. Do NOT use markdown code blocks (like ```bash). Do NOT add conversational text or explanations. Just the code."""

    user_prompt = f"""Repository: {github_url}
Constraints: {hw_context}
Missing: {files_context}"""

    try:
        raw_content = ""
        for attempt in range(2):  # a reasoning model can spend its whole budget thinking and return nothing
            response = await client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=MODEL,
                temperature=0.0,
                max_tokens=4000,  # reasoning tokens count against this
                extra_body={"reasoning_effort": "low"},
            )
            raw_content = (response.choices[0].message.content or "").strip()
            if raw_content:
                break
            print(f"DEBUG: Scaffold attempt {attempt + 1} returned empty content "
                  f"(finish_reason={response.choices[0].finish_reason})")
        if not raw_content:
            raise ValueError("LLM returned empty scaffold twice")

        if raw_content.startswith("```"):
            lines = raw_content.split("\n")
            if len(lines) > 2:
                raw_content = "\n".join(lines[1:-1]).strip()
            else:
                raw_content = raw_content.replace("```", "").replace("bash", "").replace("dockerfile", "").strip()

        return {
            "setup_script": raw_content,
            "explanation": "Auto-generated environment configuration based on extracted hardware constraints."
        }

    except Exception as e:
        print(f"DEBUG: Scaffold Generation Error: {e}")
        return {
            "setup_script": "# Error generating scaffold. Please create environments manually.",
            "explanation": "Failed to connect to the LLM engine."
        }