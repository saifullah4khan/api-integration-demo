import pytest

from api_integration_demo.app import create_app
from api_integration_demo.transport import DeliveryError


class RecordingNotifier:
    name = "fake"

    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    def send(self, lead):
        if self.fail:
            raise DeliveryError("nope", last_status=503)
        self.sent.append(lead)


@pytest.fixture
def client_and_notifier():
    notifier = RecordingNotifier()
    app = create_app(notifier=notifier)
    app.config.update(TESTING=True)
    return app.test_client(), notifier


def test_intake_relays_json(client_and_notifier):
    client, notifier = client_and_notifier
    resp = client.post("/intake", json={"name": "Ada", "email": "a@b.c"})
    assert resp.status_code == 202
    assert resp.get_json()["status"] == "relayed"
    assert len(notifier.sent) == 1


def test_intake_relays_form(client_and_notifier):
    client, notifier = client_and_notifier
    resp = client.post("/intake", data={"name": "Ada", "email": "a@b.c"})
    assert resp.status_code == 202
    assert notifier.sent[0].name == "Ada"


def test_bad_intake_returns_400(client_and_notifier):
    client, _ = client_and_notifier
    resp = client.post("/intake", json={"message": "no identity"})
    assert resp.status_code == 400


def test_relay_failure_returns_502():
    app = create_app(notifier=RecordingNotifier(fail=True))
    resp = app.test_client().post("/intake", json={"name": "Ada"})
    assert resp.status_code == 502


def test_no_notifier_returns_503():
    app = create_app(notifier=None)
    resp = app.test_client().post("/intake", json={"name": "Ada"})
    assert resp.status_code == 503


def test_healthz(client_and_notifier):
    client, _ = client_and_notifier
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["notifier_configured"] is True
