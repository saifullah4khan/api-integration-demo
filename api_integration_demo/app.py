"""Flask app: the front door of the integration.

POST an intake (form-encoded or JSON) to ``/intake`` and it is normalized into a
``Lead`` and relayed to the configured chat platform. The app is built through a
factory so tests can inject a fake notifier and never touch the network.
"""

from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, request

from .models import IntakeError, parse_intake
from .notifiers import Notifier, build_notifier
from .transport import DeliveryError


def _collect_payload() -> dict[str, Any]:
    if request.is_json:
        data = request.get_json(silent=True)
        return dict(data) if isinstance(data, dict) else {}
    return request.form.to_dict()


def create_app(notifier: Notifier | None = None) -> Flask:
    """Application factory.

    Pass a ``notifier`` directly (tests, custom wiring) or let the app build one
    from environment variables: ``RELAY_PLATFORM`` and ``RELAY_WEBHOOK_URL``.
    """

    app = Flask(__name__)

    if notifier is None:
        platform = os.environ.get("RELAY_PLATFORM", "slack")
        webhook_url = os.environ.get("RELAY_WEBHOOK_URL", "")
        if webhook_url:
            from .transport import RequestsTransport

            notifier = build_notifier(platform, webhook_url, RequestsTransport())

    app.config["NOTIFIER"] = notifier

    @app.get("/healthz")
    def healthz():  # pragma: no cover - trivial
        configured = app.config.get("NOTIFIER") is not None
        return jsonify(status="ok", notifier_configured=configured)

    @app.post("/intake")
    def intake():
        active: Notifier | None = app.config.get("NOTIFIER")
        if active is None:
            return jsonify(error="no notifier configured"), 503

        try:
            lead = parse_intake(_collect_payload(), source=request.host or "http")
        except IntakeError as exc:
            return jsonify(error=str(exc)), 400

        try:
            active.send(lead)
        except DeliveryError as exc:
            # Upstream accepted the intake but the downstream relay failed.
            return jsonify(error="relay failed", detail=str(exc)), 502

        return jsonify(status="relayed", to=active.name), 202

    return app
