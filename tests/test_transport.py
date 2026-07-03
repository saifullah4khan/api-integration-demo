import pytest

from api_integration_demo import transport as t
from api_integration_demo.transport import DeliveryError, Response, post_with_retry
from tests.conftest import FakeTransport


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Never actually sleep during retry tests."""
    monkeypatch.setattr(t, "_sleep", lambda _seconds: None)


def test_success_first_try_no_retry():
    fake = FakeTransport(responses=[Response(200, "ok")])
    resp = post_with_retry(fake, "http://x", {"a": 1})
    assert resp.ok
    assert len(fake.calls) == 1


def test_retries_then_succeeds():
    fake = FakeTransport(responses=[Response(503), Response(503), Response(200)])
    resp = post_with_retry(fake, "http://x", {}, max_attempts=4)
    assert resp.ok
    assert len(fake.calls) == 3


def test_gives_up_after_budget():
    fake = FakeTransport(responses=[Response(500)])
    with pytest.raises(DeliveryError) as exc:
        post_with_retry(fake, "http://x", {}, max_attempts=3)
    assert exc.value.last_status == 500
    assert len(fake.calls) == 3


def test_non_retryable_status_fails_immediately():
    fake = FakeTransport(responses=[Response(400)])
    with pytest.raises(DeliveryError) as exc:
        post_with_retry(fake, "http://x", {}, max_attempts=5)
    assert exc.value.last_status == 400
    assert len(fake.calls) == 1


def test_network_exception_is_retried():
    fake = FakeTransport(responses=[ConnectionError("boom"), Response(200)])
    resp = post_with_retry(fake, "http://x", {}, max_attempts=3)
    assert resp.ok
    assert len(fake.calls) == 2


def test_network_exception_exhausts_budget():
    fake = FakeTransport(responses=[TimeoutError("slow")])
    with pytest.raises(DeliveryError):
        post_with_retry(fake, "http://x", {}, max_attempts=2)
    assert len(fake.calls) == 2


def test_invalid_max_attempts():
    with pytest.raises(ValueError):
        post_with_retry(FakeTransport(), "http://x", {}, max_attempts=0)


def test_backoff_is_bounded_and_nonnegative():
    for attempt in range(6):
        delay = t._backoff_seconds(attempt, base=0.5, cap=8.0)
        assert 0.0 <= delay <= 8.0
