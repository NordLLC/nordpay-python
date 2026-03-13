"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json as json_mod
from typing import Any

import httpx
import pytest


class MockTransport(httpx.BaseTransport):
    """Records requests and replays queued responses."""

    def __init__(self) -> None:
        self._responses: list[tuple[int, Any, str, dict[str, str]]] = []
        self._requests: list[httpx.Request] = []

    def add_response(
        self,
        *,
        status_code: int = 200,
        json: Any = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self._responses.append((status_code, json, text, headers or {}))

    def get_requests(self) -> list[httpx.Request]:
        return list(self._requests)

    @property
    def request_count(self) -> int:
        return len(self._requests)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self._requests.append(request)
        if not self._responses:
            return httpx.Response(500, text="No mock response configured")
        status_code, json_data, text, extra_headers = self._responses.pop(0)
        resp_headers = {"content-type": "application/json", **extra_headers}
        if json_data is not None:
            content = json_mod.dumps(json_data).encode()
            return httpx.Response(status_code, content=content, headers=resp_headers)
        return httpx.Response(status_code, text=text, headers=resp_headers)


class MockAsyncTransport(httpx.AsyncBaseTransport):
    """Async wrapper for MockTransport."""

    def __init__(self, sync_transport: MockTransport) -> None:
        self._sync = sync_transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self._sync.handle_request(request)


@pytest.fixture
def httpx_mock(monkeypatch: pytest.MonkeyPatch) -> MockTransport:
    """Intercept all httpx requests with a mock transport."""
    mock = MockTransport()

    original_client_init = httpx.Client.__init__
    original_async_client_init = httpx.AsyncClient.__init__

    def patched_client_init(self: Any, *args: Any, **kwargs: Any) -> None:
        kwargs["transport"] = mock
        kwargs.pop("base_url", None)
        original_client_init(self, *args, base_url="https://api.nord-pay.com", **kwargs)

    def patched_async_client_init(self: Any, *args: Any, **kwargs: Any) -> None:
        kwargs["transport"] = MockAsyncTransport(mock)
        kwargs.pop("base_url", None)
        original_async_client_init(self, *args, base_url="https://api.nord-pay.com", **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", patched_client_init)
    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_async_client_init)

    return mock


# ---------------------------------------------------------------------------
# Shared mock data
# ---------------------------------------------------------------------------

MOCK_CURRENCIES = [
    {
        "name": "BTC",
        "token": None,
        "network": "bitcoin",
        "contract": None,
        "decimals": 8,
        "confirmations": 2,
        "network_fee": "0.0001",
        "min_deposit": "0.0001",
        "icon": "https://cdn.example.com/btc.png",
        "is_available": True,
        "can_exchange": True,
        "can_withdraw": True,
        "min_withdraw": "0.001",
        "rate": "67500.00",
    },
    {
        "name": "USDTERC20",
        "token": "USDT",
        "network": "ethereum",
        "contract": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "decimals": 6,
        "confirmations": 12,
        "network_fee": "5.0",
        "min_deposit": "10.0",
        "icon": "https://cdn.example.com/usdt.png",
        "is_available": True,
        "can_exchange": True,
        "can_withdraw": True,
        "min_withdraw": "20.0",
        "rate": "1.0",
    },
]

MOCK_FIAT_CURRENCIES = [
    {
        "id": 1,
        "name": "US Dollar",
        "code": "USD",
        "icon": None,
        "can_exchange": True,
        "supports_sepa": False,
        "sepa_fee": "0",
        "supports_swift": True,
        "swift_fee": "25.0",
        "can_withdraw": True,
        "min_withdraw": "100.0",
        "rate": "1.0",
    },
    {
        "id": 2,
        "name": "Euro",
        "code": "EUR",
        "icon": None,
        "can_exchange": True,
        "supports_sepa": True,
        "sepa_fee": "5.0",
        "supports_swift": True,
        "swift_fee": "30.0",
        "can_withdraw": True,
        "min_withdraw": "100.0",
        "rate": "0.92",
    },
]

MOCK_INVOICE = {
    "id": 1,
    "uuid": "abc-123-def",
    "currency": "BTC",
    "allowed_currencies": None,
    "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "amount": "0.00148",
    "amount_usd": "100.00",
    "received_amount": "0.0",
    "received_amount_usd": "0.0",
    "confirmations": 0,
    "label": "Order #123",
    "postback_url": None,
    "success_url": None,
    "fail_url": None,
    "created_at": "2026-03-07T12:00:00Z",
    "expires_at": "2026-03-07T13:00:00Z",
    "status": "pending",
    "url": "https://app.nord-pay.com/invoice/abc-123-def",
    "tx_hash": None,
}

MOCK_WALLET = {
    "id": 42,
    "label": "My BTC Wallet",
    "postback_url": None,
    "currency": "BTC",
    "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
    "status": "active",
    "created_at": "2026-03-01T10:00:00Z",
    "expires_at": "2027-03-01T10:00:00Z",
}

MOCK_TRANSACTION = {
    "id": 100,
    "currency": MOCK_CURRENCIES[0],
    "source_type": "invoice",
    "source": {"id": 1, "uuid": "abc-123-def"},
    "amount": "0.00148",
    "amount_usd": "100.00",
    "network_fee": "0.0001",
    "network_fee_usd": "6.75",
    "service_fee": "0.00001",
    "service_fee_usd": "0.68",
    "tx_hash": "abc123def456789",
    "status": "paid",
    "is_postback_sent": True,
    "created_at": "2026-03-07T12:30:00Z",
}

MOCK_WITHDRAW_REQUEST = {
    "identifier": "wd-123-abc",
    "currency": "USDTERC20",
    "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18",
    "amount": "100.00",
    "amount_usd": "100.00",
    "service_fee": "1.00",
    "service_fee_usd": "1.00",
    "expires_at": "2026-03-07T13:00:00Z",
}

MOCK_WITHDRAW_CONFIRMATION = {"detail": "ok", "status": "processing", "id": 1}

MOCK_MULTIPLE_WITHDRAW_REQUEST = {
    "identifier": "mwd-456-xyz",
    "currency": "USDTTRC20",
    "total_amount": "150.00",
    "total_amount_usd": "150.00",
    "total_service_fee": "1.50",
    "total_service_fee_usd": "1.50",
    "addresses_count": 3,
    "expires_at": "2026-03-07T13:00:00Z",
}

MOCK_PAGINATED_INVOICES = {
    "items": [
        {
            "id": 1,
            "uuid": "abc-123-def",
            "currency": "BTC",
            "allowed_currencies": None,
            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "amount": "0.00148",
            "amount_usd": "100.00",
            "received_amount": "0.0",
            "received_amount_usd": "0.0",
            "label": "Order #123",
            "postback_url": None,
            "success_url": None,
            "fail_url": None,
            "created_at": "2026-03-07T12:00:00Z",
            "expires_at": "2026-03-07T13:00:00Z",
            "status": "pending",
        },
    ],
    "total": 42,
    "offset": 0,
    "limit": 50,
    "total_pages": 1,
}

MOCK_INVOICE_SUMMARY = {
    "total_count": 100,
    "paid_count": 75,
    "pending_count": 15,
    "expired_count": 10,
    "total_amount_usd": "50000.00",
    "paid_amount_usd": "37500.00",
}

MOCK_POSTBACK_LOG = {
    "id": 1,
    "event": "invoice.paid",
    "endpoint": "https://example.com/webhook",
    "status_code": 200,
    "status": "delivered",
    "latency_ms": 150,
    "attempt": 1,
    "max_attempts": 5,
    "request_payload": {"invoice_id": 1, "status": "paid"},
    "response_body": "OK",
    "error_message": None,
    "is_final": True,
    "created_at": "2026-03-07T12:30:00Z",
}

MOCK_POSTBACK_LOG_FAILED = {
    "id": 2,
    "event": "invoice.paid",
    "endpoint": "https://example.com/webhook",
    "status_code": 500,
    "status": "failed",
    "latency_ms": 3000,
    "attempt": 3,
    "max_attempts": 5,
    "request_payload": {"invoice_id": 1, "status": "paid"},
    "response_body": "Internal Server Error",
    "error_message": "Server returned 500",
    "is_final": False,
    "created_at": "2026-03-07T12:35:00Z",
}

MOCK_PAGINATED_WALLETS = {
    "items": [
        {
            "id": 42,
            "label": "My BTC Wallet",
            "postback_url": None,
            "currency": "BTC",
            "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "status": "active",
            "created_at": "2026-03-01T10:00:00Z",
            "expires_at": "2027-03-01T10:00:00Z",
        },
    ],
    "total": 5,
    "offset": 0,
    "limit": 50,
    "total_pages": 1,
}

MOCK_WALLET_LIMITS = {"total": 10, "used": 3, "available": 7}

MOCK_WITHDRAW_HISTORY = {
    "items": [
        {
            "id": 10,
            "currency": "USDTERC20",
            "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18",
            "tx_hash": "0xabc123",
            "amount": "100.00",
            "amount_usd": "100.00",
            "service_fee": "1.00",
            "service_fee_usd": "1.00",
            "status": "completed",
            "created_at": "2026-03-05T14:00:00Z",
        },
    ],
    "total": 25,
    "offset": 0,
    "limit": 50,
    "total_pages": 1,
}

MOCK_WITHDRAW_LIMITS = [
    {
        "currency": "BTC",
        "min_amount": "0.001",
        "max_amount": "10.0",
        "fee_percent": "0.5",
        "available_balance": "2.5",
    },
    {
        "currency": "USDTERC20",
        "min_amount": "20.0",
        "max_amount": "50000.0",
        "fee_percent": "1.0",
        "available_balance": "15000.0",
    },
]
