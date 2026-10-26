from pydantic import StrictInt

MoneyCents = StrictInt


def available(total: int, committed: int) -> int:
    return total - committed
