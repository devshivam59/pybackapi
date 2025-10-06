from sqlalchemy import Column, Integer, String, Float, BigInteger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    instrument_token = Column(BigInteger, unique=True, index=True)
    exchange_token = Column(String)
    tradingsymbol = Column(String, index=True)
    name = Column(String, index=True)
    last_price = Column(Float)
    expiry = Column(String)
    strike = Column(Float)
    tick_size = Column(Float)
    lot_size = Column(Integer)
    instrument_type = Column(String)
    segment = Column(String)
    exchange = Column(String)