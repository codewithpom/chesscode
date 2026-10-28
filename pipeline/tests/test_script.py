import json
from pathlib import Path
from chesscode.context import StageError
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

def messages_client(stop_reason, text='{"x":1}', seen=None):
    class Block:
        type = "text"
        def __init__(self): self.text = text
    class Messages:
        def create(self, **kwargs):
            if seen is not None: seen.append(kwargs)
            return type("R", (), {"content": [Block()], "stop_reason": stop_reason})()
    return type("C", (), {"messages": Messages()})()

def test_truncated_response_fails_clearly_without_retrying():
    from chesscode.context import StageError
    seen = []
    with pytest.raises(StageError, match="max_tokens 16384.*config/models.yaml"):
        llm.complete_json("script_hi", "s", "u", {"type": "object"}, client=messages_client("max_tokens", seen=seen))
    assert len(seen) == 1

def test_max_tokens_comes_from_config_and_hindi_has_more_headroom():
    seen = []
    for key in ("script", "script_hi"):
        assert llm.complete_json(key, "s", "u", {"type": "object"}, client=messages_client("end_turn", seen=seen)) == {"x": 1}
    assert seen[1]["max_tokens"] > seen[0]["max_tokens"] >= 8192

def test_script_stage_asks_for_the_hindi_budget(tmp_path):
    import test_script_run as t
    keys = []
    fake, _ = t.model([t.out()])
    ctx_holder = {}
    def spy(key, *a):
        keys.append(key); return fake(key, *a)
    mp = pytest.MonkeyPatch()
    try:
        ctx = t.setup_run(tmp_path, mp, language="hi")
        mp.setattr(t.script.llm, "complete_json", spy)
        t.script.run(ctx)
    finally: mp.undo()
    assert {k for k in keys if k != "checks"} == {"script_hi"}

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


def test_offline_client_writes_request_then_reads_committed_answer(tmp_path):
    client = llm.OfflineClient(tmp_path)
    with pytest.raises(llm.AnswerMissing) as missing:
        client.complete(model=llm.load("models")["script"], system="s", user="u", schema={"type": "object"})
    request = json.loads(Path(missing.value.request).read_text(encoding="utf-8"))
    assert request["user"] == "u" and request["schema"] == {"type": "object"}
    answer = tmp_path / request["answer_path"]
    answer.parent.mkdir(parents=True)
    answer.write_text('{"x": 1}', encoding="utf-8")
    assert llm.complete_json("script", "s", "u", {"type": "object"}, client=llm.OfflineClient(tmp_path)) == {"x": 1}
    assert not Path(missing.value.request).exists()  # answered requests are cleared


def test_offline_answer_missing_is_a_stage_error_naming_the_request(tmp_path):
    with pytest.raises(StageError, match="llm_requests"):
        llm.complete_json("checks", "s", "u", {"type": "object"}, client=llm.OfflineClient(tmp_path))


def test_offline_invalid_answer_names_the_file_and_keeps_the_request(tmp_path):
    with pytest.raises(StageError):
        llm.complete_json("checks", "s", "u", {"type": "object", "required": ["bad"]}, client=llm.OfflineClient(tmp_path))
    request = next((tmp_path / "build" / "llm_requests").glob("*.json"))
    answer = tmp_path / json.loads(request.read_text(encoding="utf-8"))["answer_path"]
    answer.parent.mkdir(parents=True)
    answer.write_text('{"x": 1}', encoding="utf-8")
    with pytest.raises(StageError, match="llm_answers"):
        llm.complete_json("checks", "s", "u", {"type": "object", "required": ["bad"]}, client=llm.OfflineClient(tmp_path))
    assert request.exists()


def test_unknown_provider_is_refused(monkeypatch):
    monkeypatch.setattr(llm, "load", lambda name: {"provider": "anthopic"})
    with pytest.raises(StageError, match="provider"):
        llm.provider()
