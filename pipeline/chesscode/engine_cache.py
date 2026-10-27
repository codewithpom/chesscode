import json
import sqlite3
from pathlib import Path


class EngineCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS analysis (fen TEXT, depth INT, multipv INT, json TEXT, PRIMARY KEY(fen, depth, multipv))")

    def get(self, fen: str, depth: int, multipv: int) -> list[dict] | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT json FROM analysis WHERE fen=? AND depth=? AND multipv=?", (fen, depth, multipv)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, fen: str, depth: int, multipv: int, lines: list[dict]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR REPLACE INTO analysis VALUES (?, ?, ?, ?)", (fen, depth, multipv, json.dumps(lines)))
