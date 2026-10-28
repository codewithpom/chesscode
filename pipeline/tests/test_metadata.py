from chesscode.stages.metadata import build_description, pick_title

def test_description_ends_with_ccid():
    assert build_description("Hook",[{"title":"Opening","start_ms":0}],{"white":{"name":"A"},"black":{"name":"B"},"event":"Event","date":"2020","result":"1-0","opening":"Open","source":"lichess"},"Legendary",[],"cc-2026-0001-en").endswith("ccid: cc-2026-0001-en")

def test_description_chapters_start_0000():
    result=build_description("Hook",[{"title":"Opening","start_ms":0}],{},"S",[],"id")
    assert "00:00 Opening" in result

def test_short_hash_preserves_footer():
    assert build_description("Hook",[],{},"S",[],"cc-2026-5001-en").endswith("ccid: cc-2026-5001-en")
    assert "#Shorts" in build_description("Hook",[],{},"S",[],"cc-2026-5001-en")

def test_title_rejects_all_caps_and_long():
    assert pick_title(["THIS IS BAD", "x"*71, "A clever chess story"], lambda titles: titles[0]) == "A clever chess story"
