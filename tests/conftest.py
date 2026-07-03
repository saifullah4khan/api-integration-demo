"""Shared test helpers: a fake transport so no test touches the network."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from api_integration_demo.transport import Response


@dataclass
class FakeTransport:
    """Records POSTs and returns queued responses.

    ``responses`` is a list of Response objects or Exceptions to raise, consumed
    in order. When exhausted, the last response repeats.
    """

    responses: list[Any] = field(default_factory=lambda: [Response(200, "ok")])
    calls: list[dict[str, Any]] = field(default_factory=list)

    def post(self, url: str, *, json: Mapping[str, Any], timeout: float) -> Response:
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        idx = min(len(self.calls) - 1, len(self.responses) - 1)
        item = self.responses[idx]
        if isinstance(item, Exception):
            raise item
        return item
