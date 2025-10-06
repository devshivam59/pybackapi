import io
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, engine
from app.models.instrument import Instrument
import os
import json
from fastapi import WebSocket, WebSocketDisconnect
from kiteconnect import KiteTicker
from app.schemas.instrument import Instrument as InstrumentSchema, InstrumentCreate
from app.websocket_manager import manager

router = APIRouter()


@router.get("/search", response_model=List[InstrumentSchema])
def search_instruments(
    q: str = Query(..., min_length=2, description="Search query for instruments"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Performs a fuzzy search for instruments by name or tradingsymbol.
    Requires the pg_trgm extension to be enabled in PostgreSQL.
    """
    # Using word similarity operator %%
    # The GIN index on (name, tradingsymbol) should be used if created.
    # We can also use the similarity function and the <-> operator for distance.
    query = text("""
        SELECT * FROM instruments
        WHERE name %% :q OR tradingsymbol %% :q
        ORDER BY similarity(name, :q) DESC, similarity(tradingsymbol, :q) DESC
        LIMIT :limit
    """)

    results = db.execute(query, {"q": q, "limit": limit}).fetchall()

    if not results:
        return []

    return results


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads a CSV file with instrument data and saves it to the database.
    Handles large files efficiently using PostgreSQL's COPY command.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a CSV file.")

    conn = None
    cursor = None
    try:
        contents = await file.read()
        csv_file = io.StringIO(contents.decode('utf-8'))

        conn = engine.raw_connection()
        cursor = conn.cursor()

        sql_copy = f"""
            COPY {Instrument.__tablename__} (
                instrument_token, exchange_token, tradingsymbol, name,
                last_price, expiry, strike, tick_size, lot_size,
                instrument_type, segment, exchange
            ) FROM STDIN WITH (FORMAT CSV, HEADER)
        """

        cursor.copy_expert(sql=sql_copy, file=csv_file)
        conn.commit()

        return {"message": "CSV file uploaded and data ingested successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred during data ingestion: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@router.post("/", response_model=InstrumentSchema)
def create_instrument(instrument: InstrumentCreate, db: Session = Depends(get_db)):
    db_instrument = Instrument(**instrument.model_dump())
    db.add(db_instrument)
    db.commit()
    db.refresh(db_instrument)
    return db_instrument

@router.get("/", response_model=List[InstrumentSchema])
def read_instruments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    instruments = db.query(Instrument).offset(skip).limit(limit).all()
    return instruments

@router.get("/{instrument_id}", response_model=InstrumentSchema)
def read_instrument(instrument_id: int, db: Session = Depends(get_db)):
    db_instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if db_instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return db_instrument

@router.put("/{instrument_id}", response_model=InstrumentSchema)
def update_instrument(instrument_id: int, instrument: InstrumentCreate, db: Session = Depends(get_db)):
    db_instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if db_instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")

    for key, value in instrument.model_dump().items():
        setattr(db_instrument, key, value)

    db.commit()
    db.refresh(db_instrument)
    return db_instrument

@router.delete("/{instrument_id}", response_model=InstrumentSchema)
def delete_instrument(instrument_id: int, db: Session = Depends(get_db)):
    db_instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
    if db_instrument is None:
        raise HTTPException(status_code=404, detail="Instrument not found")

    db.delete(db_instrument)
    db.commit()
    return db_instrument

# Kite Connect WebSocket integration
KITE_API_KEY = os.getenv("KITE_API_KEY", "your_api_key")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "your_access_token")

kws = KiteTicker(KITE_API_KEY, KITE_ACCESS_TOKEN)

@router.websocket("/ws/live-price/{instrument_token}")
async def websocket_endpoint(websocket: WebSocket, instrument_token: int):
    await manager.connect(websocket)

    # Define callbacks for the WebSocket instance
    async def on_ticks(ws, ticks):
        for tick in ticks:
            # Send the tick data as a JSON string to the specific client
            await manager.send_personal_message(json.dumps(tick), websocket)

    def on_connect(ws, response):
        # Subscribe to the instrument token
        ws.subscribe([instrument_token])
        ws.set_mode(ws.MODE_FULL, [instrument_token])

    def on_close(ws, code, reason):
        # Can add logic here to handle disconnection from Kite's end
        pass

    # Assign callbacks
    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    # This is a bit of a workaround for a single global kws instance.
    # In a production scenario, you'd want a more robust way to manage this,
    # perhaps one KiteTicker per connection or a more complex multiplexing system.
    if not kws.is_connected():
        kws.connect(threaded=True)

    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # In a more complex app, you might want to unsubscribe if no one is listening.
        # kws.unsubscribe([instrument_token])
        # if len(manager.active_connections) == 0:
        #     kws.close(1000, "No active clients")