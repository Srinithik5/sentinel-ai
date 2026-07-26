from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def local_to_utc(local_dt: datetime, tz_name: str) -> datetime:
    localized = local_dt.replace(tzinfo=ZoneInfo(tz_name))
    return localized.astimezone(ZoneInfo("UTC"))


def random_business_timestamp(
    day: date,
    start_hour: int,
    end_hour: int,
    tz_name: str,
    rng: random.Random,
) -> datetime:
    window_minutes = max(1, (end_hour - start_hour) * 60)
    offset_minutes = rng.randint(0, window_minutes - 1)
    local_dt = datetime(day.year, day.month, day.day, start_hour, 0, 0) + timedelta(
        minutes=offset_minutes, seconds=rng.randint(0, 59)
    )
    return local_to_utc(local_dt, tz_name)


def random_timestamp_at_hour(day: date, hour: int, tz_name: str, rng: random.Random) -> datetime:
    local_dt = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59))
    return local_to_utc(local_dt, tz_name)


def date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]