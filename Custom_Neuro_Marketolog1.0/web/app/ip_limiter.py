from datetime import date

_MAX_DAILY = 4  # 1 diagnostic + 3 restarts

_store: dict[str, dict] = {}


def is_allowed(ip: str) -> bool:
    today = date.today()
    entry = _store.get(ip)

    if entry is None or entry["date"] != today:
        _store[ip] = {"date": today, "count": 1}
        return True

    if entry["count"] >= _MAX_DAILY:
        return False

    entry["count"] += 1
    return True
