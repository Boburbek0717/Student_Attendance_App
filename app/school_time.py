"""Display UTC database timestamps in the school's IANA timezone."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SCHOOL_ZONE = ZoneInfo("Asia/Tashkent")


def school_time(value: datetime) -> str:
    # SQLite returns naive UTC values. Never interpret them as machine-local time.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    local = value.astimezone(SCHOOL_ZONE)
    offset = local.strftime("%z")
    return f"{local:%Y-%m-%d %H:%M:%S} Asia/Tashkent (UTC{offset[:3]}:{offset[3:]})"
