"""Tests for NordPay asynchronous client."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from nordpay import (
    AsyncNordPay,
    AuthenticationError,
    BadRequestError,
    CreatedInvoice,
    Currency,
    FiatCurrency,
    Invoice,
    InvoiceSummary,
    MultipleWithdrawRequest,
    NotFoundError,
    PaginatedInvoices,
    PaginatedWallets,
    PaginatedWithdraws,
    PostbackLog,
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


class TestAsyncCurrencies:
    @pytest.mark.asyncio
    async def test_list(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        async with AsyncNordPay() as client:
            result = await client.currencies.list()
        assert len(result) == 2
        assert isinstance(result[0], Currency)
        assert result[0].name == "BTC"

    @pytest.mark.asyncio
    async def test_rates(self, httpx_mock):
        # rates() is derived from list() — the /rates endpoint no longer exists
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        async with AsyncNordPay() as client:
            result = await client.currencies.rates()
        assert len(result) == 2
        assert result[0].name == "BTC"
        assert result[0].rate == Decimal("67500.00")
        assert httpx_mock.get_requests()[0].url.path == "/v1/currencies/"


class TestAsyncFiatCurrencies:
    @pytest.mark.asyncio
    async def test_list(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_FIAT_CURRENCIES)
        async with AsyncNordPay() as client:
            result = await client.fiat_currencies.list()
        assert len(result) == 2
        assert isinstance(result[0], FiatCurrency)

    @pytest.mark.asyncio
    async def test_rates(self, httpx_mock):
        # rates() is derived from list() — the /rates endpoint no longer exists
        httpx_mock.add_response(json=MOCK_FIAT_CURRENCIES)
        async with AsyncNordPay() as client:
            result = await client.fiat_currencies.rates()
        assert len(result) == 2
        assert result[0].code == "USD"
        assert httpx_mock.get_requests()[0].url.path == "/v1/fiat-currencies/"


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


class TestAsyncInvoices:
    @pytest.mark.asyncio
    async def test_create(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE)
        async with AsyncNordPay("test-key") as client:
            invoice = await client.invoices.create(
                amount="100 USD",
                label="Test",
                expires_time=60,
            )
        assert isinstance(invoice, CreatedInvoice)
        assert invoice.url == "https://app.nord-pay.com/invoice/abc-123-def"

    @pytest.mark.asyncio
    async def test_list(self, httpx_mock):
        # list() now paginates over /v1/invoice/list (bare /v1/invoice/ was removed)
        httpx_mock.add_response(json=MOCK_PAGINATED_INVOICES)
        async with AsyncNordPay("test-key") as client:
            result = await client.invoices.list()
        assert len(result) == 1
        assert isinstance(result[0], Invoice)
        assert httpx_mock.get_requests()[0].url.path == "/v1/invoice/list"

    @pytest.mark.asyncio
    async def test_get(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE)
        async with AsyncNordPay("test-key") as client:
            invoice = await client.invoices.get("abc-123-def")
        assert invoice.uuid == "abc-123-def"

    @pytest.mark.asyncio
    async def test_transactions(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_TRANSACTION])
        async with AsyncNordPay("test-key") as client:
            txs = await client.invoices.transactions()
        assert len(txs) == 1
        assert isinstance(txs[0], Transaction)

    @pytest.mark.asyncio
    async def test_transactions_with_dates(self, httpx_mock):
        httpx_mock.add_response(json=[])
        async with AsyncNordPay("test-key") as client:
            await client.invoices.transactions(
                start_date=datetime(2026, 1, 1),
                end_date=datetime(2026, 3, 1),
            )
        url = str(httpx_mock.get_requests()[0].url)
        assert "start_date=" in url
        assert "end_date=" in url

    @pytest.mark.asyncio
    async def test_list_paginated(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_PAGINATED_INVOICES)
        async with AsyncNordPay("test-key") as client:
            result = await client.invoices.list_paginated()
        assert isinstance(result, PaginatedInvoices)
        assert result.total == 42
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_summary(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_INVOICE_SUMMARY)
        async with AsyncNordPay("test-key") as client:
            result = await client.invoices.summary()
        assert isinstance(result, InvoiceSummary)
        assert result.total_count == 100

    @pytest.mark.asyncio
    async def test_postback_logs(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_POSTBACK_LOG, MOCK_POSTBACK_LOG_FAILED])
        async with AsyncNordPay("test-key") as client:
            logs = await client.invoices.postback_logs(1)
        assert len(logs) == 2
        assert isinstance(logs[0], PostbackLog)

    @pytest.mark.asyncio
    async def test_retry_postback(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_POSTBACK_LOG)
        async with AsyncNordPay("test-key") as client:
            log = await client.invoices.retry_postback(1, 2)
        assert isinstance(log, PostbackLog)


# ---------------------------------------------------------------------------
# Wallets
# ---------------------------------------------------------------------------


class TestAsyncWallets:
    @pytest.mark.asyncio
    async def test_list(self, httpx_mock):
        # list() now paginates over /v1/wallet/list (bare /v1/wallet/ was removed)
        httpx_mock.add_response(json=MOCK_PAGINATED_WALLETS)
        async with AsyncNordPay("test-key") as client:
            wallets = await client.wallets.list()
        assert len(wallets) == 1
        assert isinstance(wallets[0], Wallet)
        assert httpx_mock.get_requests()[0].url.path == "/v1/wallet/list"

    @pytest.mark.asyncio
    async def test_create(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WALLET)
        async with AsyncNordPay("test-key") as client:
            wallet = await client.wallets.create(currency="BTC", label="Test")
        assert wallet.id == 42

    @pytest.mark.asyncio
    async def test_get(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WALLET)
        async with AsyncNordPay("test-key") as client:
            wallet = await client.wallets.get(42)
        assert wallet.currency == "BTC"

    @pytest.mark.asyncio
    async def test_qrcode(self, httpx_mock):
        httpx_mock.add_response(json={"qrcode": "iVBORw0KGgo..."})
        async with AsyncNordPay("test-key") as client:
            qr = await client.wallets.qrcode(42)
        assert qr == "iVBORw0KGgo..."

    @pytest.mark.asyncio
    async def test_transactions(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_TRANSACTION])
        async with AsyncNordPay("test-key") as client:
            txs = await client.wallets.transactions(42)
        assert len(txs) == 1

    @pytest.mark.asyncio
    async def test_list_paginated(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_PAGINATED_WALLETS)
        async with AsyncNordPay("test-key") as client:
            result = await client.wallets.list_paginated()
        assert isinstance(result, PaginatedWallets)
        assert result.total == 5

    @pytest.mark.asyncio
    async def test_limits(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WALLET_LIMITS)
        async with AsyncNordPay("test-key") as client:
            limits = await client.wallets.limits()
        assert isinstance(limits, WalletLimits)
        assert limits.available == 7

    @pytest.mark.asyncio
    async def test_postback_logs(self, httpx_mock):
        httpx_mock.add_response(json=[MOCK_POSTBACK_LOG])
        async with AsyncNordPay("test-key") as client:
            logs = await client.wallets.postback_logs(42)
        assert len(logs) == 1
        assert isinstance(logs[0], PostbackLog)

    @pytest.mark.asyncio
    async def test_retry_postback(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_POSTBACK_LOG)
        async with AsyncNordPay("test-key") as client:
            log = await client.wallets.retry_postback(42, 1)
        assert isinstance(log, PostbackLog)


# ---------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------


class TestAsyncBalance:
    @pytest.mark.asyncio
    async def test_get(self, httpx_mock):
        httpx_mock.add_response(
            json=[
                {"currency": "BTC", "amount": "0.5", "amount_usd": "33750.00"},
            ]
        )
        async with AsyncNordPay("test-key") as client:
            balances = await client.balance.get()
        assert len(balances) == 1
        assert balances[0].currency == "BTC"

    @pytest.mark.asyncio
    async def test_get_dict_format(self, httpx_mock):
        """API returns balances as a flat dict: {"BTC": "0.05", ...}."""
        httpx_mock.add_response(
            json={
                "BTC": "0.05230000",
                "USDTERC20": "1000.00",
            }
        )
        async with AsyncNordPay("test-key") as client:
            balances = await client.balance.get()
        assert len(balances) == 2
        btc = next(b for b in balances if b.currency == "BTC")
        assert btc.amount == Decimal("0.05230000")

    @pytest.mark.asyncio
    async def test_withdraw_history(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_HISTORY)
        async with AsyncNordPay("test-key") as client:
            result = await client.balance.withdraw_history()
        assert isinstance(result, PaginatedWithdraws)
        assert result.total == 25
        assert isinstance(result.items[0], WithdrawHistory)

    @pytest.mark.asyncio
    async def test_withdraw_limits(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_LIMITS)
        async with AsyncNordPay("test-key") as client:
            limits = await client.balance.withdraw_limits()
        assert len(limits) == 2
        assert isinstance(limits[0], WithdrawLimit)
        assert limits[0].currency == "BTC"


# ---------------------------------------------------------------------------
# Withdrawals
# ---------------------------------------------------------------------------


class TestAsyncWithdrawals:
    @pytest.mark.asyncio
    async def test_request(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_REQUEST)
        async with AsyncNordPay("test-key") as client:
            req = await client.withdrawals.request(
                currency="USDTERC20",
                address="0x123",
                amount=Decimal("100"),
            )
        assert isinstance(req, WithdrawRequest)
        assert req.identifier == "wd-123-abc"

    @pytest.mark.asyncio
    async def test_confirm(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_CONFIRMATION)
        async with AsyncNordPay("test-key") as client:
            result = await client.withdrawals.confirm("wd-123-abc")
        assert isinstance(result, WithdrawConfirmation)
        assert result.status == "processing"

    @pytest.mark.asyncio
    async def test_request_multiple(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_MULTIPLE_WITHDRAW_REQUEST)
        async with AsyncNordPay("test-key") as client:
            req = await client.withdrawals.request_multiple(
                currency="USDTTRC20",
                recipients=[("TAddr1", "50"), ("TAddr2", "75")],
            )
        assert isinstance(req, MultipleWithdrawRequest)
        assert req.identifier == "mwd-456-xyz"

    @pytest.mark.asyncio
    async def test_confirm_multiple(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_CONFIRMATION)
        async with AsyncNordPay("test-key") as client:
            result = await client.withdrawals.confirm_multiple("mwd-456-xyz")
        assert result.status == "processing"

    @pytest.mark.asyncio
    async def test_full_flow(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_WITHDRAW_REQUEST)
        httpx_mock.add_response(json=MOCK_WITHDRAW_CONFIRMATION)
        async with AsyncNordPay("test-key") as client:
            req = await client.withdrawals.request(currency="USDTERC20", address="0x123", amount="100")
            result = await client.withdrawals.confirm(req.identifier)
        assert result.status == "processing"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TestAsyncErrors:
    @pytest.mark.asyncio
    async def test_401(self, httpx_mock):
        httpx_mock.add_response(status_code=401, json={"detail": "Invalid X-API-Key"})
        async with AsyncNordPay("bad-key") as client:
            with pytest.raises(AuthenticationError):
                await client.invoices.list()

    @pytest.mark.asyncio
    async def test_400(self, httpx_mock):
        httpx_mock.add_response(status_code=400, json={"detail": "Bad request"})
        async with AsyncNordPay("test-key") as client:
            with pytest.raises(BadRequestError):
                await client.invoices.create(amount="bad", label="x", expires_time=60)

    @pytest.mark.asyncio
    async def test_404(self, httpx_mock):
        httpx_mock.add_response(status_code=404, json={"detail": "Not found"})
        async with AsyncNordPay("test-key") as client:
            with pytest.raises(NotFoundError):
                await client.invoices.get("nonexistent")

    @pytest.mark.asyncio
    async def test_500(self, httpx_mock):
        httpx_mock.add_response(status_code=500, json={"detail": "Internal error"})
        async with AsyncNordPay("test-key", max_retries=0) as client:
            with pytest.raises(ServerError):
                await client.invoices.list()


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------


class TestAsyncClientLifecycle:
    @pytest.mark.asyncio
    async def test_context_manager(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        async with AsyncNordPay() as client:
            await client.currencies.list()

    @pytest.mark.asyncio
    async def test_explicit_close(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_CURRENCIES)
        client = AsyncNordPay()
        await client.currencies.list()
        await client.close()

    @pytest.mark.asyncio
    async def test_api_key_header(self, httpx_mock):
        httpx_mock.add_response(json=MOCK_PAGINATED_INVOICES)
        async with AsyncNordPay("async-key") as client:
            await client.invoices.list()
        req = httpx_mock.get_requests()[0]
        assert req.headers["X-API-Key"] == "async-key"
