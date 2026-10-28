from chesscode.san_guard import extract_san, unknown_moves

def test_extract_san_basic():
    assert extract_san("Nxe5 and O-O") == ["Nxe5", "O-O"]

def test_extract_san_inside_devanagari():
    assert extract_san("अब Nxe5 आया") == ["Nxe5"]

def test_unknown_move_rejected():
    assert unknown_moves("Nxe5 Qh4+", {"Nxe5"}, set()) == ["Qh4+"]

def test_engine_line_move_allowed():
    assert unknown_moves("Nxe5", set(), {"Nxe5"}) == []
