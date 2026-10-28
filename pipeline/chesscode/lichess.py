import threading
import time

_REQUEST_LOCK = threading.Lock()


def export_game(source_id: str, session, sleep=time.sleep) -> str:
    url = f"https://lichess.org/game/export/{source_id}"
    headers = {"Accept": "application/x-chess-pgn"}
    params = {"clocks": "true", "evals": "false", "literate": "false"}
    with _REQUEST_LOCK:
        for attempt in range(3):
            response = session.get(url, params=params, headers=headers)
            if response.status_code == 429:
                if attempt == 2:
                    response.raise_for_status()
                    raise RuntimeError("Lichess rate limit retry limit reached")
                sleep(60)
                continue
            response.raise_for_status()
            return response.text
    raise RuntimeError("Lichess export failed")
