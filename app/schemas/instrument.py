from pydantic import BaseModel
from typing import Optional

class InstrumentBase(BaseModel):
    instrument_token: int
    exchange_token: Optional[str] = None
    tradingsymbol: str
    name: Optional[str] = None
    last_price: Optional[float] = None
    expiry: Optional[str] = None
    strike: Optional[float] = None
    tick_size: Optional[float] = None
    lot_size: Optional[int] = None
    instrument_type: Optional[str] = None
    segment: Optional[str] = None
    exchange: Optional[str] = None

class InstrumentCreate(InstrumentBase):
    pass

class Instrument(InstrumentBase):
    id: int

    class Config:
        from_attributes = True