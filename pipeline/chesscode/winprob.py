import math


def win_pct(cp: int | None, mate: int | None) -> float:
    if mate is not None:
        return 100.0 if mate > 0 else 0.0
    if cp is None:
        raise ValueError("either cp or mate must be provided")
    return 50 + 50 * (2 / (1 + math.exp(-0.00368208 * cp)) - 1)
