"""Profile-freshness calculations (M1).

Single source of truth for `days_since_profile_update` so the API, the
stale-profile queries, and the tests all share the same boundary semantics:

- `None` (never substantively updated) counts as stale.
- Exactly `threshold_days` is NOT stale; only strictly greater is stale.
- Computed from the timestamp on read; never persisted as a counter.
"""

from datetime import datetime, timezone
from typing import Optional


def days_since(last_update: Optional[datetime], now: Optional[datetime] = None) -> Optional[int]:
    if last_update is None:
        return None
    at = now or datetime.now(timezone.utc)
    base = last_update
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    delta = at - base
    return max(0, delta.days)


def is_stale(
    last_update: Optional[datetime],
    threshold_days: int = 365,
    now: Optional[datetime] = None,
) -> bool:
    if last_update is None:
        return True
    days = days_since(last_update, now)
    assert days is not None
    return days > threshold_days
