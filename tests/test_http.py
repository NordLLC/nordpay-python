"""Tests for HTTP transport — retries, error parsing, headers."""

from __future__ import annotations

import httpx
import pytest

from nordpay import NordPay, NordPayError, RateLimitError, ServerError
from nordpay._http import _build_headers, _parse_error
from nordpay.exceptions import ConnectionError as NordPayConnectionError
from nordpay.exceptions import TimeoutError as NordPayTimeoutError

from .conftest import MOCK_CURRENCIES

# ---------------------------------------------------------------------------
# Header building
# ---------------------------------------------------------------------------


class TestBuildHeaders:
    def test_with_api_key(self):
        headers = _build_headers("my-key")
        assert headers["X-API-Key"] == "my-key"
        assert "nordpay-python/" in headers["User-Agent"]
        assert headers["Accept"] == "application/json"

    def test_without_api_key(self):
        headers = _build_headers(None)
        assert "X-API-Key" not in headers

    def test_empty_api_key(self):
        headers = _build_headers("")
        assert "X-API-Key" not in headers


# ---------------------------------------------------------------------------
# Error parsing
# ---------------------------------------------------------------------------


class TestParseError:
    def test_json_detail(self):
        response = httpx.Response(400, json={"detail": "Bad amount"})
        err = _parse_error(response)
        assert err.status_code == 400
        assert "Bad amount" in err.detail

    def test_json_message(self):
        response = httpx.Response(400, json={"message": "Invalid"})
        err = _parse_error(response)
        assert "Invalid" in err.detail

    def test_plain_text(self):
        response = httpx.Response(502, text="Bad Gateway")
        err = _parse_error(response)
        assert err.status_code == 502
        assert "Bad Gateway" in err.detail

    def test_429_with_retry_after(self):
        response = httpx.Response(429, json={"detail": "Rate limited"}, headers={"Retry-After": "60"})
        err = _parse_error(response)
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 60.0

    def test_429_without_retry_after(self):
        response = httpx.Response(429, json={"detail": "Rate limited"})
        err = _parse_error(response)
        assert isinstance(err, RateLimitError)
        assert err.retry_after is None

    def test_429_with_http_date_retry_after(self):
        """Non-numeric Retry-After (HTTP-date) should not crash, just return None."""
        response = httpx.Response(
            429,
            json={"detail": "Rate limited"},
            headers={"Retry-After": "Thu, 13 Mar 2026 12:00:00 GMT"},
        )
        err = _parse_error(response)
        assert isinstance(err, RateLimitError)
        assert err.retry_after is None

    def test_500_is_server_error(self):
        response = httpx.Response(500, json={"detail": "Internal"})
        err = _parse_error(response)
        assert isinstance(err, ServerError)

    def test_response_body_preserved(self):
        body = {"detail": "Bad", "code": "INVALID_AMOUNT"}
        response = httpx.Response(400, json=body)
        err = _parse_error(response)
        assert err.response_body == body


# ---------------------------------------------------------------------------
# Retry behavior
# ---------------------------------------------------------------------------


