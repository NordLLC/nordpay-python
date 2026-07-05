# Changelog

All notable changes to this project are documented here. This project adheres to
[Semantic Versioning](https://semver.org/).

## [1.3.0] — 2026-07-05

Alignment with the current NordPay merchant `/v1/` API. Verified against live
production responses (reads + invoice/wallet creation) and the API source for the
withdrawal endpoints. **No breaking changes** — all method signatures are unchanged.

### Added
- `Invoice.explorer_url` and `Invoice.tx_hash` — both are now returned by
  `GET /v1/invoice/{id}` and invoice lists (populated once a payment is on-chain).
- `CreatedInvoice.explorer_url` (via `Invoice`).
- `InvoiceSummary.cancelled_count` and `InvoiceSummary.partially_paid_count`
  (default `0` for forward-compatibility).
- `Transaction.explorer_url`.

### Changed
- `Transaction`: `network_fee`, `network_fee_usd`, `service_fee`, `service_fee_usd`,
  `tx_hash` and `is_postback_sent` are now optional — the API returns them nullable
  for pending/unmined transactions, which previously raised a validation error.

### Fixed
- `currencies.rates()` / `fiat_currencies.rates()` no longer call the removed
  `/rates` endpoints (which returned 404). They now derive the rates from
  `list()` — the API embeds `rate` in each currency.
- `invoices.list()` / `wallets.list()` no longer call the removed bare
  `GET /v1/invoice/` and `GET /v1/wallet/` endpoints (404). They now paginate over
  `/v1/invoice/list` and `/v1/wallet/list`. For large accounts prefer
  `auto_paginate()` (lazy) or `list_paginated()`.

## [1.2.0] — 2026-04-01

- Unified response envelope support, `error_type` on exceptions.
