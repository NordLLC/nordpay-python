# NordPay Python SDK

Official Python SDK for the [NordPay API](https://nord-3.gitbook.io/nord-api) — accept crypto payments with a few lines of code.

## Features

- **Sync & Async** — `NordPay` (sync) and `AsyncNordPay` (async) with identical API
- **Full type hints** — autocomplete everywhere, `py.typed` (PEP 561)
- **Pydantic v2 models** — validated responses, `Decimal` precision for money
- **Typed exceptions** — specific error class for every HTTP status
- **Automatic retries** — exponential backoff on 429/5xx (configurable)
- **Webhook verification** — validate postback signatures with constant-time comparison
- **Zero config** — just pass your API key

## Installation

```bash
pip install nordpay
```

## Quick Start

```python
from nordpay import NordPay

with NordPay("your-api-key") as client:
    # Create a $100 invoice
    invoice = client.invoices.create(
        amount="100 USD",
        label="Order #123",
        expires_time=60,  # minutes
        allowed_currencies=["BTC", "USDTERC20", "USDTTRC20"],
    )
    print(f"Payment link: {invoice.url}")
    print(f"Status: {invoice.status}")
```

### Async

```python
import asyncio
from nordpay import AsyncNordPay

async def main():
    async with AsyncNordPay("your-api-key") as client:
        invoice = await client.invoices.create(
            amount="50 USD",
            label="Subscription",
            expires_time=30,
            allowed_currencies=["BTC", "USDTERC20", "USDTTRC20"],
        )
        print(invoice.url)

asyncio.run(main())
```

## API Reference

### Currencies (public, no auth)

```python
client = NordPay()  # no API key needed

currencies = client.currencies.list()   # each Currency carries its own `.rate`
rates = client.currencies.rates()        # convenience view derived from list()
fiats = client.fiat_currencies.list()
fiat_rates = client.fiat_currencies.rates()
```

### Invoices

```python
# Create
invoice = client.invoices.create(
    amount="100 USD",           # or "0.5 BTC"
    label="Order #123",
    expires_time=60,            # minutes (30-1440)
    currency="USDTERC20",       # lock to specific crypto (or use allowed_currencies)
    postback_url="https://...", # optional: webhook URL
    success_url="https://...",  # optional: redirect on success
    fail_url="https://...",     # optional: redirect on failure
    allowed_currencies=["BTC", "USDTERC20", "USDTTRC20"],  # min 2 currencies
)

# List / Get
invoices = client.invoices.list()   # paginates over all invoices
inv = client.invoices.get("uuid-or-id")
print(inv.status, inv.tx_hash, inv.explorer_url)  # tx_hash / explorer_url populate once paid

# Paginated list with filters
page = client.invoices.list_paginated(
    status="paid", currency=["BTC", "USDTBEP20"],
    sort="created_at:desc", limit=50,
)

# Auto-paginate (iterate all pages automatically)
for inv in client.invoices.auto_paginate(status="paid"):
    print(inv.uuid, inv.amount_usd)

# Summary statistics
summary = client.invoices.summary()
print(
    f"Total: {summary.total_count}, Paid: {summary.paid_count}, "
    f"Pending: {summary.pending_count}, Cancelled: {summary.cancelled_count}, "
    f"Partially paid: {summary.partially_paid_count}"
)

# Transactions
txs = client.invoices.transactions()                    # all invoices
txs = client.invoices.transactions("uuid-or-id")        # specific

# Postback logs & retry
logs = client.invoices.postback_logs(invoice_id=131)
client.invoices.retry_postback(invoice_id=131, log_id=1)
```

### Wallets

```python
wallet = client.wallets.create(currency="BTC", label="Store Wallet")
wallets = client.wallets.list()
wallet = client.wallets.get(wallet_id=42)
qr = client.wallets.qrcode(wallet_id=42)  # base64
txs = client.wallets.transactions(wallet_id=42)

# Paginated list
page = client.wallets.list_paginated(currency="USDTBEP20", status="active")

# Wallet creation limits
limits = client.wallets.limits()
print(f"Available: {limits.available}/{limits.total}")

# Postback logs
logs = client.wallets.postback_logs(wallet_id=42)
```

### Balance

```python
balances = client.balance.get()
for b in balances:
    if float(b.amount) > 0:
        print(f"{b.currency}: {b.amount}")

# Withdrawal history (paginated)
history = client.balance.withdraw_history(currency="USDTBEP20", limit=50)
for w in client.balance.auto_paginate_withdraws():
    print(f"{w.currency}: {w.amount} — {w.status}")

# Per-currency withdrawal limits
for lim in client.balance.withdraw_limits():
    print(f"{lim.currency}: min={lim.min_amount}, max={lim.max_amount}, fee={lim.fee_percent}%")
```

### Withdrawals

```python
from decimal import Decimal

# Step 1: Request
req = client.withdrawals.request(
    currency="USDTERC20",
    address="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD18",
    amount=Decimal("100.50"),
)
print(f"Fee: {req.service_fee} | Expires: {req.expires_at}")

# Step 2: Confirm
result = client.withdrawals.confirm(req.identifier)

# Batch withdrawal
batch = client.withdrawals.request_multiple(
    currency="USDTTRC20",
    recipients=[
        ("TAddress1...", Decimal("50.00")),
        ("TAddress2...", Decimal("75.00")),
    ],
)
result = client.withdrawals.confirm_multiple(batch.identifier)
```

## Webhook Verification

NordPay sends a `postback_secret` in webhook payloads. Verify it:

```python
from nordpay import verify_postback, WebhookVerificationError

# FastAPI
@app.post("/webhook")
async def handle(request: Request):
    body = await request.json()
    try:
        event = verify_postback(body, secret="your-postback-secret")
    except WebhookVerificationError:
        raise HTTPException(403)

    if event.postback_type == "transaction":
        print(f"Tx {event.tx_hash}: {event.amount} {event.currency}")
    return {"ok": True}
```

Or just a boolean check:

```python
from nordpay import is_valid_postback

if is_valid_postback(payload, secret="your-secret"):
    # process
    ...
```

## Error Handling

```python
from nordpay import NordPay, BadRequestError, AuthenticationError, RateLimitError

try:
    invoice = client.invoices.create(amount="100 USD", label="Test", expires_time=60)
except AuthenticationError:
    print("Invalid API key")
except BadRequestError as e:
    print(f"Bad request: {e.detail}")
    print(f"Response: {e.response_body}")  # full error body
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
```

### Exception Hierarchy

```
NordPayError                      # base
├── AuthenticationError           # 401
├── ForbiddenError                # 403
├── BadRequestError               # 400
├── NotFoundError                 # 404
├── RateLimitError                # 429 (+ retry_after)
├── ServerError                   # 5xx
└── WebhookVerificationError      # invalid postback
```

## Configuration

```python
client = NordPay(
    api_key="your-key",
    base_url="https://api.nord-pay.com",  # default
    timeout=30.0,                          # seconds
    max_retries=3,                         # retry on 429/5xx (0 to disable)
)
```

### Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("nordpay").setLevel(logging.DEBUG)
# Now you'll see all HTTP requests and retries
```

## Requirements

- Python 3.10+
- httpx >= 0.25
- pydantic >= 2.0

## License

MIT
