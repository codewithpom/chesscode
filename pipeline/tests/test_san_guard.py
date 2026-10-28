import pytest
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


def test_plain_prose_without_squares_is_unaffected():
    assert unknown_moves("A quiet positional squeeze, and the queen is trapped.", {"Nf3"}, set()) == []
    assert unknown_moves("अब राजा सुरक्षित है और हाथी खुला है", {"Nf3"}, set()) == []


def test_bare_square_must_be_a_destination_of_a_game_or_engine_move():
    assert unknown_moves("Black played d5", {"d6"}, set()) == ["d5"]
    assert unknown_moves("Black played d5", {"d5"}, set()) == []
    assert unknown_moves("the pawn lands on d5", {"exd5+"}, set()) == []          # capture destination
    assert unknown_moves("after e8 Queen", {"e8=Q"}, set()) == []                 # promotion destination
    assert unknown_moves("Black played d5", {"d6"}, {"d5"}) == []                 # engine line
    assert unknown_moves("Black played d5", {"d6"}, {"Nbd5"}) == []


def test_squares_the_pieces_start_on_are_referable():
    assert unknown_moves("the rook on a1 and the pawn on e2, the king on e8", {"Nf3"}, set()) == []


@pytest.mark.parametrize("text", ["knight to f6", "Knight f6", "queen takes h7", "pawn to e5", "king to g1"])
def test_spelled_out_move_without_a_matching_move_is_flagged(text):
    assert text in unknown_moves(text, {"Nf3", "Qh7", "d5", "Rg1"}, set())


def test_spelled_out_move_matches_piece_destination_and_capture():
    game = {"Nf6", "Qxh7+", "e5", "O-O"}
    assert unknown_moves("Then knight to f6, queen takes h7, pawn to e5 and the king to g1.", game, set()) == []
    assert unknown_moves("knight to f6", {"Nf3", "f6"}, set()) == ["knight to f6"]  # a pawn move to f6 is not a knight move
    assert unknown_moves("queen takes h7", {"Qh7"}, set()) == ["queen takes h7"]    # not a capture
    assert unknown_moves("rook to f6", set(), {"Rf6"}) == []                         # engine line


@pytest.mark.parametrize("text,san", [("घोड़ा f6", "Nf6"), ("नाइट f6", "Nf6"), ("हाथी d1", "Rd1"), ("रूक d1", "Rd1"), ("ऊँट b5", "Bb5"), ("बिशप b5", "Bb5"),
                                      ("वज़ीर h5", "Qh5"), ("रानी h5", "Qh5"), ("क्वीन h5", "Qh5"), ("राजा g1", "O-O"), ("किंग g1", "O-O"), ("प्यादा e5", "e5"), ("पॉन e5", "e5")])
def test_hindi_piece_names_with_a_square(text, san):
    sentence = f"अब {text} पर"
    assert unknown_moves(sentence, {san}, set()) == []
    assert text in unknown_moves(sentence, {"a3"}, set())
