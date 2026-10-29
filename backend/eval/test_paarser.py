"""Offline pytest for your fault-tolerant JSON parser in llm.py. No API calls, runs in <1s.
EDIT the import + function name to match your code."""
import pytest
from app.services.llm import parse_llm_json   # <-- change to your real path/function

CASES = [
 ('{"gpus": ["A100"], "score": 40}', {"gpus": ["A100"], "score": 40}),                       # clean
 ('```json\n{"gpus": ["A100"], "score": 40}\n```', {"gpus": ["A100"], "score": 40}),           # fenced
 ('Here is the result:\n{"gpus": [], "score": 90}\nHope this helps!', {"gpus": [], "score": 90}),  # chatter
 ('{"gpus": ["A100"], "score": 40,}', {"gpus": ["A100"], "score": 40}),                       # trailing comma
 ("{'gpus': ['A100'], 'score': 40}", {"gpus": ["A100"], "score": 40}),                        # single quotes
]
@pytest.mark.parametrize("raw,expected", CASES)
def test_recovers(raw, expected):
    assert parse_llm_json(raw) == expected

@pytest.mark.parametrize("raw", ["", "I cannot help with that.", '{"gpus": ["A100"', "null", "[]"])
def test_garbage_never_raises(raw):
    out = parse_llm_json(raw)            # must return a safe default / None, not throw
    assert out is None or isinstance(out, dict)

def test_truncated_json_flagged_not_trusted():
    out = parse_llm_json('{"gpus": ["A100"], "score": 4')
    assert out is None or out.get("score") != 4   # don't silently accept a half-cut number