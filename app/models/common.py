from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Instrument(BaseModel):
    id: str = Field(default_factory=lambda: f"ins_{uuid4().hex}")
    instrument_token: str
    exchange_token: str
    tradingsymbol: str
    name: Optional[str] = None
    last_price: float = 0.0
    expiry: Optional[str] = None
    strike: Optional[float] = None
    tick_size: float = 0.0
    lot_size: int = 0
    instrument_type: str
    segment: str
    exchange: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class Watchlist(BaseModel):
    id: str = Field(default_factory=lambda: f"wl_{uuid4().hex}")
    user_id: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WatchlistItem(BaseModel):
    id: str = Field(default_factory=lambda: f"wli_{uuid4().hex}")
    watchlist_id: str
    instrument_id: str
    sort_order: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Order(BaseModel):
    id: str = Field(default_factory=lambda: f"ord_{uuid4().hex}")
    user_id: str
    instrument_id: str
    side: str
    qty: int
    order_type: str
    product: str
    validity: str
    price: Optional[float] = None
    trigger: Optional[float] = None
    status: str = "PENDING"
    placed_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    idempotency_key: Optional[str] = None


class Trade(BaseModel):
    id: str = Field(default_factory=lambda: f"trd_{uuid4().hex}")
    order_id: str
    user_id: str
    instrument_id: str
    qty: int
    price: float
    ts: datetime = Field(default_factory=datetime.utcnow)


class Position(BaseModel):
    id: str = Field(default_factory=lambda: f"pos_{uuid4().hex}")
    user_id: str
    instrument_id: str
    side: str
    qty: int
    avg_price: float
    realized_pnl: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    as_of_date: datetime = Field(default_factory=datetime.utcnow)
    source: str = "system"


class Wallet(BaseModel):
    user_id: str
    balance: float = 0.0
    margin: float = 0.0
    collateral: float = 0.0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WalletTransaction(BaseModel):
    id: str = Field(default_factory=lambda: f"wtx_{uuid4().hex}")
    user_id: str
    type: str
    amount: float
    note: Optional[str] = None
    ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LedgerEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"ldg_{uuid4().hex}")
    user_id: str
    date: datetime
    ref: Optional[str] = None
    type: str
    debit: float = 0.0
    credit: float = 0.0
    balance: float = 0.0
    note: Optional[str] = None


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: f"ntf_{uuid4().hex}")
    user_id: Optional[str]
    title: str
    body: str
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InstrumentImport(BaseModel):
    id: str = Field(default_factory=lambda: f"imp_{uuid4().hex}")
    source: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    rows_in: int = 0
    rows_ok: int = 0
    rows_err: int = 0
    status: str = "pending"
    errors: List[str] = Field(default_factory=list)
    log_url: Optional[str] = None


class InstrumentSource(BaseModel):
    id: str = Field(default_factory=lambda: f"src_{uuid4().hex}")
    name: str
    type: str
    config: dict = Field(default_factory=dict)
    schedule_cron: Optional[str] = None
    enabled: bool = True
    last_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
