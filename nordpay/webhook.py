"""Postback (webhook) verification utilities.

NordPay sends a ``postback_secret`` in the JSON body of webhook notifications.
Use :func:`verify_postback` to validate the secret and parse the event, or
:func:`is_valid_postback` for a simple boolean check.

Example — FastAPI::

    from nordpay.webhook import verify_postback

    @app.post("/webhook")
    async def handle_postback(request: Request):
        body = await request.json()
        event = verify_postback(body, secret="your-postback-secret")
        print(f"Got {event.postback_type} for {event.object_type} #{event.object_id}")
        return {"ok": True}

Example — Flask::

    from nordpay.webhook import verify_postback

    @app.route("/webhook", methods=["POST"])
    def handle_postback():
        event = verify_postback(request.json, secret="your-postback-secret")
        ...
"""

from __future__ import annotations

import hmac
from typing import Any

from nordpay.exceptions import WebhookVerificationError
from nordpay.models import PostbackEvent


def is_valid_postback(payload: dict[str, Any], *, secret: str) -> bool:
    """Check if a postback payload has a valid secret.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        payload: Parsed JSON body from the webhook request.
        secret: Your postback secret (from NordPay dashboard).

    Returns:
        ``True`` if the secret matches, ``False`` otherwise.
    """
    received_secret = payload.get("postback_secret", "")
    if not isinstance(received_secret, str) or not received_secret:
        return False
    return hmac.compare_digest(received_secret, secret)


def verify_postback(payload: dict[str, Any], *, secret: str) -> PostbackEvent:
    """Verify a postback payload and parse it into a :class:`PostbackEvent`.

    Args:
        payload: Parsed JSON body from the webhook request.
        secret: Your postback secret (from NordPay dashboard).

    Returns:
        Parsed :class:`PostbackEvent`.

    Raises:
        WebhookVerificationError: If the secret doesn't match.
    """
    if not is_valid_postback(payload, secret=secret):
        raise WebhookVerificationError()
    return PostbackEvent.model_validate(payload)
