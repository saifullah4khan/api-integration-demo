import pytest

from api_integration_demo.models import parse_intake
from api_integration_demo.notifiers import (
    DiscordNotifier,
    SlackNotifier,
    build_notifier,
)
from api_integration_demo.transport import Response
from tests.conftest import FakeTransport


def _lead():
    return parse_intake(
        {"name": "Ada", "email": "ada@example.com", "message": "hello", "plan": "pro"},
        source="site",
    )


def test_slack_payload_shape():
    fake = FakeTransport()
    SlackNotifier("http://slack", fake).send(_lead())
    body = fake.calls[0]["json"]
    assert set(body) == {"text"}
    assert "Ada" in body["text"]
    assert "ada@example.com" in body["text"]
    assert "plan: pro" in body["text"]  # unmapped extra rendered


def test_discord_payload_shape():
    fake = FakeTransport(responses=[Response(204)])  # Discord returns 204
    resp = DiscordNotifier("http://discord", fake).send(_lead())
    assert resp.ok
    assert set(fake.calls[0]["json"]) == {"content"}


def test_factory_selects_platform():
    fake = FakeTransport()
    assert build_notifier("slack", "http://x", fake).name == "slack"
    assert build_notifier("Discord", "http://x", fake).name == "discord"


def test_factory_rejects_unknown_platform():
    with pytest.raises(ValueError):
        build_notifier("teams", "http://x", FakeTransport())
