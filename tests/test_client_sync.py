"""Tests for NordPay synchronous client — full coverage."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest

from nordpay import (
    AuthenticationError,
    BadRequestError,
    CreatedInvoice,
    Currency,
    CurrencyRate,
    FiatCurrency,
    FiatCurrencyRate,
    ForbiddenError,
    Invoice,
    InvoiceSummary,
    MultipleWithdrawRequest,
    NordPay,
    NotFoundError,
    PaginatedInvoices,
    PaginatedWallets,
    PaginatedWithdraws,
    PostbackLog,
    RateLimitError,
    ServerError,
    Transaction,
    Wallet,
    WalletLimits,
    WithdrawConfirmation,
    WithdrawHistory,
    WithdrawLimit,
    WithdrawRequest,
)

from .conftest import (
    MOCK_CURRENCIES,
    MOCK_FIAT_CURRENCIES,
    MOCK_INVOICE,
    MOCK_INVOICE_SUMMARY,
    MOCK_MULTIPLE_WITHDRAW_REQUEST,
    MOCK_PAGINATED_INVOICES,
    MOCK_PAGINATED_WALLETS,
    MOCK_POSTBACK_LOG,
    MOCK_POSTBACK_LOG_FAILED,
    MOCK_TRANSACTION,
    MOCK_WALLET,
    MOCK_WALLET_LIMITS,
    MOCK_WITHDRAW_CONFIRMATION,
    MOCK_WITHDRAW_HISTORY,
    MOCK_WITHDRAW_LIMITS,
    MOCK_WITHDRAW_REQUEST,
)

# ---------------------------------------------------------------------------
# Currencies
# ---------------------------------------------------------------------------


class TestSyncCurrencies:
    def test_list(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay() as client:
            result = client.currencies.list()
        assert len(result) == 2
        assert isinstance(result[0], Currency)
        assert result[0].name == "BTC"
        assert result[0].rate == Decimal("67500.00")
        assert result[0].decimals == 8
        assert result[0].is_available is True

    def test_list_with_token_currency(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay() as client:
            result = client.currencies.list()
        usdt = result[1]
        assert usdt.name == "USDTERC20"
        assert usdt.token == "USDT"
        assert usdt.network == "ethereum"
        assert usdt.contract is not None

    def test_rates(self, httpx_mock):
        httpx_mock.add_response(json=[{"name": "BTC", "rate": "67500.00"}, {"name": "ETH", "rate": "3500.00"}])
        with NordPay() as client:
            result = client.currencies.rates()
        assert len(result) == 2
        assert isinstance(result[0], CurrencyRate)
        assert result[0].rate == Decimal("67500.00")

    def test_no_auth_required(self, httpx_mock):
        """Currency endpoints work without API key."""
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay() as client:
            client.currencies.list()
        req = httpx_mock.get_requests()[0]
        assert "X-API-Key" not in req.headers


# ---------------------------------------------------------------------------
# Fiat Currencies
# ---------------------------------------------------------------------------


class TestSyncFiatCurrencies:
    def test_list(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_FIAT_CURRENCIES)
        with NordPay() as client:
            result = client.fiat_currencies.list()
        assert len(result) == 2
        assert isinstance(result[0], FiatCurrency)
        assert result[0].code == "USD"
        assert result[1].code == "EUR"
        assert result[1].supports_sepa is True

    def test_rates(self, httpx_mock):
        httpx_mock.add_response(json=[{"code": "USD", "rate": "1.0"}, {"code": "EUR", "rate": "0.92"}])
        with NordPay() as client:
            result = client.fiat_currencies.rates()
        assert len(result) == 2
        assert isinstance(result[0], FiatCurrencyRate)
        assert result[1].rate == Decimal("0.92")


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


class TestSyncInvoices:
    def test_create_minimal(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE)
        with NordPay("test-key") as client:
            invoice = client.invoices.create(
                amount="100 USD",
                label="Order #123",
                expires_time=60,
            )
        assert isinstance(invoice, CreatedInvoice)
        assert invoice.uuid == "abc-123-def"
        assert invoice.url == "https://app.nord-pay.com/invoice/abc-123-def"
        assert invoice.amount == Decimal("0.00148")
        assert invoice.status == "pending"

        req = httpx_mock.get_requests()[0]
        body = json.loads(req.content)
        assert body == {"amount": "100 USD", "label": "Order #123", "expires_time": 60}
        assert req.headers["X-API-Key"] == "test-key"

    def test_create_with_all_options(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE)
        with NordPay("test-key") as client:
            client.invoices.create(
                amount="100 USD",
                label="Order #123",
                expires_time=60,
                currency="BTC",
                postback_url="https://example.com/webhook",
                success_url="https://example.com/success",
                fail_url="https://example.com/fail",
                allowed_currencies=["BTC", "USDTERC20"],
            )
        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body["currency"] == "BTC"
        assert body["postback_url"] == "https://example.com/webhook"
        assert body["success_url"] == "https://example.com/success"
        assert body["fail_url"] == "https://example.com/fail"
        assert body["allowed_currencies"] == ["BTC", "USDTERC20"]

    def test_list(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_INVOICE, MOCK_INVOICE])
        with NordPay("test-key") as client:
            result = client.invoices.list()
        assert len(result) == 2
        assert all(isinstance(inv, Invoice) for inv in result)

    def test_list_empty(self, httpx_mock):
        httpx_mock.add_response(json=[])
        with NordPay("test-key") as client:
            result = client.invoices.list()
        assert result == []

    def test_get_by_uuid(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE)
        with NordPay("test-key") as client:
            invoice = client.invoices.get("abc-123-def")
        assert invoice.uuid == "abc-123-def"
        assert httpx_mock.get_requests()[0].url.path == "/v1/invoice/abc-123-def"

    def test_get_by_id(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE)
        with NordPay("test-key") as client:
            client.invoices.get(1)
        assert httpx_mock.get_requests()[0].url.path == "/v1/invoice/1"

    def test_transactions_all(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_TRANSACTION])
        with NordPay("test-key") as client:
            txs = client.invoices.transactions()
        assert len(txs) == 1
        assert isinstance(txs[0], Transaction)
        assert txs[0].tx_hash == "abc123def456789"
        assert httpx_mock.get_requests()[0].url.path == "/v1/invoice/transactions"

    def test_transactions_for_invoice(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_TRANSACTION])
        with NordPay("test-key") as client:
            client.invoices.transactions("abc-123-def")
        assert httpx_mock.get_requests()[0].url.path == "/v1/invoice/abc-123-def/transactions"

    def test_transactions_with_dates(self, httpx_mock):
        httpx_mock.add_response(json=[])
        with NordPay("test-key") as client:
            client.invoices.transactions(
                start_date=datetime(2026, 1, 1),
                end_date=datetime(2026, 3, 1),
            )
        url = str(httpx_mock.get_requests()[0].url)
        assert "start_date=2026-01-01" in url
        assert "end_date=2026-03-01" in url

    def test_list_paginated(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_PAGINATED_INVOICES)
        with NordPay("test-key") as client:
            result = client.invoices.list_paginated(offset=0, limit=50)
        assert isinstance(result, PaginatedInvoices)
        assert result.total == 42
        assert result.total_pages == 1
        assert len(result.items) == 1
        assert isinstance(result.items[0], Invoice)

    def test_list_paginated_with_filters(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_PAGINATED_INVOICES)
        with NordPay("test-key") as client:
            client.invoices.list_paginated(
                q="Order",
                currency=["BTC", "USDTERC20"],
                status="pending",
                start_date=datetime(2026, 1, 1),
                sort="created_at:desc",
            )
        url = str(httpx_mock.get_requests()[0].url)
        assert "q=Order" in url
        assert "status=pending" in url
        assert "sort=created_at" in url

    def test_summary(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE_SUMMARY)
        with NordPay("test-key") as client:
            result = client.invoices.summary()
        assert isinstance(result, InvoiceSummary)
        assert result.total_count == 100
        assert result.paid_count == 75
        assert result.paid_amount_usd == Decimal("37500.00")

    def test_postback_logs(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_POSTBACK_LOG, MOCK_POSTBACK_LOG_FAILED])
        with NordPay("test-key") as client:
            logs = client.invoices.postback_logs(1)
        assert len(logs) == 2
        assert isinstance(logs[0], PostbackLog)
        assert logs[0].status == "delivered"
        assert logs[0].is_final is True
        assert logs[1].status == "failed"
        assert logs[1].error_message == "Server returned 500"

    def test_retry_postback(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_POSTBACK_LOG)
        with NordPay("test-key") as client:
            log = client.invoices.retry_postback(1, 2)
        assert isinstance(log, PostbackLog)
        assert httpx_mock.get_requests()[0].method == "POST"
        assert httpx_mock.get_requests()[0].url.path == "/v1/invoice/1/postback-logs/2/retry"


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------


class TestSyncWallets:
    def test_list(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_WALLET])
        with NordPay("test-key") as client:
            wallets = client.wallets.list()
        assert len(wallets) == 1
        assert isinstance(wallets[0], Wallet)
        assert wallets[0].currency == "BTC"
        assert wallets[0].status == "active"

    def test_get(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WALLET)
        with NordPay("test-key") as client:
            wallet = client.wallets.get(42)
        assert wallet.id == 42
        assert wallet.address == "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"

    def test_create_minimal(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WALLET)
        with NordPay("test-key") as client:
            wallet = client.wallets.create(currency="BTC", label="My BTC Wallet")
        assert wallet.id == 42
        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body == {"currency": "BTC", "label": "My BTC Wallet"}

    def test_create_with_postback(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WALLET)
        with NordPay("test-key") as client:
            client.wallets.create(
                currency="BTC",
                label="My Wallet",
                postback_url="https://example.com/hook",
            )
        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body["postback_url"] == "https://example.com/hook"

    def test_qrcode(self, httpx_mock):
        httpx_mock.add_response(json={"qrcode": "iVBORw0KGgo..."})
        with NordPay("test-key") as client:
            qr = client.wallets.qrcode(42)
        assert qr == "iVBORw0KGgo..."
        assert httpx_mock.get_requests()[0].url.path == "/v1/wallet/42/qrcode"

    def test_transactions_all(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_TRANSACTION])
        with NordPay("test-key") as client:
            txs = client.wallets.transactions()
        assert len(txs) == 1
        assert httpx_mock.get_requests()[0].url.path == "/v1/wallet/transactions"

    def test_transactions_for_wallet(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_TRANSACTION])
        with NordPay("test-key") as client:
            client.wallets.transactions(42)
        assert httpx_mock.get_requests()[0].url.path == "/v1/wallet/42/transactions"

    def test_list_paginated(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_PAGINATED_WALLETS)
        with NordPay("test-key") as client:
            result = client.wallets.list_paginated()
        assert isinstance(result, PaginatedWallets)
        assert result.total == 5
        assert len(result.items) == 1
        assert isinstance(result.items[0], Wallet)
        assert result.items[0].currency == "BTC"

    def test_list_paginated_with_filters(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_PAGINATED_WALLETS)
        with NordPay("test-key") as client:
            client.wallets.list_paginated(
                currency="BTC", status="active", sort="created_at:desc",
            )
        url = str(httpx_mock.get_requests()[0].url)
        assert "status=active" in url
        assert "sort=created_at" in url

    def test_limits(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WALLET_LIMITS)
        with NordPay("test-key") as client:
            limits = client.wallets.limits()
        assert isinstance(limits, WalletLimits)
        assert limits.total == 10
        assert limits.used == 3
        assert limits.available == 7

    def test_postback_logs(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_POSTBACK_LOG])
        with NordPay("test-key") as client:
            logs = client.wallets.postback_logs(42)
        assert len(logs) == 1
        assert isinstance(logs[0], PostbackLog)
        assert httpx_mock.get_requests()[0].url.path == "/v1/wallet/42/postback-logs"

    def test_retry_postback(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_POSTBACK_LOG)
        with NordPay("test-key") as client:
            log = client.wallets.retry_postback(42, 1)
        assert isinstance(log, PostbackLog)
        assert httpx_mock.get_requests()[0].url.path == "/v1/wallet/42/postback-logs/1/retry"


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------


class TestSyncBalance:
    def test_get_list_format(self, httpx_mock):
        """API returns balances as a list."""
        httpx_mock.add_response(json=[
            {"currency": "BTC", "amount": "0.5", "amount_usd": "33750.00"},
            {"currency": "USDTERC20", "amount": "1000.00", "amount_usd": "1000.00"},
        ])
        with NordPay("test-key") as client:
            balances = client.balance.get()
        assert len(balances) == 2
        assert balances[0].currency == "BTC"
        assert balances[0].amount == Decimal("0.5")
        assert balances[1].amount_usd == Decimal("1000.00")

    def test_get_dict_format(self, httpx_mock):
        """API returns balances as a flat dict: {"BTC": "0.05", ...}."""
        httpx_mock.add_response(json={
            "BTC": "0.05230000",
            "USDTERC20": "1000.00",
            "ETH": "0",
        })
        with NordPay("test-key") as client:
            balances = client.balance.get()
        assert len(balances) == 3
        currencies = {b.currency for b in balances}
        assert currencies == {"BTC", "USDTERC20", "ETH"}
        btc = next(b for b in balances if b.currency == "BTC")
        assert btc.amount == Decimal("0.05230000")

    def test_get_empty(self, httpx_mock):
        httpx_mock.add_response(json=[])
        with NordPay("test-key") as client:
            balances = client.balance.get()
        assert balances == []

    def test_withdraw_history(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_HISTORY)
        with NordPay("test-key") as client:
            result = client.balance.withdraw_history()
        assert isinstance(result, PaginatedWithdraws)
        assert result.total == 25
        assert len(result.items) == 1
        assert isinstance(result.items[0], WithdrawHistory)
        assert result.items[0].currency == "USDTERC20"
        assert result.items[0].tx_hash == "0xabc123"

    def test_withdraw_history_with_filters(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_HISTORY)
        with NordPay("test-key") as client:
            client.balance.withdraw_history(
                currency="BTC", status="completed", sort="created_at:desc",
            )
        url = str(httpx_mock.get_requests()[0].url)
        assert "currency=BTC" in url
        assert "status=completed" in url

    def test_withdraw_limits(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_LIMITS)
        with NordPay("test-key") as client:
            limits = client.balance.withdraw_limits()
        assert len(limits) == 2
        assert isinstance(limits[0], WithdrawLimit)
        assert limits[0].currency == "BTC"
        assert limits[0].min_amount == Decimal("0.001")
        assert limits[0].max_amount == Decimal("10.0")
        assert limits[1].available_balance == Decimal("15000.0")


# ---------------------------------------------------------------------------
# Withdrawals
# ---------------------------------------------------------------------------


class TestSyncWithdrawals:
    def test_request(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_REQUEST)
        with NordPay("test-key") as client:
            req = client.withdrawals.request(
                currency="USDTERC20",
                address="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18",
                amount=Decimal("100.00"),
            )
        assert isinstance(req, WithdrawRequest)
        assert req.identifier == "wd-123-abc"
        assert req.service_fee == Decimal("1.00")

        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body["currency"] == "USDTERC20"
        assert body["amount"] == "100.00"

    def test_request_with_string_amount(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_REQUEST)
        with NordPay("test-key") as client:
            client.withdrawals.request(currency="USDTERC20", address="0x123", amount="100")
        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body["amount"] == "100"

    def test_confirm(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_CONFIRMATION)
        with NordPay("test-key") as client:
            result = client.withdrawals.confirm("wd-123-abc")
        assert isinstance(result, WithdrawConfirmation)
        assert result.status == "processing"
        assert result.id == 1

    def test_full_flow(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_REQUEST)
        httpx_mock.add_response(json=MOCK_WITHDRAW_CONFIRMATION)
        with NordPay("test-key") as client:
            req = client.withdrawals.request(currency="USDTERC20", address="0x123", amount="100")
            result = client.withdrawals.confirm(req.identifier)
        assert result.status == "processing"

    def test_request_multiple(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_MULTIPLE_WITHDRAW_REQUEST)
        with NordPay("test-key") as client:
            req = client.withdrawals.request_multiple(
                currency="USDTTRC20",
                recipients=[
                    ("TAddr1", Decimal("50.00")),
                    ("TAddr2", Decimal("75.00")),
                    ("TAddr3", Decimal("25.00")),
                ],
            )
        assert isinstance(req, MultipleWithdrawRequest)
        assert req.identifier == "mwd-456-xyz"
        assert req.addresses_count == 3
        assert req.total_amount == Decimal("150.00")

        body = json.loads(httpx_mock.get_requests()[0].content)
        assert body["currency"] == "USDTTRC20"
        assert len(body["addresses_and_amounts"]) == 3
        assert body["addresses_and_amounts"][0] == ["TAddr1", "50.00"]

    def test_confirm_multiple(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_CONFIRMATION)
        with NordPay("test-key") as client:
            result = client.withdrawals.confirm_multiple("mwd-456-xyz")
        assert result.status == "processing"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestSyncErrors:
    def test_authentication_error_401(self, httpx_mock):
        httpx_mock.add_response(status_code=401, json={"detail": "Invalid X-API-Key"})
        with NordPay("bad-key") as client, pytest.raises(AuthenticationError) as exc_info:
            client.invoices.list()
        assert exc_info.value.status_code == 401
        assert "Invalid X-API-Key" in exc_info.value.detail

    def test_bad_request_400(self, httpx_mock):
        httpx_mock.add_response(status_code=400, json={"detail": "Invalid amount format"})
        with NordPay("test-key") as client, pytest.raises(BadRequestError) as exc_info:
            client.invoices.create(amount="bad", label="x", expires_time=60)
        assert exc_info.value.status_code == 400
        assert exc_info.value.response_body == {"detail": "Invalid amount format"}

    def test_forbidden_403(self, httpx_mock):
        httpx_mock.add_response(status_code=403, json={"detail": "Access denied"})
        with NordPay("test-key") as client, pytest.raises(ForbiddenError) as exc_info:
            client.invoices.create(amount="100 USD", label="x", expires_time=60)
        assert exc_info.value.status_code == 403

    def test_not_found_404(self, httpx_mock):
        httpx_mock.add_response(status_code=404, json={"detail": "Invoice not found"})
        with NordPay("test-key") as client, pytest.raises(NotFoundError):
            client.invoices.get("nonexistent")

    def test_rate_limit_429(self, httpx_mock):
        httpx_mock.add_response(
            status_code=429,
            json={"detail": "Too many requests"},
            headers={"Retry-After": "30"},
        )
        with NordPay("test-key", max_retries=0) as client, pytest.raises(RateLimitError) as exc_info:
            client.invoices.list()
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 30.0

    def test_server_error_500(self, httpx_mock):
        httpx_mock.add_response(status_code=500, json={"detail": "Internal error"})
        with NordPay("test-key", max_retries=0) as client, pytest.raises(ServerError) as exc_info:
            client.invoices.list()
        assert exc_info.value.status_code == 500

    def test_server_error_502(self, httpx_mock):
        httpx_mock.add_response(status_code=502, text="Bad Gateway")
        with NordPay("test-key", max_retries=0) as client, pytest.raises(ServerError):
            client.invoices.list()

    def test_error_repr(self, httpx_mock):
        httpx_mock.add_response(status_code=401, json={"detail": "Invalid key"})
        with NordPay("bad-key") as client, pytest.raises(AuthenticationError) as exc_info:
            client.invoices.list()
        assert "AuthenticationError" in repr(exc_info.value)
        assert "401" in repr(exc_info.value)


# ---------------------------------------------------------------------------
# Client configuration
# ---------------------------------------------------------------------------


class TestSyncClientConfig:
    def test_context_manager(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay() as client:
            client.currencies.list()
        # Should not raise after close

    def test_api_key_in_headers(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_INVOICE])
        with NordPay("my-secret-key") as client:
            client.invoices.list()
        req = httpx_mock.get_requests()[0]
        assert req.headers["X-API-Key"] == "my-secret-key"

    def test_user_agent(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay() as client:
            client.currencies.list()
        req = httpx_mock.get_requests()[0]
        assert "nordpay-python/" in req.headers["User-Agent"]

    def test_no_api_key(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        with NordPay() as client:
            client.currencies.list()
        req = httpx_mock.get_requests()[0]
        assert "X-API-Key" not in req.headers

    def test_explicit_close(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        client = NordPay()
        client.currencies.list()
        client.close()


# ---------------------------------------------------------------------------
# Client-side validation
# ---------------------------------------------------------------------------


class TestSyncValidation:
    def test_invoice_empty_amount(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="amount must not be empty"):
            client.invoices.create(amount="", label="Test", expires_time=60)

    def test_invoice_empty_label(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="label must not be empty"):
            client.invoices.create(amount="100 USD", label="", expires_time=60)

    def test_invoice_label_too_long(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="at most 255"):
            client.invoices.create(amount="100 USD", label="x" * 256, expires_time=60)

    def test_invoice_expires_time_too_low(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="between 30 and 1440"):
            client.invoices.create(amount="100 USD", label="Test", expires_time=5)

    def test_invoice_expires_time_too_high(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="between 30 and 1440"):
            client.invoices.create(amount="100 USD", label="Test", expires_time=2000)

    def test_invoice_too_few_allowed_currencies(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="at least 2"):
            client.invoices.create(
                amount="100 USD", label="Test", expires_time=60,
                allowed_currencies=["BTC"],
            )

    def test_wallet_empty_label(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="label must not be empty"):
            client.wallets.create(currency="BTC", label="")

    def test_wallet_label_too_long(self):
        with NordPay("key") as client, pytest.raises(ValueError, match="at most 255"):
            client.wallets.create(currency="BTC", label="x" * 256)


# ---------------------------------------------------------------------------
# Auto-pagination
# ---------------------------------------------------------------------------


class TestSyncAutoPaginate:
    def test_invoices_single_page(self, httpx_mock):
        httpx_mock.add_response(json={
            "items": [{"id": 1, "uuid": "a", "amount": "1", "amount_usd": "1",
                       "received_amount": "0", "received_amount_usd": "0",
                       "label": "x", "created_at": "2026-01-01T00:00:00Z",
                       "expires_at": "2026-01-01T01:00:00Z", "status": "paid"}],
            "total": 1, "offset": 0, "limit": 50, "total_pages": 1,
        })
        with NordPay("key") as client:
            items = list(client.invoices.auto_paginate())
        assert len(items) == 1
        assert isinstance(items[0], Invoice)

    def test_invoices_multiple_pages(self, httpx_mock):
        inv = {"id": 1, "uuid": "a", "amount": "1", "amount_usd": "1",
               "received_amount": "0", "received_amount_usd": "0",
               "label": "x", "created_at": "2026-01-01T00:00:00Z",
               "expires_at": "2026-01-01T01:00:00Z", "status": "paid"}
        httpx_mock.add_response(json={
            "items": [inv, inv], "total": 3, "offset": 0, "limit": 2, "total_pages": 2,
        })
        httpx_mock.add_response(json={
            "items": [inv], "total": 3, "offset": 2, "limit": 2, "total_pages": 2,
        })
        with NordPay("key") as client:
            items = list(client.invoices.auto_paginate(limit=2))
        assert len(items) == 3
        assert httpx_mock.request_count == 2

    def test_wallets_auto_paginate(self, httpx_mock):
        from .conftest import MOCK_PAGINATED_WALLETS
        httpx_mock.add_response(json=MOCK_PAGINATED_WALLETS)
        with NordPay("key") as client:
            items = list(client.wallets.auto_paginate())
        assert len(items) == 1
        assert isinstance(items[0], Wallet)

    def test_withdraws_auto_paginate(self, httpx_mock):
        from .conftest import MOCK_WITHDRAW_HISTORY
        httpx_mock.add_response(json=MOCK_WITHDRAW_HISTORY)
        with NordPay("key") as client:
            items = list(client.balance.auto_paginate_withdraws())
        assert len(items) == 1
