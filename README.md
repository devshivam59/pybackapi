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
- Single-page admin dashboard with overview metrics, instrument tooling, Kite credential controls, and user management.
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
