from chesscode.san_guard import extract_san, unknown_moves

def test_extract_san_basic():
    assert extract_san("Nxe5 and O-O") == ["Nxe5", "O-O"]

def test_extract_san_inside_devanagari():
    assert extract_san("अब Nxe5 आया") == ["Nxe5"]

def test_unknown_move_rejected():
    assert unknown_moves("Nxe5 Qh4+", {"Nxe5"}, set()) == ["Qh4+"]

def test_engine_line_move_allowed():
    assert unknown_moves("Nxe5", set(), {"Nxe5"}) == []


def test_zero_castling_and_promotion_without_equals_are_extracted():
    assert extract_san("0-0 then 0-0-0 and e8Q") == ["0-0", "0-0-0", "e8Q"]
    assert extract_san("O-O+ and exd8=Q#") == ["O-O+", "exd8=Q#"]


def test_unknown_castling_and_promotion_are_rejected():
    assert unknown_moves("0-0-0", {"O-O"}, set()) == ["0-0-0"]
    assert unknown_moves("e8Q", {"e7"}, set()) == ["e8Q"]


def test_equivalent_spellings_match_the_game():
    assert unknown_moves("0-0 and e8Q", {"O-O", "e8=Q+"}, set()) == []


def test_check_suffix_may_be_omitted_or_added():
    assert unknown_moves("Rd8 Nf3+ Qxf7", {"Rd8#", "Nf3", "Qxf7+"}, set()) == []


def test_bare_square_is_not_a_move():
    assert unknown_moves("the pressure on e5 and the d4 square", {"Nf3"}, set()) == []
