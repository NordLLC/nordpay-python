"""NordPay SDK — sync and async clients."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from decimal import Decimal
from typing import Any

from nordpay._http import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, MAX_RETRIES, AsyncTransport, SyncTransport
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
    PaginatedInvoices,
    PaginatedWallets,
    PaginatedWithdraws,
    PostbackLog,
    Transaction,
    Wallet,
    WalletLimits,
    WithdrawConfirmation,
    WithdrawHistory,
    WithdrawLimit,
    WithdrawRequest,
)


def _validate_invoice_params(
    amount: str,
    label: str,
    expires_time: int,
    allowed_currencies: list[str] | None,
) -> None:
    if not amount or not amount.strip():
        raise ValueError("amount must not be empty")
    if not label or not label.strip():
        raise ValueError("label must not be empty")
    if len(label) > 255:
        raise ValueError("label must be at most 255 characters")
    if not (30 <= expires_time <= 1440):
        raise ValueError("expires_time must be between 30 and 1440 minutes")
    if allowed_currencies is not None and len(allowed_currencies) < 2:
        raise ValueError("allowed_currencies must contain at least 2 currencies")


def _validate_wallet_params(label: str) -> None:
    if not label or not label.strip():
        raise ValueError("label must not be empty")
    if len(label) > 255:
        raise ValueError("label must be at most 255 characters")


def _date_params(start_date: datetime | None, end_date: datetime | None) -> dict[str, str]:
    params: dict[str, str] = {}
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()
    return params


def _paginated_params(
    *,
    q: str | None = None,
    currency: str | list[str] | None = None,
    status: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
    sort: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"offset": offset, "limit": limit}
    if q is not None:
        params["q"] = q
    if currency is not None:
        params["currency"] = currency if isinstance(currency, list) else [currency]
    if status is not None:
        params["status"] = status
    if start_date is not None:
        params["start_date"] = start_date.isoformat()
    if end_date is not None:
        params["end_date"] = end_date.isoformat()
    if sort is not None:
        params["sort"] = sort
    return params


# ---------------------------------------------------------------------------
# Synchronous client
# ---------------------------------------------------------------------------


class NordPay:
    """Synchronous NordPay API client.

    Usage::

        from nordpay import NordPay

        client = NordPay("your-api-key")

        # List currencies (no auth required)
        currencies = client.currencies.list()

        # Create an invoice
        invoice = client.invoices.create(
            amount="100 USD",
            label="Order #123",
            expires_time=60,
        )
        print(invoice.url)  # payment link

        client.close()

    Or as a context manager::

        with NordPay("your-api-key") as client:
            wallets = client.wallets.list()
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._transport = SyncTransport(api_key, base_url, timeout, max_retries)
        self.currencies = _SyncCurrencies(self._transport)
        self.fiat_currencies = _SyncFiatCurrencies(self._transport)
        self.invoices = _SyncInvoices(self._transport)
        self.wallets = _SyncWallets(self._transport)
        self.balance = _SyncBalance(self._transport)
        self.withdrawals = _SyncWithdrawals(self._transport)

    def close(self) -> None:
        """Close the underlying HTTP connection."""
        self._transport.close()

    def __enter__(self) -> NordPay:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


