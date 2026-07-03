"""api-integration-demo: relay a form/JSON intake to Slack or Discord.

A compact, end-to-end example of wiring one API's input to another API's output
with the reliability details a production integration needs: canonical field
mapping, pluggable destination adapters, and bounded retry with backoff.
"""

from .app import create_app
from .models import IntakeError, Lead, parse_intake
from .notifiers import DiscordNotifier, Notifier, SlackNotifier, build_notifier
from .transport import (
    DeliveryError,
    RequestsTransport,
    Response,
    Transport,
    post_with_retry,
)

__version__ = "0.1.0"

__all__ = [
    "create_app",
    "parse_intake",
    "Lead",
    "IntakeError",
    "Notifier",
    "SlackNotifier",
    "DiscordNotifier",
    "build_notifier",
    "Transport",
    "Response",
    "post_with_retry",
    "DeliveryError",
    "RequestsTransport",
]
