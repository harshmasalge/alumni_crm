from datetime import datetime, timedelta, timezone

from app.services.freshness import days_since, is_stale

NOW = datetime(2026, 9, 18, tzinfo=timezone.utc)


def test_days_since_none_means_never_updated():
    assert days_since(None, NOW) is None


def test_days_since_counts_whole_days():
    assert days_since(NOW - timedelta(days=10, hours=23), NOW) == 10
    assert days_since(NOW, NOW) == 0


def test_naive_timestamps_assumed_utc():
    naive = datetime(2026, 9, 8)  # 10 days before NOW, no tzinfo
    assert days_since(naive, NOW) == 10


def test_boundary_exactly_threshold_is_not_stale():
    assert is_stale(NOW - timedelta(days=365), 365, NOW) is False
    assert is_stale(NOW - timedelta(days=366), 365, NOW) is True
    assert is_stale(None, 365, NOW) is True
    assert is_stale(NOW - timedelta(days=1), 365, NOW) is False
