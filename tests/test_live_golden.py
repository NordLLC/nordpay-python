"""Parse real captured prod /v1 responses with SDK models under extra='forbid'.

Fixtures in tests/fixtures/live/ are unwrapped `data` payloads captured from the
live merchant API on 2026-07-05. extra='forbid' turns any new API field the model
doesn't declare into a hard failure — that is exactly the drift we want to catch.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from nordpay.models import (
    CreatedInvoice,
    Currency,
    FiatCurrency,
    Invoice,
    InvoiceSummary,
    PaginatedInvoices,
    PaginatedWallets,
    PaginatedWithdraws,
    Wallet,
    WalletLimits,
    WithdrawHistory,
    WithdrawLimit,
)

FIX = pathlib.Path(__file__).parent / "fixtures" / "live"


def _strict(model):
    return type(f"Strict{model.__name__}", (model,), {"model_config": {"extra": "forbid"}})


# fixture name -> (model, is_list)
FLAT = {
    "currencies_list": (Currency, True),
    "fiat_list": (FiatCurrency, True),
    "balance_withdraw_limits": (WithdrawLimit, True),
    "invoices_get": (Invoice, False),
    "invoices_create": (CreatedInvoice, False),
    "invoices_summary": (InvoiceSummary, False),
    "wallets_get": (Wallet, False),
    "wallets_create": (Wallet, False),
    "wallets_limits": (WalletLimits, False),
}

# paginated fixture -> (container_model, item_model)
PAGINATED = {
    "invoices_list_paginated": (PaginatedInvoices, Invoice),
    "wallets_list_paginated": (PaginatedWallets, Wallet),
    "balance_withdraws": (PaginatedWithdraws, WithdrawHistory),
}


def _load(name):
    f = FIX / f"{name}.json"
    if not f.exists():
        pytest.skip(f"no fixture {name}")
    return json.loads(f.read_text())


@pytest.mark.parametrize("name,spec", FLAT.items())
def test_flat_parses_strict(name, spec):
    model, is_list = spec
    data = _load(name)
    strict = _strict(model)
    items = data if is_list else [data]
    assert items, f"{name}: empty sample"
    for item in items[:10]:
        strict.model_validate(item)


@pytest.mark.parametrize("name,spec", PAGINATED.items())
def test_paginated_parses_strict(name, spec):
    container, item_model = spec
    data = _load(name)
    _strict(container).model_validate(data)  # container envelope shape
    strict_item = _strict(item_model)
    for item in data.get("items", [])[:10]:
        strict_item.model_validate(item)


def test_balance_get_shape():
    data = _load("balance_get")
    assert isinstance(data, dict)
    assert "balances" in data
    assert all(isinstance(v, str) for v in data["balances"].values())


def test_qrcode_shape():
    data = _load("wallets_qrcode")
    assert isinstance(data.get("qrcode"), str) and data["qrcode"]
