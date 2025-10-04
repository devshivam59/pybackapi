# Trading Backend API

This project implements a FastAPI-based backend that models a retail trading platform with modules for authentication, instruments, market data, orders, portfolios, wallets, ledgers, reports, notifications, admin tools, and automation controls.

## Features

- JWT-based authentication with role claims (`admin`, `client`).
- Idempotency handling for orders and wallet operations via the `Idempotency-Key` header.
- Instrument import pipeline backed by SQLite with 100k+ row CSV ingestion, fuzzy search, and broker token mapping utilities.
- Watchlist management with shortcut order placement and live quotes streamed from Kite Connect when credentials are supplied.
- Order lifecycle management with modification and cancellation support.
- Portfolio summaries, trades history, wallet balance management, and ledger adjustments.
- Reporting endpoints for P&L, taxes, and exports.
- Notification broadcast and per-user inbox support.
- Admin APIs for users, orders, positions, and Zerodha token management.
- WebSocket endpoint for price subscriptions and system events.

## Getting Started

### Requirements

- Python 3.11+
- Poetry or pip for dependency management

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the API & UI

```bash
uvicorn app.main:app --reload
```

The API is served at `http://localhost:8000`. Interactive API docs are available at `/docs`.

A lightweight admin console for testing CSV uploads, fuzzy search, watchlists, and Kite connectivity is exposed at `http://localhost:8000/`. The console serves static assets from the `frontend/` directory and communicates with the `/v1` API surface.

#### Demo credentials

- Email: `admin@example.com`
- Password: `admin123`

The demo admin is provisioned on startup and has full privileges for importing/purging instrument data, managing watchlists, and updating Kite tokens.

#### Kite Connect integration

- Navigate to the "Configure Kite Credentials" card in the console to store your Kite API key and the daily access token. Credentials are kept in-memory for the running process only.
- Use the "Test Connectivity" action to verify the credentials. The backend hits `/v1/admin/brokers/zerodha/test`, which in turn pings the Kite REST API.
- The same card exposes a "Clear" action to wipe the stored credentials when rotating tokens.

### Instrument imports & watchlists

- CSV uploads must include the following headers: `instrument_token`, `exchange_token`, `tradingsymbol`, `name`, `last_price`, `expiry`, `strike`, `tick_size`, `lot_size`, `instrument_type`, `segment`, `exchange`.
- Use the `replace_existing` toggle to clear the existing catalog before loading a fresh dump.
- Imports are tracked in the `instrument_imports` table and surfaced via `GET /v1/instruments/imports` and the UI.
- Watchlists can be created from the UI once logged in. Use the search table's "Add" buttons to populate a watchlist and the watchlist table's "Remove" buttons to prune entries.
- When Kite credentials are configured, `/v1/watchlists/{watchlist_id}/items` and `/v1/market/quotes` will enrich instruments with live LTP sourced from Kite. Without credentials, the endpoints fall back to the last imported price.

### Running Tests

This scaffold does not include automated tests yet. You can exercise the API using the interactive docs or HTTP clients such as `curl` or Postman.
