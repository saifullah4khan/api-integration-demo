"""Send one lead straight to a webhook, no Flask server involved.

Usage:
    RELAY_WEBHOOK_URL=https://hooks.slack.com/services/... \
        python examples/send_test_lead.py slack

This uses the real RequestsTransport, so it needs `pip install requests` and a
live webhook URL. It is the fastest way to confirm your Slack/Discord webhook
works before wiring up the HTTP intake.
"""

import os
import sys

from api_integration_demo.models import parse_intake
from api_integration_demo.notifiers import build_notifier
from api_integration_demo.transport import RequestsTransport


def main() -> int:
    platform = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("RELAY_PLATFORM", "slack")
    url = os.environ.get("RELAY_WEBHOOK_URL")
    if not url:
        print("Set RELAY_WEBHOOK_URL to your Slack/Discord webhook first.")
        return 1

    lead = parse_intake(
        {
            "name": "Test Lead",
            "email": "test@example.com",
            "message": "Kicking the tires on api-integration-demo.",
            "plan": "trial",
        },
        source="example-script",
    )
    notifier = build_notifier(platform, url, RequestsTransport())
    resp = notifier.send(lead)
    print(f"Sent to {notifier.name}: HTTP {resp.status_code}")
    return 0 if resp.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
