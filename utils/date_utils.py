from datetime import datetime
from zoneinfo import ZoneInfo


def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def now_channel_time(timezone_name: str) -> str:
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception:
        timezone = ZoneInfo("Europe/Madrid")

    return datetime.now(timezone).strftime("%d.%m.%Y, %H:%M")
