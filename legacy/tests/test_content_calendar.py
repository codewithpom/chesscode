"""tests/test_content_calendar.py — sqlite-backed content queue."""

from content_calendar import ContentCalendar


def test_add_returns_new_row_id(tmp_path):
    cal = ContentCalendar(str(tmp_path / "test.db"))
    qid = cal.add(content_type="game", content_id="game.pgn", title="My Game")
    assert isinstance(qid, int)
    assert qid >= 1


def test_add_multiple_gives_increasing_ids(tmp_path):
    cal = ContentCalendar(str(tmp_path / "test.db"))
    id1 = cal.add(content_type="opening", content_id="Sicilian", title="Sicilian Video")
    id2 = cal.add(content_type="trap", content_id="Fried Liver", title="Trap Video")
    assert id2 > id1


def test_get_status_reflects_queued_items(tmp_path):
    cal = ContentCalendar(str(tmp_path / "test.db"))
    cal.add(content_type="game", content_id="a.pgn", title="A", priority=7)
    status = cal.get_status()
    assert len(status["queue"]) == 1
    assert status["queue"][0]["title"] == "A"
    assert status["queue"][0]["priority"] == 7
    assert status["scheduled"] == []


def test_default_priority_is_five(tmp_path):
    import sqlite3
    db_path = str(tmp_path / "test.db")
    cal = ContentCalendar(db_path)
    cal.add(content_type="game", content_id="a.pgn", title="A")

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT priority FROM content_queue").fetchone()
    conn.close()
    assert row[0] == 5
