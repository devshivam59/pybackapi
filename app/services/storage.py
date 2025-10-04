from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from app.models.common import (
    Instrument,
    InstrumentImport,
    InstrumentSource,
    LedgerEntry,
    Notification,
    Order,
    Position,
    Trade,
    Wallet,
    WalletTransaction,
    Watchlist,
    WatchlistItem,
)
from app.models.user import User


@dataclass
class InMemoryDB:
    users: Dict[str, User] = field(default_factory=dict)
    instruments: Dict[str, Instrument] = field(default_factory=dict)
    watchlists: Dict[str, Watchlist] = field(default_factory=dict)
    watchlist_items: Dict[str, WatchlistItem] = field(default_factory=dict)
    orders: Dict[str, Order] = field(default_factory=dict)
    trades: Dict[str, Trade] = field(default_factory=dict)
    positions: Dict[str, Position] = field(default_factory=dict)
    wallets: Dict[str, Wallet] = field(default_factory=dict)
    wallet_transactions: Dict[str, WalletTransaction] = field(default_factory=dict)
    ledger_entries: Dict[str, LedgerEntry] = field(default_factory=dict)
    notifications: Dict[str, Notification] = field(default_factory=dict)
    instrument_imports: Dict[str, InstrumentImport] = field(default_factory=dict)
    instrument_sources: Dict[str, InstrumentSource] = field(default_factory=dict)
    idempotency_keys: Dict[str, str] = field(default_factory=dict)
    kite_api_key: Optional[str] = None
    kite_access_token: Optional[str] = None
    kite_token_valid_till: Optional[datetime] = None
    kite_token_updated_at: Optional[datetime] = None
    kite_last_request_token: Optional[str] = None
    kite_request_token_at: Optional[datetime] = None

    def get_or_create_wallet(self, user_id: str) -> Wallet:
        wallet = self.wallets.get(user_id)
        if wallet is None:
            wallet = Wallet(user_id=user_id)
            self.wallets[user_id] = wallet
        return wallet

    def record_wallet_transaction(self, txn: WalletTransaction) -> None:
        self.wallet_transactions[txn.id] = txn
        wallet = self.get_or_create_wallet(txn.user_id)
        if txn.type == "credit":
            wallet.balance += txn.amount
        elif txn.type == "debit":
            wallet.balance -= txn.amount
        wallet.updated_at = datetime.utcnow()

    def add_ledger_entry(self, entry: LedgerEntry) -> None:
        self.ledger_entries[entry.id] = entry


_db: Optional[InMemoryDB] = None


def get_db() -> InMemoryDB:
    global _db
    if _db is None:
        _db = InMemoryDB()
    return _db