class TestRetry:
    def test_retry_on_500(self, httpx_mock):
        """Server errors are retried up to max_retries times."""
        httpx_mock.add_response(status_code=500, json={"detail": "error"})
        httpx_mock.add_response(json=MOCK_CURRENCIES)  # success on retry
        with NordPay(max_retries=1) as client:
            result = client.currencies.list()
        assert len(result) == 2
        assert httpx_mock.request_count == 2

    def test_retry_on_502(self, httpx_mock):
        httpx_mock.add_response(status_code=502, text="Bad Gateway")
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay(max_retries=1) as client:
            result = client.currencies.list()
        assert len(result) == 2

    def test_retry_on_503(self, httpx_mock):
        httpx_mock.add_response(status_code=503, text="Service Unavailable")
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay(max_retries=1) as client:
            result = client.currencies.list()
        assert len(result) == 2

    def test_retry_on_429(self, httpx_mock):
        httpx_mock.add_response(status_code=429, json={"detail": "rate limited"}, headers={"Retry-After": "0"})
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay(max_retries=1) as client:
            result = client.currencies.list()
        assert len(result) == 2

    def test_no_retry_on_400(self, httpx_mock):
        """Client errors (4xx except 429) should not be retried."""
        httpx_mock.add_response(status_code=400, json={"detail": "bad"})
        with NordPay("key", max_retries=3) as client, pytest.raises(NordPayError):
            client.invoices.create(amount="bad", label="x", expires_time=60)
        assert httpx_mock.request_count == 1

    def test_no_retry_on_401(self, httpx_mock):
        httpx_mock.add_response(status_code=401, json={"detail": "unauthorized"})
        with NordPay("bad", max_retries=3) as client, pytest.raises(NordPayError):
            client.invoices.list()
        assert httpx_mock.request_count == 1

    def test_no_retry_on_404(self, httpx_mock):
        httpx_mock.add_response(status_code=404, json={"detail": "not found"})
        with NordPay("key", max_retries=3) as client, pytest.raises(NordPayError):
            client.invoices.get("nope")
        assert httpx_mock.request_count == 1

    def test_max_retries_exhausted(self, httpx_mock):
        """After max_retries+1 attempts, the last error is raised."""
        for _ in range(4):
            httpx_mock.add_response(status_code=500, json={"detail": "error"})
        with NordPay(max_retries=3) as client, pytest.raises(ServerError):
            client.currencies.list()
        assert httpx_mock.request_count == 4  # 1 initial + 3 retries

    def test_zero_retries(self, httpx_mock):
        httpx_mock.add_response(status_code=500, json={"detail": "error"})
        with NordPay(max_retries=0) as client, pytest.raises(ServerError):
            client.currencies.list()
        assert httpx_mock.request_count == 1


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_negative_max_retries(self):
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            NordPay(max_retries=-1)

    def test_negative_max_retries_async(self):
        from nordpay import AsyncNordPay

        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            AsyncNordPay(max_retries=-1)


# ---------------------------------------------------------------------------
# Network error handling
# ---------------------------------------------------------------------------


class TestNetworkErrors:
    def test_timeout_raises_sdk_error(self, monkeypatch):
        """httpx.TimeoutException is wrapped in nordpay.TimeoutError."""
        original_init = httpx.Client.__init__

        class TimeoutTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.ReadTimeout("read timed out")

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = TimeoutTransport()
            kwargs.pop("base_url", None)
            original_init(self, *args, base_url="https://api.nord-pay.com", **kwargs)

        monkeypatch.setattr(httpx.Client, "__init__", patched_init)

        with NordPay(max_retries=0) as client, pytest.raises(NordPayTimeoutError) as exc_info:
            client.currencies.list()
        assert "timed out" in exc_info.value.message

    def test_connect_error_raises_sdk_error(self, monkeypatch):
        """httpx.ConnectError is wrapped in nordpay.ConnectionError."""
        original_init = httpx.Client.__init__

        class FailTransport(httpx.BaseTransport):
            def handle_request(self, request):
                raise httpx.ConnectError("connection refused")

        def patched_init(self, *args, **kwargs):
            kwargs["transport"] = FailTransport()
            kwargs.pop("base_url", None)
            original_init(self, *args, base_url="https://api.nord-pay.com", **kwargs)

        monkeypatch.setattr(httpx.Client, "__init__", patched_init)

        with NordPay(max_retries=0) as client, pytest.raises(NordPayConnectionError) as exc_info:
            client.currencies.list()
        assert "connection refused" in exc_info.value.message

    def test_network_errors_are_nordpay_errors(self):
        """Both network error types inherit from NordPayError."""
        assert issubclass(NordPayTimeoutError, NordPayError)
        assert issubclass(NordPayConnectionError, NordPayError)
