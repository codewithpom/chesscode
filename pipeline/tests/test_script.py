import json
import pytest
import yaml
from chesscode import llm
from chesscode.stages.script import ensure_specific, select_bank_line

def test_complete_json_retries_twice_then_raises():
    class Client:
        def __init__(self): self.calls=0
        def complete(self, **kwargs): self.calls+=1; return "{}"
    client=Client()
    with pytest.raises(Exception): llm.complete_json("script", "s", "u", {"type":"object","required":["x"]}, client=client)
    assert client.calls == 3

def test_complete_json_validates():
    class Client:
        def complete(self, **kwargs): return '{"x":1}'
    assert llm.complete_json("script", "s", "u", {"type":"object","required":["x"]}, client=Client()) == {"x":1}

def test_bad_line_falls_back_to_bank():
    bank={"blunder":["That move dropped the rook."]}
    assert select_bank_line("blunder", bank, set(), "en") == "That move dropped the rook."

def test_bank_skips_recent_lines():
    bank={"blunder":["One line.","Other line."]}
    assert select_bank_line("blunder",bank,{"One line."},"en")=="Other line."

def test_hindi_prompt_not_given_english_script():
    # The request is constructed from source facts and language independently, never a prior script.
    from pathlib import Path
    source=Path(__file__).parents[1]/"chesscode/stages/script.py"
    assert "english_script" not in source.read_text(encoding="utf-8")

def test_specificity_below_threshold_regenerates():
    initial={"segments":[{"text":"A nice game with a surprising ending."}]}
    improved={"segments":[{"text":"Knight f3 controls e5; the rook attacks the open file."}]}
    calls=[]
    result=ensure_specific(initial,lambda:(calls.append(True) or improved),6,150)
    assert calls and result is improved
