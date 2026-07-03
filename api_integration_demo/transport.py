"""HTTP transport with a bounded, jittered retry policy.

Delivery to a third-party API is the part most likely to fail transiently: a
429, a 502, a dropped connection. This module isolates that concern behind a
small ``Transport`` protocol so:

* the notifier code never touches ``requests`` directly and stays trivial to
  test with a fake transport, and
* the retry / backoff policy lives in exactly one place.

The policy is deliberately conservative: retry only on clearly transient
signals (429 and 5xx), give up after a bounded number of attempts, and never
retry a 4xx that will never succeed.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass
class Response:
    status_code: int
    text: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class Transport(Protocol):
    """Minimal HTTP surface the notifiers depend on."""

    def post(self, url: str, *, json: Mapping[str, Any], timeout: float) -> Response:
        ...


class DeliveryError(RuntimeError):
    """Raised when delivery fails after exhausting the retry budget."""

    def __init__(self, message: str, *, last_status: int | None = None) -> None:
        super().__init__(message)
        self.last_status = last_status


_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Exposed so tests can monkeypatch it instead of actually sleeping.
_sleep = time.sleep


def _backoff_seconds(attempt: int, base: float, cap: float) -> float:
    """Exponential backoff with full jitter (attempt is 0-indexed)."""
    ceiling = min(cap, base * (2 ** attempt))
    return random.uniform(0, ceiling)


class RequestsTransport:
    """Default transport backed by ``requests``. Imported lazily so the package
    can be imported (and unit-tested with a fake transport) without requests
    installed."""

    def __init__(self) -> None:
        import requests  # noqa: PLC0415 - intentional lazy import

        self._session = requests.Session()

    def post(self, url: str, *, json: Mapping[str, Any], timeout: float) -> Response:
        resp = self._session.post(url, json=json, timeout=timeout)
        return Response(status_code=resp.status_code, text=resp.text)


def post_with_retry(
    transport: Transport,
    url: str,
    payload: Mapping[str, Any],
    *,
    max_attempts: int = 4,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    timeout: float = 10.0,
) -> Response:
    """POST ``payload`` to ``url``, retrying transient failures.

    Returns the successful ``Response``. Raises ``DeliveryError`` if every
    attempt fails or a non-retryable status is returned.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    last_status: int | None = None
    for attempt in range(max_attempts):
        try:
            resp = transport.post(url, json=payload, timeout=timeout)
        except Exception as exc:  # network-level failure: retryable
            last_status = None
            if attempt == max_attempts - 1:
                raise DeliveryError(
                    f"delivery failed after {max_attempts} attempts: {exc}"
                ) from exc
            _sleep(_backoff_seconds(attempt, base_delay, max_delay))
            continue

        if resp.ok:
            return resp

        last_status = resp.status_code
        if resp.status_code not in _RETRYABLE_STATUS:
            raise DeliveryError(
                f"delivery rejected with status {resp.status_code}",
                last_status=resp.status_code,
            )

        if attempt == max_attempts - 1:
            break
        _sleep(_backoff_seconds(attempt, base_delay, max_delay))

    raise DeliveryError(
        f"delivery failed after {max_attempts} attempts (last status {last_status})",
        last_status=last_status,
    )
