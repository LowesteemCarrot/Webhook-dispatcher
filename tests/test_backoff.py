"""Tests for backoff and retry-eligibility logic."""

from app.worker import BASE_DELAY, MAX_DELAY, backoff_delay, should_retry


def test_backoff_increases_with_attempts():
    """Delay should grow roughly exponentially."""
    delays = [backoff_delay(n) for n in range(6)]
    # Even with jitter, later delays should be larger on average
    assert delays[4] > delays[0]


def test_backoff_is_capped():
    """Delay should never exceed MAX_DELAY (+ jitter headroom)."""
    for _ in range(50):
        d = backoff_delay(20)  # very high attempt
        assert d <= MAX_DELAY * 1.6  # generous headroom for jitter


def test_backoff_has_jitter():
    """Repeated calls should give different results."""
    results = {backoff_delay(3) for _ in range(20)}
    assert len(results) > 1  # not all identical


def test_should_retry_5xx():
    assert should_retry(500) is True
    assert should_retry(502) is True
    assert should_retry(503) is True


def test_should_retry_429():
    assert should_retry(429) is True


def test_should_not_retry_4xx():
    assert should_retry(400) is False
    assert should_retry(401) is False
    assert should_retry(404) is False
    assert should_retry(422) is False


def test_should_not_retry_2xx():
    assert should_retry(200) is False
    assert should_retry(201) is False