class AsyncNordPay:
    """Asynchronous NordPay API client.

    Usage::

        import asyncio
        from nordpay import AsyncNordPay

        async def main():
            async with AsyncNordPay("your-api-key") as client:
                currencies = await client.currencies.list()
                invoice = await client.invoices.create(
                    amount="100 USD",
                    label="Order #123",
                    expires_time=60,
                )
                print(invoice.url)

        asyncio.run(main())
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self._transport = AsyncTransport(api_key, base_url, timeout, max_retries)
        self.currencies = _AsyncCurrencies(self._transport)
        self.fiat_currencies = _AsyncFiatCurrencies(self._transport)
        self.invoices = _AsyncInvoices(self._transport)
        self.wallets = _AsyncWallets(self._transport)
        self.balance = _AsyncBalance(self._transport)
        self.withdrawals = _AsyncWithdrawals(self._transport)

    async def close(self) -> None:
        """Close the underlying HTTP connection."""
        await self._transport.close()

    async def __aenter__(self) -> AsyncNordPay:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


# ===================================================================
# Resource classes — Sync
# ===================================================================


class _SyncCurrencies:
    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(self) -> list[Currency]:
        """Get all supported cryptocurrencies."""
        data = self._t.request("GET", "/v1/currencies/")
        return [Currency.model_validate(item) for item in data]

    def rates(self) -> list[CurrencyRate]:
        """Get current exchange rates for all cryptocurrencies."""
        data = self._t.request("GET", "/v1/currencies/rates")
        return [CurrencyRate.model_validate(item) for item in data]


class _SyncFiatCurrencies:
    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(self) -> list[FiatCurrency]:
        """Get all supported fiat currencies."""
        data = self._t.request("GET", "/v1/fiat-currencies/")
        return [FiatCurrency.model_validate(item) for item in data]

    def rates(self) -> list[FiatCurrencyRate]:
        """Get current exchange rates for all fiat currencies."""
        data = self._t.request("GET", "/v1/fiat-currencies/rates")
        return [FiatCurrencyRate.model_validate(item) for item in data]


class _SyncInvoices:
    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(self) -> list[Invoice]:
        """Get all invoices."""
        data = self._t.request("GET", "/v1/invoice/")
        return [Invoice.model_validate(item) for item in data]

    def get(self, identifier: str | int) -> Invoice:
        """Get invoice by ID or UUID.

        Args:
            identifier: Invoice numeric ID or UUID string.
        """
        data = self._t.request("GET", f"/v1/invoice/{identifier}")
        return Invoice.model_validate(data)

    def create(
        self,
        *,
        amount: str,
        label: str,
        expires_time: int,
        currency: str | None = None,
        postback_url: str | None = None,
        success_url: str | None = None,
        fail_url: str | None = None,
        allowed_currencies: list[str] | None = None,
    ) -> CreatedInvoice:
        """Create a new invoice.

        Args:
            amount: Amount with currency, e.g. ``"100 USD"`` or ``"0.5 BTC"``.
            label: Label for the invoice (max 255 chars).
            expires_time: Expiration time in minutes (30-1440).
            currency: Lock to a specific cryptocurrency (optional).
            postback_url: URL for webhook notifications (optional).
            success_url: Redirect URL on successful payment (optional).
            fail_url: Redirect URL on failed/expired payment (optional).
            allowed_currencies: Allow only specific currencies (min 2, optional).

        Returns:
            Created invoice with payment URL.
        """
        _validate_invoice_params(amount, label, expires_time, allowed_currencies)
        body: dict[str, Any] = {
            "amount": amount,
            "label": label,
            "expires_time": expires_time,
        }
        if currency is not None:
            body["currency"] = currency
        if postback_url is not None:
            body["postback_url"] = postback_url
        if success_url is not None:
            body["success_url"] = success_url
        if fail_url is not None:
            body["fail_url"] = fail_url
        if allowed_currencies is not None:
            body["allowed_currencies"] = allowed_currencies

        data = self._t.request("POST", "/v1/invoice/create", json=body)
        return CreatedInvoice.model_validate(data)

    def transactions(
        self,
        identifier: str | int | None = None,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Transaction]:
        """Get transactions for an invoice or all invoices.

        Args:
            identifier: Invoice ID/UUID — if None, returns transactions for all invoices.
            start_date: Filter — start date (optional).
            end_date: Filter — end date (optional).
        """
        path = f"/v1/invoice/{identifier}/transactions" if identifier else "/v1/invoice/transactions"
        data = self._t.request("GET", path, params=_date_params(start_date, end_date))
        return [Transaction.model_validate(item) for item in data]

    def list_paginated(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str | None = None,
    ) -> PaginatedInvoices:
        """List invoices with pagination, filtering, and sorting.

        Args:
            q: Search query (label, UUID).
            currency: Filter by currency or list of currencies.
            status: Filter by status (pending, paid, expired).
            start_date: Filter — created after this date.
            end_date: Filter — created before this date.
            offset: Number of items to skip (default 0).
            limit: Max items to return (default 50, max 200).
            sort: Sort expression, e.g. ``"created_at:desc"``.
        """
        params = _paginated_params(
            q=q, currency=currency, status=status,
            start_date=start_date, end_date=end_date,
            offset=offset, limit=limit, sort=sort,
        )
        data = self._t.request("GET", "/v1/invoice/list", params=params)
        return PaginatedInvoices.model_validate(data)

    def auto_paginate(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
        sort: str | None = None,
    ) -> Iterator[Invoice]:
        """Iterate over all invoices, automatically fetching pages.

        Yields individual ``Invoice`` objects across all pages.
        """
        offset = 0
        while True:
            page = self.list_paginated(
                q=q, currency=currency, status=status,
                start_date=start_date, end_date=end_date,
                offset=offset, limit=limit, sort=sort,
            )
            yield from page.items
            offset += limit
            if offset >= page.total:
                break

    def summary(self) -> InvoiceSummary:
        """Get aggregated invoice statistics."""
        data = self._t.request("GET", "/v1/invoice/summary")
        return InvoiceSummary.model_validate(data)

    def postback_logs(self, identifier: int) -> list[PostbackLog]:
        """Get postback delivery logs for an invoice.

        Args:
            identifier: Invoice numeric ID.
        """
        data = self._t.request("GET", f"/v1/invoice/{identifier}/postback-logs")
        return [PostbackLog.model_validate(item) for item in data]

    def retry_postback(self, identifier: int, log_id: int) -> PostbackLog:
        """Retry a failed postback delivery.

        Args:
            identifier: Invoice numeric ID.
            log_id: Postback log entry ID.
        """
        data = self._t.request("POST", f"/v1/invoice/{identifier}/postback-logs/{log_id}/retry")
        return PostbackLog.model_validate(data)


class _SyncWallets:
    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def list(self) -> list[Wallet]:
        """Get all wallets."""
        data = self._t.request("GET", "/v1/wallet/")
        return [Wallet.model_validate(item) for item in data]

    def get(self, wallet_id: int) -> Wallet:
        """Get wallet by ID."""
        data = self._t.request("GET", f"/v1/wallet/{wallet_id}")
        return Wallet.model_validate(data)

    def create(
        self,
        *,
        currency: str,
        label: str,
        postback_url: str | None = None,
    ) -> Wallet:
        """Create a new wallet.

        Args:
            currency: Cryptocurrency name (e.g. ``"BTC"``, ``"USDTERC20"``).
            label: Label for the wallet (max 255 chars).
            postback_url: URL for webhook notifications (optional).
        """
        _validate_wallet_params(label)
        body: dict[str, Any] = {"currency": currency, "label": label}
        if postback_url is not None:
            body["postback_url"] = postback_url
        data = self._t.request("POST", "/v1/wallet/create", json=body)
        return Wallet.model_validate(data)

    def qrcode(self, wallet_id: int) -> str:
        """Get wallet QR code as base64-encoded image.

        Args:
            wallet_id: Wallet ID.

        Returns:
            Base64 string of the QR code image.
        """
        data = self._t.request("GET", f"/v1/wallet/{wallet_id}/qrcode")
        return data["qrcode"]

    def transactions(
        self,
        wallet_id: int | None = None,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Transaction]:
        """Get transactions for a wallet or all wallets.

        Args:
            wallet_id: Wallet ID — if None, returns transactions for all wallets.
            start_date: Filter — start date (optional).
            end_date: Filter — end date (optional).
        """
        path = f"/v1/wallet/{wallet_id}/transactions" if wallet_id else "/v1/wallet/transactions"
        data = self._t.request("GET", path, params=_date_params(start_date, end_date))
        return [Transaction.model_validate(item) for item in data]

    def list_paginated(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str | None = None,
    ) -> PaginatedWallets:
        """List wallets with pagination, filtering, and sorting.

        Args:
            q: Search query (label, address).
            currency: Filter by currency or list of currencies.
            status: Filter by status (active, expired).
            offset: Number of items to skip (default 0).
            limit: Max items to return (default 50, max 200).
            sort: Sort expression, e.g. ``"created_at:desc"``.
        """
        params = _paginated_params(
            q=q, currency=currency, status=status,
            offset=offset, limit=limit, sort=sort,
        )
        data = self._t.request("GET", "/v1/wallet/list", params=params)
        return PaginatedWallets.model_validate(data)

    def auto_paginate(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        limit: int = 50,
        sort: str | None = None,
    ) -> Iterator[Wallet]:
        """Iterate over all wallets, automatically fetching pages."""
        offset = 0
        while True:
            page = self.list_paginated(
                q=q, currency=currency, status=status,
                offset=offset, limit=limit, sort=sort,
            )
            yield from page.items
            offset += limit
            if offset >= page.total:
                break

    def limits(self) -> WalletLimits:
        """Get wallet creation limits for the current account."""
        data = self._t.request("GET", "/v1/wallet/limits")
        return WalletLimits.model_validate(data)

    def postback_logs(self, wallet_id: int) -> list[PostbackLog]:
        """Get postback delivery logs for a wallet.

        Args:
            wallet_id: Wallet ID.
        """
        data = self._t.request("GET", f"/v1/wallet/{wallet_id}/postback-logs")
        return [PostbackLog.model_validate(item) for item in data]

    def retry_postback(self, wallet_id: int, log_id: int) -> PostbackLog:
        """Retry a failed postback delivery.

        Args:
            wallet_id: Wallet ID.
            log_id: Postback log entry ID.
        """
        data = self._t.request("POST", f"/v1/wallet/{wallet_id}/postback-logs/{log_id}/retry")
        return PostbackLog.model_validate(data)


class _SyncBalance:
    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def get(self) -> list[Balance]:
        """Get all currency balances."""
        data = self._t.request("GET", "/v1/balance/")
        if isinstance(data, list):
            return [Balance.model_validate(item) for item in data]
        # API returns flat dict: {"BTC": "0.05", "ETH": "1.25", ...}
        if isinstance(data, dict):
            return [
                Balance(currency=k, amount=Decimal(str(v)), amount_usd=Decimal("0"))
                for k, v in data.items()
            ]
        return []

    def withdraw_history(
        self,
        *,
        currency: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str | None = None,
    ) -> PaginatedWithdraws:
        """Get paginated withdrawal history.

        Args:
            currency: Filter by currency.
            status: Filter by status.
            offset: Number of items to skip (default 0).
            limit: Max items to return (default 50, max 200).
            sort: Sort expression, e.g. ``"created_at:desc"``.
        """
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if currency is not None:
            params["currency"] = currency
        if status is not None:
            params["status"] = status
        if sort is not None:
            params["sort"] = sort
        data = self._t.request("GET", "/v1/balance/withdraws", params=params)
        return PaginatedWithdraws.model_validate(data)

    def auto_paginate_withdraws(
        self,
        *,
        currency: str | None = None,
        status: str | None = None,
        limit: int = 50,
        sort: str | None = None,
    ) -> Iterator[WithdrawHistory]:
        """Iterate over all withdrawals, automatically fetching pages."""
        offset = 0
        while True:
            page = self.withdraw_history(
                currency=currency, status=status,
                offset=offset, limit=limit, sort=sort,
            )
            yield from page.items
            offset += limit
            if offset >= page.total:
                break

    def withdraw_limits(self) -> list[WithdrawLimit]:
        """Get per-currency withdrawal limits."""
        data = self._t.request("GET", "/v1/balance/withdraw/limits")
        return [WithdrawLimit.model_validate(item) for item in data]


class _SyncWithdrawals:
    def __init__(self, transport: SyncTransport) -> None:
        self._t = transport

    def request(
        self,
        *,
        currency: str,
        address: str,
        amount: Decimal | str,
    ) -> WithdrawRequest:
        """Request a withdrawal.

        Args:
            currency: Cryptocurrency to withdraw.
            address: Destination wallet address.
            amount: Amount to withdraw.

        Returns:
            Withdraw request with identifier (must be confirmed).
        """
        body = {"currency": currency, "address": address, "amount": str(amount)}
        data = self._t.request("POST", "/v1/balance/withdraw/request", json=body)
        return WithdrawRequest.model_validate(data)

    def confirm(self, identifier: str) -> WithdrawConfirmation:
        """Confirm a pending withdrawal.

        Args:
            identifier: Identifier from :meth:`request`.
        """
        data = self._t.request("POST", "/v1/balance/withdraw/confirm", json={"identifier": identifier})
        return WithdrawConfirmation.model_validate(data)

    def request_multiple(
        self,
        *,
        currency: str,
        recipients: list[tuple[str, Decimal | str]],
    ) -> MultipleWithdrawRequest:
        """Request a batch withdrawal to multiple addresses.

        Args:
            currency: Cryptocurrency to withdraw.
            recipients: List of ``(address, amount)`` tuples.

        Returns:
            Multiple withdraw request with identifier (must be confirmed).
        """
        body = {
            "currency": currency,
            "addresses_and_amounts": [[addr, str(amt)] for addr, amt in recipients],
        }
        data = self._t.request("POST", "/v1/balance/withdraw/multiple/request", json=body)
        return MultipleWithdrawRequest.model_validate(data)

    def confirm_multiple(self, identifier: str) -> WithdrawConfirmation:
        """Confirm a pending batch withdrawal.

        Args:
            identifier: Identifier from :meth:`request_multiple`.
        """
        data = self._t.request("POST", "/v1/balance/withdraw/multiple/confirm", json={"identifier": identifier})
        return WithdrawConfirmation.model_validate(data)


# ===================================================================
# Resource classes — Async
# ===================================================================


class _AsyncCurrencies:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(self) -> list[Currency]:
        """Get all supported cryptocurrencies."""
        data = await self._t.request("GET", "/v1/currencies/")
        return [Currency.model_validate(item) for item in data]

    async def rates(self) -> list[CurrencyRate]:
        """Get current exchange rates for all cryptocurrencies."""
        data = await self._t.request("GET", "/v1/currencies/rates")
        return [CurrencyRate.model_validate(item) for item in data]


class _AsyncFiatCurrencies:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(self) -> list[FiatCurrency]:
        """Get all supported fiat currencies."""
        data = await self._t.request("GET", "/v1/fiat-currencies/")
        return [FiatCurrency.model_validate(item) for item in data]

    async def rates(self) -> list[FiatCurrencyRate]:
        """Get current exchange rates for all fiat currencies."""
        data = await self._t.request("GET", "/v1/fiat-currencies/rates")
        return [FiatCurrencyRate.model_validate(item) for item in data]


class _AsyncInvoices:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(self) -> list[Invoice]:
        """Get all invoices."""
        data = await self._t.request("GET", "/v1/invoice/")
        return [Invoice.model_validate(item) for item in data]

    async def get(self, identifier: str | int) -> Invoice:
        """Get invoice by ID or UUID."""
        data = await self._t.request("GET", f"/v1/invoice/{identifier}")
        return Invoice.model_validate(data)

    async def create(
        self,
        *,
        amount: str,
        label: str,
        expires_time: int,
        currency: str | None = None,
        postback_url: str | None = None,
        success_url: str | None = None,
        fail_url: str | None = None,
        allowed_currencies: list[str] | None = None,
    ) -> CreatedInvoice:
        """Create a new invoice.

        Args:
            amount: Amount with currency, e.g. ``"100 USD"`` or ``"0.5 BTC"``.
            label: Label for the invoice (max 255 chars).
            expires_time: Expiration time in minutes (30-1440).
            currency: Lock to a specific cryptocurrency (optional).
            postback_url: URL for webhook notifications (optional).
            success_url: Redirect URL on successful payment (optional).
            fail_url: Redirect URL on failed/expired payment (optional).
            allowed_currencies: Allow only specific currencies (min 2, optional).

        Returns:
            Created invoice with payment URL.
        """
        _validate_invoice_params(amount, label, expires_time, allowed_currencies)
        body: dict[str, Any] = {
            "amount": amount,
            "label": label,
            "expires_time": expires_time,
        }
        if currency is not None:
            body["currency"] = currency
        if postback_url is not None:
            body["postback_url"] = postback_url
        if success_url is not None:
            body["success_url"] = success_url
        if fail_url is not None:
            body["fail_url"] = fail_url
        if allowed_currencies is not None:
            body["allowed_currencies"] = allowed_currencies

        data = await self._t.request("POST", "/v1/invoice/create", json=body)
        return CreatedInvoice.model_validate(data)

    async def transactions(
        self,
        identifier: str | int | None = None,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Transaction]:
        """Get transactions for an invoice or all invoices."""
        path = f"/v1/invoice/{identifier}/transactions" if identifier else "/v1/invoice/transactions"
        data = await self._t.request("GET", path, params=_date_params(start_date, end_date))
        return [Transaction.model_validate(item) for item in data]

    async def list_paginated(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str | None = None,
    ) -> PaginatedInvoices:
        """List invoices with pagination, filtering, and sorting."""
        params = _paginated_params(
            q=q, currency=currency, status=status,
            start_date=start_date, end_date=end_date,
            offset=offset, limit=limit, sort=sort,
        )
        data = await self._t.request("GET", "/v1/invoice/list", params=params)
        return PaginatedInvoices.model_validate(data)

    async def auto_paginate(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
        sort: str | None = None,
    ) -> AsyncIterator[Invoice]:
        """Iterate over all invoices, automatically fetching pages."""
        offset = 0
        while True:
            page = await self.list_paginated(
                q=q, currency=currency, status=status,
                start_date=start_date, end_date=end_date,
                offset=offset, limit=limit, sort=sort,
            )
            for item in page.items:
                yield item
            offset += limit
            if offset >= page.total:
                break

    async def summary(self) -> InvoiceSummary:
        """Get aggregated invoice statistics."""
        data = await self._t.request("GET", "/v1/invoice/summary")
        return InvoiceSummary.model_validate(data)

    async def postback_logs(self, identifier: int) -> list[PostbackLog]:
        """Get postback delivery logs for an invoice."""
        data = await self._t.request("GET", f"/v1/invoice/{identifier}/postback-logs")
        return [PostbackLog.model_validate(item) for item in data]

    async def retry_postback(self, identifier: int, log_id: int) -> PostbackLog:
        """Retry a failed postback delivery."""
        data = await self._t.request("POST", f"/v1/invoice/{identifier}/postback-logs/{log_id}/retry")
        return PostbackLog.model_validate(data)


class _AsyncWallets:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def list(self) -> list[Wallet]:
        """Get all wallets."""
        data = await self._t.request("GET", "/v1/wallet/")
        return [Wallet.model_validate(item) for item in data]

    async def get(self, wallet_id: int) -> Wallet:
        """Get wallet by ID."""
        data = await self._t.request("GET", f"/v1/wallet/{wallet_id}")
        return Wallet.model_validate(data)

    async def create(
        self,
        *,
        currency: str,
        label: str,
        postback_url: str | None = None,
    ) -> Wallet:
        """Create a new wallet."""
        _validate_wallet_params(label)
        body: dict[str, Any] = {"currency": currency, "label": label}
        if postback_url is not None:
            body["postback_url"] = postback_url
        data = await self._t.request("POST", "/v1/wallet/create", json=body)
        return Wallet.model_validate(data)

    async def qrcode(self, wallet_id: int) -> str:
        """Get wallet QR code as base64-encoded image."""
        data = await self._t.request("GET", f"/v1/wallet/{wallet_id}/qrcode")
        return data["qrcode"]

    async def transactions(
        self,
        wallet_id: int | None = None,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Transaction]:
        """Get transactions for a wallet or all wallets."""
        path = f"/v1/wallet/{wallet_id}/transactions" if wallet_id else "/v1/wallet/transactions"
        data = await self._t.request("GET", path, params=_date_params(start_date, end_date))
        return [Transaction.model_validate(item) for item in data]

    async def list_paginated(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str | None = None,
    ) -> PaginatedWallets:
        """List wallets with pagination, filtering, and sorting."""
        params = _paginated_params(
            q=q, currency=currency, status=status,
            offset=offset, limit=limit, sort=sort,
        )
        data = await self._t.request("GET", "/v1/wallet/list", params=params)
        return PaginatedWallets.model_validate(data)

    async def auto_paginate(
        self,
        *,
        q: str | None = None,
        currency: str | list[str] | None = None,
        status: str | None = None,
        limit: int = 50,
        sort: str | None = None,
    ) -> AsyncIterator[Wallet]:
        """Iterate over all wallets, automatically fetching pages."""
        offset = 0
        while True:
            page = await self.list_paginated(
                q=q, currency=currency, status=status,
                offset=offset, limit=limit, sort=sort,
            )
            for item in page.items:
                yield item
            offset += limit
            if offset >= page.total:
                break

    async def limits(self) -> WalletLimits:
        """Get wallet creation limits for the current account."""
        data = await self._t.request("GET", "/v1/wallet/limits")
        return WalletLimits.model_validate(data)

    async def postback_logs(self, wallet_id: int) -> list[PostbackLog]:
        """Get postback delivery logs for a wallet."""
        data = await self._t.request("GET", f"/v1/wallet/{wallet_id}/postback-logs")
        return [PostbackLog.model_validate(item) for item in data]

    async def retry_postback(self, wallet_id: int, log_id: int) -> PostbackLog:
        """Retry a failed postback delivery."""
        data = await self._t.request("POST", f"/v1/wallet/{wallet_id}/postback-logs/{log_id}/retry")
        return PostbackLog.model_validate(data)


class _AsyncBalance:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def get(self) -> list[Balance]:
        """Get all currency balances."""
        data = await self._t.request("GET", "/v1/balance/")
        if isinstance(data, list):
            return [Balance.model_validate(item) for item in data]
        # API returns flat dict: {"BTC": "0.05", "ETH": "1.25", ...}
        if isinstance(data, dict):
            return [
                Balance(currency=k, amount=Decimal(str(v)), amount_usd=Decimal("0"))
                for k, v in data.items()
            ]
        return []

    async def withdraw_history(
        self,
        *,
        currency: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort: str | None = None,
    ) -> PaginatedWithdraws:
        """Get paginated withdrawal history."""
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if currency is not None:
            params["currency"] = currency
        if status is not None:
            params["status"] = status
        if sort is not None:
            params["sort"] = sort
        data = await self._t.request("GET", "/v1/balance/withdraws", params=params)
        return PaginatedWithdraws.model_validate(data)

    async def auto_paginate_withdraws(
        self,
        *,
        currency: str | None = None,
        status: str | None = None,
        limit: int = 50,
        sort: str | None = None,
    ) -> AsyncIterator[WithdrawHistory]:
        """Iterate over all withdrawals, automatically fetching pages."""
        offset = 0
        while True:
            page = await self.withdraw_history(
                currency=currency, status=status,
                offset=offset, limit=limit, sort=sort,
            )
            for item in page.items:
                yield item
            offset += limit
            if offset >= page.total:
                break

    async def withdraw_limits(self) -> list[WithdrawLimit]:
        """Get per-currency withdrawal limits."""
        data = await self._t.request("GET", "/v1/balance/withdraw/limits")
        return [WithdrawLimit.model_validate(item) for item in data]


class _AsyncWithdrawals:
    def __init__(self, transport: AsyncTransport) -> None:
        self._t = transport

    async def request(
        self,
        *,
        currency: str,
        address: str,
        amount: Decimal | str,
    ) -> WithdrawRequest:
        """Request a withdrawal."""
        body = {"currency": currency, "address": address, "amount": str(amount)}
        data = await self._t.request("POST", "/v1/balance/withdraw/request", json=body)
        return WithdrawRequest.model_validate(data)

    async def confirm(self, identifier: str) -> WithdrawConfirmation:
        """Confirm a pending withdrawal."""
        data = await self._t.request("POST", "/v1/balance/withdraw/confirm", json={"identifier": identifier})
        return WithdrawConfirmation.model_validate(data)

    async def request_multiple(
        self,
        *,
        currency: str,
        recipients: list[tuple[str, Decimal | str]],
    ) -> MultipleWithdrawRequest:
        """Request a batch withdrawal to multiple addresses."""
        body = {
            "currency": currency,
            "addresses_and_amounts": [[addr, str(amt)] for addr, amt in recipients],
        }
        data = await self._t.request("POST", "/v1/balance/withdraw/multiple/request", json=body)
        return MultipleWithdrawRequest.model_validate(data)

    async def confirm_multiple(self, identifier: str) -> WithdrawConfirmation:
        """Confirm a pending batch withdrawal."""
        data = await self._t.request(
            "POST", "/v1/balance/withdraw/multiple/confirm", json={"identifier": identifier}
        )
        return WithdrawConfirmation.model_validate(data)
