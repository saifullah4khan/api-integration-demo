"""Notifier adapters: turn a ``Lead`` into a message for a chat platform.

Two systems, one contract. A real Solutions Engineering integration has to cope
with "we use Slack" versus "we use Discord" without rewriting the pipeline. Each
notifier owns exactly two things: the destination URL and how to shape the JSON
body for that platform's incoming-webhook API. Everything else (retries,
timeouts) is shared via the transport.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .models import Lead
from .transport import Response, Transport, post_with_retry


class Notifier(Protocol):
    name: str

    def send(self, lead: Lead) -> Response:
        ...


def _lead_lines(lead: Lead) -> list[str]:
    lines = [lead.summary()]
    if lead.email:
        lines.append(f"Email: {lead.email}")
    if lead.message:
        lines.append(f"Message: {lead.message}")
    if lead.source and lead.source != "unknown":
        lines.append(f"Source: {lead.source}")
    for key, value in lead.extra.items():
        lines.append(f"{key}: {value}")
    return lines


class SlackNotifier:
    """Posts to a Slack Incoming Webhook (https://api.slack.com/messaging/webhooks).

    Slack expects ``{"text": "..."}`` and answers 200/``ok`` on success.
    """

    name = "slack"

    def __init__(self, webhook_url: str, transport: Transport, **retry: Any) -> None:
        self._url = webhook_url
        self._transport = transport
        self._retry = retry

    def build_payload(self, lead: Lead) -> Mapping[str, Any]:
        return {"text": "\n".join(_lead_lines(lead))}

    def send(self, lead: Lead) -> Response:
        return post_with_retry(
            self._transport, self._url, self.build_payload(lead), **self._retry
        )


class DiscordNotifier:
    """Posts to a Discord webhook (https://discord.com/developers/docs/resources/webhook).

    Discord expects ``{"content": "..."}`` and answers 204 with no body on
    success, which the shared ``Response.ok`` check already handles.
    """

    name = "discord"

    def __init__(self, webhook_url: str, transport: Transport, **retry: Any) -> None:
        self._url = webhook_url
        self._transport = transport
        self._retry = retry

    def build_payload(self, lead: Lead) -> Mapping[str, Any]:
        return {"content": "\n".join(_lead_lines(lead))}

    def send(self, lead: Lead) -> Response:
        return post_with_retry(
            self._transport, self._url, self.build_payload(lead), **self._retry
        )


def build_notifier(
    platform: str, webhook_url: str, transport: Transport, **retry: Any
) -> Notifier:
    """Factory: pick a notifier by platform name."""
    platform = platform.lower().strip()
    if platform == "slack":
        return SlackNotifier(webhook_url, transport, **retry)
    if platform == "discord":
        return DiscordNotifier(webhook_url, transport, **retry)
    raise ValueError(f"unknown platform: {platform!r} (expected 'slack' or 'discord')")
