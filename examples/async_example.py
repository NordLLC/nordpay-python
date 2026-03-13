"""Async usage example."""

import asyncio
from decimal import Decimal

from nordpay import AsyncNordPay, BadRequestError

API_KEY = "your-api-key-here"


async def main() -> None:
    async with AsyncNordPay(API_KEY) as client:
        # Create invoice with multiple allowed currencies
        invoice = await client.invoices.create(
            amount="250 USD",
            label="Premium plan",
            expires_time=30,
            allowed_currencies=["BTC", "USDTERC20", "USDTTRC20"],
        )
        print(f"Pay here: {invoice.url}")

        # Create wallet
        wallet = await client.wallets.create(
            currency="USDTERC20",
            label="Main USDT wallet",
        )
        print(f"Wallet: {wallet.address}")

        # Check balances
        balances = await client.balance.get()
        for b in balances:
            print(f"Balance: {b.currency} = {b.amount}")

        # Request withdrawal
        try:
            req = await client.withdrawals.request(
                currency="USDTTRC20",
                address="TYourAddress...",
                amount=Decimal("50.00"),
            )
            print(f"Withdraw requested: {req.identifier}, fee: {req.service_fee}")

            result = await client.withdrawals.confirm(req.identifier)
            print(f"Confirmed: {result.status}")
        except BadRequestError as e:
            print(f"Withdrawal error: {e.detail}")


if __name__ == "__main__":
    asyncio.run(main())
