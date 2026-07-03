"""Canonical intake model and parsing.

Inbound submissions arrive in many shapes: an HTML form POST, a JSON body from
another service, field names that differ per source. Rather than let those
differences leak into the notifier code, everything is normalized into one
canonical ``Lead`` first. The formatting and delivery code then only ever sees
a ``Lead``, never a raw request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


class IntakeError(ValueError):
    """Raised when an inbound payload cannot be turned into a Lead."""


# Common aliases seen across form vendors and hand-rolled clients. Kept small
# and explicit on purpose: an obvious mapping table beats clever guessing.
_NAME_KEYS = ("name", "full_name", "fullName", "contact_name")
_EMAIL_KEYS = ("email", "email_address", "emailAddress", "from")
_MESSAGE_KEYS = ("message", "msg", "body", "comments", "notes")


def _first(source: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


@dataclass
class Lead:
    """A normalized inbound contact/lead.

    ``extra`` keeps any fields we did not map so nothing is silently dropped;
    the notifier can render them if it wants.
    """

    name: str
    email: str
    message: str
    source: str = "unknown"
    extra: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        who = self.name or self.email or "someone"
        return f"New lead from {who}"


def parse_intake(payload: Mapping[str, Any], *, source: str = "unknown") -> Lead:
    """Turn a raw payload (form dict or parsed JSON) into a ``Lead``.

    Requires at least an email or a name so downstream systems have something to
    key on. Everything unmapped is preserved in ``Lead.extra``.
    """

    if not isinstance(payload, Mapping):
        raise IntakeError("payload must be a mapping of fields")

    name = _first(payload, _NAME_KEYS)
    email = _first(payload, _EMAIL_KEYS)
    message = _first(payload, _MESSAGE_KEYS)

    if not name and not email:
        raise IntakeError("payload must include at least a name or an email")

    mapped = set(_NAME_KEYS) | set(_EMAIL_KEYS) | set(_MESSAGE_KEYS)
    extra = {k: v for k, v in payload.items() if k not in mapped}

    return Lead(name=name, email=email, message=message, source=source, extra=extra)
