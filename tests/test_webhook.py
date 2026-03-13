"""Tests for postback (webhook) verification."""

from __future__ import annotations

from decimal import Decimal

import pytest

from nordpay import PostbackEvent, WebhookVerificationError, is_valid_postback, verify_postback

SECRET = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


# ---------------------------------------------------------------------------
# is_valid_postback
# ---------------------------------------------------------------------------


class TestIsValidPostback:
    def test_valid_secret(self):
        payload = {"postback_secret": SECRET, "postback_type": "transaction"}
        assert is_valid_postback(payload, secret=SECRET) is True

    def test_invalid_secret(self):
        payload = {"postback_secret": "wrong-secret", "postback_type": "transaction"}
        assert is_valid_postback(payload, secret=SECRET) is False

    def test_missing_secret(self):
        payload = {"postback_type": "transaction"}
        assert is_valid_postback(payload, secret=SECRET) is False

    def test_empty_secret(self):
        payload = {"postback_secret": "", "postback_type": "transaction"}
        assert is_valid_postback(payload, secret=SECRET) is False

    def test_non_string_secret(self):
        payload = {"postback_secret": 12345, "postback_type": "transaction"}
        assert is_valid_postback(payload, secret=SECRET) is False

    def test_none_secret(self):
        payload = {"postback_secret": None, "postback_type": "transaction"}
        assert is_valid_postback(payload, secret=SECRET) is False


# ---------------------------------------------------------------------------
# verify_postback
# ---------------------------------------------------------------------------


class TestVerifyPostback:
    def test_valid_invoice_event(self):
        payload = {
            "postback_secret": SECRET,
            "postback_type": "invoice_expired",
            "object_type": "invoice",
            "object_id": 42,
            "status": "expired",
            "label": "Order #123",
            "currency": "BTC",
            "expires_at": "2026-03-07T13:00:00Z",
            "received_amount": "0.0",
            "received_amount_usd": "0.0",
            "created_at": "2026-03-07T12:00:00Z",
        }
        event = verify_postback(payload, secret=SECRET)
        assert isinstance(event, PostbackEvent)
        assert event.postback_type == "invoice_expired"
        assert event.object_type == "invoice"
        assert event.object_id == 42
        assert event.status == "expired"
        assert event.received_amount == Decimal("0.0")

    def test_valid_transaction_event(self):
        payload = {
            "postback_secret": SECRET,
            "postback_type": "transaction",
            "tx_id": 100,
            "tx_hash": "abc123def456",
            "tx_type": "invoice",
            "label": "Order #123",
            "currency": "BTC",
            "amount": "0.00148",
            "amount_usd": "100.00",
            "network_fee": "0.0001",
            "network_fee_usd": "6.75",
            "service_fee": "0.00001",
            "service_fee_usd": "0.68",
            "receive_amount": "0.00137",
            "receive_amount_usd": "92.57",
            "status": "paid",
            "created_at": "2026-03-07T12:30:00Z",
        }
        event = verify_postback(payload, secret=SECRET)
        assert event.postback_type == "transaction"
        assert event.tx_id == 100
        assert event.tx_hash == "abc123def456"
        assert event.amount == Decimal("0.00148")
        assert event.service_fee == Decimal("0.00001")

    def test_invalid_secret_raises(self):
        payload = {"postback_secret": "wrong", "postback_type": "test"}
        with pytest.raises(WebhookVerificationError):
            verify_postback(payload, secret=SECRET)

    def test_missing_secret_raises(self):
        payload = {"postback_type": "test"}
        with pytest.raises(WebhookVerificationError):
            verify_postback(payload, secret=SECRET)

    def test_extra_fields_preserved(self):
        """Unknown fields are preserved thanks to model_config extra='allow'."""
        payload = {
            "postback_secret": SECRET,
            "postback_type": "custom_event",
            "custom_field": "custom_value",
            "nested": {"a": 1},
        }
        event = verify_postback(payload, secret=SECRET)
        assert event.postback_type == "custom_event"
        # Extra fields accessible via model_extra
        assert event.model_extra is not None
        assert event.model_extra.get("custom_field") == "custom_value"

    def test_wallet_expired_event(self):
        payload = {
            "postback_secret": SECRET,
            "postback_type": "wallet_expired",
            "object_type": "wallet",
            "object_id": 42,
            "status": "expired",
            "label": "My Wallet",
            "currency": "USDTERC20",
            "expires_at": "2027-03-01T10:00:00Z",
        }
        event = verify_postback(payload, secret=SECRET)
        assert event.postback_type == "wallet_expired"
        assert event.object_type == "wallet"
