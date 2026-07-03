# api-integration-demo

Relay a web form or JSON intake to Slack or Discord, with the reliability details a real integration needs.

## The problem

"When a lead fills out the form, ping our team channel" is the most common integration request there is, and the naive version breaks in production. It hardcodes one chat platform, it assumes every inbound payload uses the same field names, and it treats the outbound webhook call as if it never fails. Then a customer says "we use Discord, not Slack," a form vendor sends `full_name` instead of `name`, and Slack returns a `429` during a launch. This repo is a small, complete example of wiring input from one API to output on another while handling those three realities up front.

## What it does

An HTTP `POST /intake` (form-encoded or JSON) is normalized into a canonical `Lead`, then relayed to whichever chat platform you configured. The whole path is about 200 lines and easy to read end to end.

```
POST /intake  ->  parse_intake()  ->  Lead  ->  Notifier.send()  ->  Slack / Discord
                                                     |
                                             post_with_retry()  (shared transport + backoff)
```

## Quickstart

```bash
pip install -e ".[requests]"

export RELAY_PLATFORM=slack
export RELAY_WEBHOOK_URL="https://hooks.slack.com/services/XXX/YYY/ZZZ"
flask --app api_integration_demo.app:create_app run
```

Then send an intake:

```bash
curl -X POST http://localhost:5000/intake \
  -H "Content-Type: application/json" \
  -d '{"name": "Ada Lovelace", "email": "ada@example.com", "message": "Interested in a demo"}'
# {"status":"relayed","to":"slack"}
```

Prefer to test the webhook without running a server first? `examples/send_test_lead.py` sends one lead directly.

## Design decisions (the why)

**One canonical model, mapped at the edge.** Inbound field names vary per source, so `parse_intake()` maps a small set of known aliases (`full_name`, `email_address`, `msg`, and so on) into a single `Lead` before anything else runs. The formatting and delivery code only ever sees a `Lead`. Anything unmapped is kept in `Lead.extra` rather than dropped, because silently losing a field the customer sent is worse than rendering an extra line.

**Destination is an adapter, not an `if` ladder.** `SlackNotifier` and `DiscordNotifier` implement the same `Notifier` protocol. Each owns exactly two things: its webhook URL and how to shape the JSON body for that platform (`{"text": ...}` for Slack, `{"content": ...}` for Discord). Adding a third platform is a new class, not a new branch scattered through the pipeline. This is the part that answers "but we use a different tool."

**Retry policy lives in one place.** Both notifiers deliver through `post_with_retry()`, which retries only clearly transient failures (`429` and `5xx`, plus network-level exceptions), uses exponential backoff with full jitter, and stops after a bounded number of attempts. A `4xx` such as a bad webhook URL is not retried, because it will never succeed and hammering it just delays the error. When the budget is exhausted it raises a typed `DeliveryError` carrying the last status.

**The transport is injectable.** Notifiers depend on a tiny `Transport` protocol, not on `requests` directly. Production uses `RequestsTransport`; the test suite uses a `FakeTransport` that queues responses. That is why every test runs in a fraction of a second and never opens a socket, and why `requests` is an optional dependency.

**The intake is accepted even when the relay fails.** If parsing succeeds but delivery fails, the endpoint returns `502` with detail rather than a generic `500`, so the caller can tell "you sent me bad data" (`400`) apart from "I could not reach the downstream service" (`502`).

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `RELAY_PLATFORM` | `slack` | Destination adapter: `slack` or `discord`. |
| `RELAY_WEBHOOK_URL` | (empty) | Incoming-webhook URL for the platform. If unset, `/intake` returns `503`. |

Retry behavior is set in code when constructing a notifier (or calling `post_with_retry`): `max_attempts` (default 4), `base_delay` (0.5s), `max_delay` (8s), and `timeout` (10s).

## API

| Route | Method | Result |
| --- | --- | --- |
| `/intake` | POST | `202` relayed, `400` bad intake, `502` relay failed, `503` no notifier configured. |
| `/healthz` | GET | `200` with whether a notifier is configured. |

## Testing

```bash
pip install -e ".[dev]"
pytest
```

24 tests cover field mapping, the retry state machine (success, retry-then-succeed, budget exhaustion, non-retryable status, network errors), both payload shapes, and the HTTP endpoint. All run offline against `FakeTransport`.

## License

MIT. Contact: saifullah4khan@gmail.com
