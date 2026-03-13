"""Basic usage example — synchronous client."""

from nordpay import NordPay

API_KEY = "your-api-key-here"


def main() -> None:
    with NordPay(API_KEY) as client:
        # 1. Public: get available currencies (no auth)
        currencies = client.currencies.list()
        print(f"Available currencies: {len(currencies)}")
        for c in currencies[:5]:
            print(f"  {c.name} ({c.network}) — rate: ${c.rate}, fee: {c.network_fee}")

        # 2. Create an invoice
        invoice = client.invoices.create(
            amount="100 USD",
            label="Order #12345",
            expires_time=60,
        )
        print(f"\nInvoice created:")
        print(f"  UUID: {invoice.uuid}")
        print(f"  Amount: ${invoice.amount_usd}")
        print(f"  Payment link: {invoice.url}")
        print(f"  Expires: {invoice.expires_at}")

        # 3. Check balances
        balances = client.balance.get()
        print(f"\nBalances:")
        for b in balances:
            print(f"  {b.currency}: {b.amount} (${b.amount_usd})")

        # 4. List wallets
        wallets = client.wallets.list()
        print(f"\nWallets: {len(wallets)}")
        for w in wallets[:3]:
            print(f"  [{w.id}] {w.currency} — {w.address[:20]}...")


if __name__ == "__main__":
    main()
