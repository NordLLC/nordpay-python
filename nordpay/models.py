"""NordPay SDK data models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Currency models
# ---------------------------------------------------------------------------


class Currency(BaseModel):
    """Cryptocurrency supported by NordPay."""

    name: str
    token: str | None = None
    network: str
    contract: str | None = None
    decimals: int
    confirmations: int
    network_fee: Decimal
    min_deposit: Decimal
    icon: str | None = None
    is_available: bool
    can_exchange: bool
    can_withdraw: bool
    min_withdraw: Decimal
    rate: Decimal | None = None


class CurrencyRate(BaseModel):
    """Cryptocurrency exchange rate (to USD)."""

    name: str
    rate: Decimal


class FiatCurrency(BaseModel):
    """Fiat currency supported by NordPay."""

    id: int
    name: str
    code: str
    icon: str | None = None
    can_exchange: bool
    supports_sepa: bool
    sepa_fee: Decimal
    supports_swift: bool
    swift_fee: Decimal
    can_withdraw: bool
    min_withdraw: Decimal
    rate: Decimal | None = None


class FiatCurrencyRate(BaseModel):
    """Fiat currency exchange rate."""

    code: str
    rate: Decimal | None = None


# ---------------------------------------------------------------------------
# Invoice models
# ---------------------------------------------------------------------------


class Invoice(BaseModel):
    """Invoice (payment request)."""

    id: int
    uuid: str
    currency: str | None = None
    allowed_currencies: list[str] | None = None
    address: str | None = None
    amount: Decimal
    amount_usd: Decimal
    received_amount: Decimal
    received_amount_usd: Decimal
    label: str
    postback_url: str | None = None
    success_url: str | None = None
    fail_url: str | None = None
    created_at: datetime
    expires_at: datetime
    status: str


class CreatedInvoice(Invoice):
    """Invoice returned after creation — includes payment URL and extra fields."""

    confirmations: int = 0
    url: str
    tx_hash: str | None = None


# ---------------------------------------------------------------------------
# Wallet models
# ---------------------------------------------------------------------------


class Wallet(BaseModel):
    """Crypto wallet."""

    id: int
    label: str
    postback_url: str | None = None
    currency: str
    address: str
    status: str
    created_at: datetime
    expires_at: datetime


# ---------------------------------------------------------------------------
# Transaction models
# ---------------------------------------------------------------------------


class Transaction(BaseModel):
    """Blockchain transaction."""

    id: int
    currency: Currency
    source_type: Literal["wallet", "invoice"]
    source: dict[str, Any] = Field(default_factory=dict)
    amount: Decimal
    amount_usd: Decimal
    network_fee: Decimal
    network_fee_usd: Decimal
    service_fee: Decimal
    service_fee_usd: Decimal
    tx_hash: str
    status: Literal["pending", "paid", "cancelled", "refunded"]
    is_postback_sent: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Balance models
# ---------------------------------------------------------------------------


class Balance(BaseModel):
    """Currency balance entry."""

    currency: str
    amount: Decimal
    amount_usd: Decimal


# ---------------------------------------------------------------------------
# Withdraw models
# ---------------------------------------------------------------------------


class WithdrawRequest(BaseModel):
    """Withdraw request (awaiting confirmation)."""

    identifier: str
    currency: str
    address: str
    amount: Decimal
    amount_usd: Decimal
    service_fee: Decimal
    service_fee_usd: Decimal
    expires_at: datetime


class MultipleWithdrawRequest(BaseModel):
    """Multiple withdraw request (awaiting confirmation)."""

    identifier: str
    currency: str
    total_amount: Decimal
    total_amount_usd: Decimal
    total_service_fee: Decimal
    total_service_fee_usd: Decimal
    addresses_count: int
    expires_at: datetime


class WithdrawConfirmation(BaseModel):
    """Withdraw confirmation response."""

    detail: str
    status: str
    id: int


# ---------------------------------------------------------------------------
# Postback / webhook models
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Pagination models
# ---------------------------------------------------------------------------


class PaginatedInvoices(BaseModel):
    """Paginated list of invoices."""

    items: list[Invoice]
    total: int
    offset: int
    limit: int
    total_pages: int = 0


class PaginatedWallets(BaseModel):
    """Paginated list of wallets."""

    items: list[Wallet]
    total: int
    offset: int
    limit: int
    total_pages: int = 0


class PaginatedTransactions(BaseModel):
    """Paginated list of transactions."""

    items: list[Transaction]
    total: int
    offset: int
    limit: int
    total_pages: int = 0


# ---------------------------------------------------------------------------
# Invoice summary
# ---------------------------------------------------------------------------


class InvoiceSummary(BaseModel):
    """Aggregated invoice statistics."""

    total_count: int
    paid_count: int
    pending_count: int
    expired_count: int
    total_amount_usd: Decimal
    paid_amount_usd: Decimal


# ---------------------------------------------------------------------------
# Postback log
# ---------------------------------------------------------------------------


class PostbackLog(BaseModel):
    """Postback (webhook) delivery log entry."""

    id: int
    event: str
    endpoint: str
    status_code: int | None = None
    status: str
    latency_ms: int | None = None
    attempt: int
    max_attempts: int
    request_payload: dict[str, Any] | None = None
    response_body: str | None = None
    error_message: str | None = None
    is_final: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Wallet limits
# ---------------------------------------------------------------------------


class WalletLimits(BaseModel):
    """Wallet creation limits for the current account."""

    total: int
    used: int
    available: int


# ---------------------------------------------------------------------------
# Withdraw history & limits
# ---------------------------------------------------------------------------


class WithdrawHistory(BaseModel):
    """Single withdrawal history entry."""

    id: int
    currency: str
    address: str
    tx_hash: str | None = None
    amount: Decimal
    amount_usd: Decimal
    service_fee: Decimal
    service_fee_usd: Decimal
    status: str
    created_at: datetime


class PaginatedWithdraws(BaseModel):
    """Paginated list of withdrawal history."""

    items: list[WithdrawHistory]
    total: int
    offset: int
    limit: int
    total_pages: int = 0


class WithdrawLimit(BaseModel):
    """Per-currency withdrawal limit."""

    currency: str
    min_amount: Decimal
    max_amount: Decimal
    fee_percent: Decimal
    available_balance: Decimal


# ---------------------------------------------------------------------------
# Postback / webhook models
# ---------------------------------------------------------------------------


class PostbackEvent(BaseModel):
    """Parsed postback (webhook) event from NordPay.

    This represents the JSON payload NordPay sends to your ``postback_url``.
    """

    postback_secret: str
    postback_type: str
    object_type: str | None = None
    object_id: int | None = None
    status: str | None = None
    label: str | None = None
    currency: str | None = None
    expires_at: datetime | None = None

    # Invoice fields
    received_amount: Decimal | None = None
    received_amount_usd: Decimal | None = None
    created_at: datetime | None = None

    # Transaction fields
    tx_id: int | None = None
    tx_hash: str | None = None
    tx_type: str | None = None
    amount: Decimal | None = None
    amount_usd: Decimal | None = None
    network_fee: Decimal | None = None
    network_fee_usd: Decimal | None = None
    service_fee: Decimal | None = None
    service_fee_usd: Decimal | None = None
    receive_amount: Decimal | None = None
    receive_amount_usd: Decimal | None = None

    model_config = {"extra": "allow"}
