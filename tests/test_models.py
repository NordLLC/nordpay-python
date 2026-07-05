"""Tests for Pydantic model validation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from nordpay.models import (
    Balance,
    CreatedInvoice,
    Currency,
    CurrencyRate,
    FiatCurrency,
    FiatCurrencyRate,
    Invoice,
    InvoiceSummary,
    MultipleWithdrawRequest,
    PostbackEvent,
    Transaction,
    Wallet,
    WithdrawConfirmation,
    WithdrawRequest,
)


class TestCurrency:
    def test_full(self):
        c = Currency(
            name="BTC",
            network="bitcoin",
            decimals=8,
            confirmations=2,
            network_fee=Decimal("0.0001"),
            min_deposit=Decimal("0.0001"),
            is_available=True,
            can_exchange=True,
            can_withdraw=True,
            min_withdraw=Decimal("0.001"),
            rate=Decimal("67500"),
        )
        assert c.name == "BTC"
        assert c.token is None
        assert c.contract is None

    def test_with_token(self):
        c = Currency(
            name="USDTERC20",
            token="USDT",
            network="ethereum",
            contract="0xdAC17F958D2ee523a2206206994597C13D831ec7",
            decimals=6,
            confirmations=12,
            network_fee=Decimal("5"),
            min_deposit=Decimal("10"),
            is_available=True,
            can_exchange=True,
            can_withdraw=True,
            min_withdraw=Decimal("20"),
        )
        assert c.token == "USDT"
        assert c.rate is None

    def test_decimal_from_string(self):
        c = Currency(
            name="BTC",
            network="bitcoin",
            decimals=8,
            confirmations=2,
            network_fee="0.0001",
            min_deposit="0.0001",  # type: ignore[arg-type]
            is_available=True,
            can_exchange=True,
            can_withdraw=True,
            min_withdraw="0.001",
            rate="67500.50",  # type: ignore[arg-type]
        )
        assert c.rate == Decimal("67500.50")
        assert isinstance(c.network_fee, Decimal)


class TestCurrencyRate:
    def test_basic(self):
        r = CurrencyRate(name="BTC", rate=Decimal("67500"))
        assert r.name == "BTC"
        assert r.rate == Decimal("67500")


class TestFiatCurrency:
    def test_full(self):
        f = FiatCurrency(
            id=1,
            name="US Dollar",
            code="USD",
            can_exchange=True,
            supports_sepa=False,
            sepa_fee=Decimal("0"),
            supports_swift=True,
            swift_fee=Decimal("25"),
            can_withdraw=True,
            min_withdraw=Decimal("100"),
        )
        assert f.code == "USD"
        assert f.icon is None
        assert f.rate is None


class TestFiatCurrencyRate:
    def test_basic(self):
        r = FiatCurrencyRate(code="EUR", rate=Decimal("0.92"))
        assert r.rate == Decimal("0.92")

    def test_no_rate(self):
        r = FiatCurrencyRate(code="XYZ")
        assert r.rate is None


class TestInvoice:
    def test_full(self):
        inv = Invoice(
            id=1,
            uuid="abc-123",
            amount=Decimal("0.00148"),
            amount_usd=Decimal("100"),
            received_amount=Decimal("0"),
            received_amount_usd=Decimal("0"),
            label="Test",
            created_at=datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc),
            expires_at=datetime(2026, 3, 7, 13, 0, tzinfo=timezone.utc),
            status="pending",
        )
        assert inv.uuid == "abc-123"
        assert inv.currency is None
        assert inv.allowed_currencies is None
        assert inv.address is None


class TestCreatedInvoice:
    def test_with_url(self):
        inv = CreatedInvoice(
            id=1,
            uuid="abc-123",
            amount=Decimal("0.00148"),
            amount_usd=Decimal("100"),
            received_amount=Decimal("0"),
            received_amount_usd=Decimal("0"),
            label="Test",
            created_at=datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc),
            expires_at=datetime(2026, 3, 7, 13, 0, tzinfo=timezone.utc),
            status="pending",
            url="https://app.nord-pay.com/invoice/abc-123",
        )
        assert inv.url.startswith("https://")
        assert inv.confirmations == 0
        assert inv.tx_hash is None


class TestWallet:
    def test_full(self):
        w = Wallet(
            id=42,
            label="My Wallet",
            currency="BTC",
            address="bc1q...",
            status="active",
            created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            expires_at=datetime(2027, 3, 1, tzinfo=timezone.utc),
        )
        assert w.id == 42
        assert w.postback_url is None


class TestTransaction:
    def test_full(self):
        tx = Transaction(
            id=100,
            currency=Currency(
                name="BTC",
                network="bitcoin",
                decimals=8,
                confirmations=2,
                network_fee=Decimal("0.0001"),
                min_deposit=Decimal("0.0001"),
                is_available=True,
                can_exchange=True,
                can_withdraw=True,
                min_withdraw=Decimal("0.001"),
            ),
            source_type="invoice",
            source={"id": 1},
            amount=Decimal("0.00148"),
            amount_usd=Decimal("100"),
            network_fee=Decimal("0.0001"),
            network_fee_usd=Decimal("6.75"),
            service_fee=Decimal("0.00001"),
            service_fee_usd=Decimal("0.68"),
            tx_hash="abc123",
            status="paid",
            is_postback_sent=True,
            created_at=datetime(2026, 3, 7, tzinfo=timezone.utc),
        )
        assert tx.source_type == "invoice"
        assert tx.status == "paid"

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            Transaction(
                id=1,
                currency=Currency(
                    name="BTC",
                    network="bitcoin",
                    decimals=8,
                    confirmations=2,
                    network_fee=Decimal("0"),
                    min_deposit=Decimal("0"),
                    is_available=True,
                    can_exchange=True,
                    can_withdraw=True,
                    min_withdraw=Decimal("0"),
                ),
                source_type="invoice",
                amount=Decimal("1"),
                amount_usd=Decimal("1"),
                network_fee=Decimal("0"),
                network_fee_usd=Decimal("0"),
                service_fee=Decimal("0"),
                service_fee_usd=Decimal("0"),
                tx_hash="abc",
                status="invalid_status",  # type: ignore[arg-type]
                is_postback_sent=False,
                created_at=datetime.now(tz=timezone.utc),
            )


class TestBalance:
    def test_basic(self):
        b = Balance(currency="BTC", amount=Decimal("0.5"), amount_usd=Decimal("33750"))
        assert b.currency == "BTC"
        assert b.amount == Decimal("0.5")


class TestWithdrawRequest:
    def test_basic(self):
        wr = WithdrawRequest(
            identifier="wd-123",
            currency="USDTERC20",
            address="0x123",
            amount=Decimal("100"),
            amount_usd=Decimal("100"),
            service_fee=Decimal("1"),
            service_fee_usd=Decimal("1"),
            expires_at=datetime(2026, 3, 7, tzinfo=timezone.utc),
        )
        assert wr.identifier == "wd-123"


class TestMultipleWithdrawRequest:
    def test_basic(self):
        mwr = MultipleWithdrawRequest(
            identifier="mwd-456",
            currency="USDTTRC20",
            total_amount=Decimal("150"),
            total_amount_usd=Decimal("150"),
            total_service_fee=Decimal("1.5"),
            total_service_fee_usd=Decimal("1.5"),
            addresses_count=3,
            expires_at=datetime(2026, 3, 7, tzinfo=timezone.utc),
        )
        assert mwr.addresses_count == 3


class TestWithdrawConfirmation:
    def test_basic(self):
        wc = WithdrawConfirmation(detail="ok", status="processing", id=1)
        assert wc.status == "processing"


class TestPostbackEvent:
    def test_invoice_event(self):
        pe = PostbackEvent(
            postback_secret="secret",
            postback_type="invoice_expired",
            object_type="invoice",
            object_id=42,
            status="expired",
        )
        assert pe.postback_type == "invoice_expired"
        assert pe.tx_id is None

    def test_transaction_event(self):
        pe = PostbackEvent(
            postback_secret="secret",
            postback_type="transaction",
            tx_id=100,
            tx_hash="abc",
            amount=Decimal("0.5"),
        )
        assert pe.tx_id == 100

    def test_extra_fields(self):
        pe = PostbackEvent(
            postback_secret="secret",
            postback_type="custom",
            unknown_field="value",
        )
        assert pe.model_extra is not None
        assert pe.model_extra["unknown_field"] == "value"


# ---------------------------------------------------------------------------
# 2026-07 API alignment — new fields exposed by the live /v1 responses
# ---------------------------------------------------------------------------


class TestApiAlignment202607:
    def test_invoice_has_explorer_url_and_tx_hash(self):
        inv = Invoice(
            id=1,
            uuid="abc-123",
            amount=Decimal("0"),
            amount_usd=Decimal("0"),
            received_amount=Decimal("0"),
            received_amount_usd=Decimal("0"),
            label="x",
            created_at=datetime(2026, 7, 5, tzinfo=timezone.utc),
            expires_at=datetime(2026, 7, 5, 1, tzinfo=timezone.utc),
            status="pending",
        )
        # both default to None and are accepted when present
        assert inv.explorer_url is None
        assert inv.tx_hash is None
        inv2 = inv.model_copy(update={"explorer_url": "https://tronscan.org/#/tx/deadbeef", "tx_hash": "deadbeef"})
        assert inv2.explorer_url.endswith("deadbeef")
        assert inv2.tx_hash == "deadbeef"

    def test_created_invoice_inherits_explorer_url(self):
        inv = CreatedInvoice(
            id=1,
            uuid="abc",
            amount=Decimal("0"),
            amount_usd=Decimal("0"),
            received_amount=Decimal("0"),
            received_amount_usd=Decimal("0"),
            label="x",
            created_at=datetime(2026, 7, 5, tzinfo=timezone.utc),
            expires_at=datetime(2026, 7, 5, 1, tzinfo=timezone.utc),
            status="pending",
            url="https://panel.nord-pay.com/invoice/abc",
            explorer_url=None,
        )
        assert inv.explorer_url is None
        assert inv.confirmations == 0

    def test_invoice_summary_new_counts(self):
        s = InvoiceSummary(
            total_count=3,
            paid_count=1,
            pending_count=1,
            expired_count=1,
            cancelled_count=2,
            partially_paid_count=1,
            total_amount_usd=Decimal("100"),
            paid_amount_usd=Decimal("40"),
        )
        assert s.cancelled_count == 2
        assert s.partially_paid_count == 1

    def test_invoice_summary_counts_default_zero(self):
        # older payloads without the new counters still parse
        s = InvoiceSummary(
            total_count=0,
            paid_count=0,
            pending_count=0,
            expired_count=0,
            total_amount_usd=Decimal("0"),
            paid_amount_usd=Decimal("0"),
        )
        assert s.cancelled_count == 0
        assert s.partially_paid_count == 0

    def test_transaction_nullable_fees_and_tx_hash(self):
        tx = Transaction(
            id=1,
            currency=Currency(
                name="USDTTRC20",
                token="USDT",
                network="tron",
                contract="T...",
                decimals=6,
                confirmations=19,
                network_fee=Decimal("1"),
                min_deposit=Decimal("1"),
                is_available=True,
                can_exchange=True,
                can_withdraw=True,
                min_withdraw=Decimal("1"),
            ),
            source_type="wallet",
            amount=Decimal("10"),
            amount_usd=Decimal("10"),
            status="pending",
            created_at=datetime(2026, 7, 5, tzinfo=timezone.utc),
        )
        # fees, tx_hash, explorer_url and is_postback_sent are all optional now
        assert tx.network_fee is None
        assert tx.service_fee_usd is None
        assert tx.tx_hash is None
        assert tx.explorer_url is None
        assert tx.is_postback_sent is False
