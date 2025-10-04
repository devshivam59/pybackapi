from io import TextIOWrapper
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.deps import get_current_user, require_admin
from app.models.common import Instrument, InstrumentImport, InstrumentSource
from app.models.user import User
from app.services.instrument_store import instrument_store
from app.services.storage import get_db

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_instruments(
    source: str = Query(..., regex="^(upstox|zerodha|dhan|custom)$"),
    file: UploadFile = File(...),
    replace_existing: bool = Query(False, description="Delete existing instruments before import"),
    _: User = Depends(require_admin),
) -> Dict[str, Any]:
    import_record = instrument_store.start_import(source)
    try:
        file.file.seek(0)
        text_stream = TextIOWrapper(file.file, encoding="utf-8", newline="")
        try:
            rows_in, rows_ok, rows_err, errors = instrument_store.import_csv(
                text_stream,
                replace_existing=replace_existing,
            )
        finally:
            text_stream.close()
    except ValueError as exc:  # noqa: BLE001
        instrument_store.fail_import(import_record.id, [str(exc)])
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        instrument_store.fail_import(import_record.id, [str(exc)])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import instruments",
        ) from exc
    finally:
        await file.close()

    updated = instrument_store.finish_import(
        import_record.id,
        rows_in,
        rows_ok,
        rows_err,
        errors,
    )
    return {
        "import_id": updated.id,
        "status": updated.status,
        "rows_in": updated.rows_in,
        "rows_ok": updated.rows_ok,
        "rows_err": updated.rows_err,
        "errors": updated.errors,
        "replaced": replace_existing,
    }


@router.get("/imports")
async def list_imports(_: User = Depends(require_admin)) -> List[InstrumentImport]:
    return instrument_store.list_imports()


@router.get("/imports/{import_id}")
async def get_import(import_id: str, _: User = Depends(require_admin)) -> InstrumentImport:
    try:
        return instrument_store.get_import(import_id)
    except KeyError as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import not found") from exc


@router.post("/sources")
async def create_source(
    source: InstrumentSource,
    _: User = Depends(require_admin),
) -> InstrumentSource:
    db = get_db()
    db.instrument_sources[source.id] = source
    return source


@router.get("/sources")
async def list_sources(_: User = Depends(get_current_user)) -> List[InstrumentSource]:
    db = get_db()
    return list(db.instrument_sources.values())


@router.get("")
async def search_instruments(
    q: Optional[str] = Query(default=None),
    segment: Optional[str] = None,
    exchange: Optional[str] = None,
    instrument_type: Optional[str] = Query(default=None, alias="type"),
    limit: int = Query(default=20, le=500),
    cursor: Optional[str] = None,
    _: User = Depends(get_current_user),
) -> Dict[str, Any]:
    offset = 0
    if cursor:
        try:
            offset = int(cursor)
        except ValueError as exc:  # noqa: BLE001
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
        if offset < 0:
            offset = 0

    items, next_cursor, total = instrument_store.search(
        query=q.strip() if q else None,
        segment=segment,
        exchange=exchange,
        instrument_type=instrument_type,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "next_cursor": next_cursor, "total": total}


@router.get("/{instrument_id}")
async def get_instrument(instrument_id: str, _: User = Depends(get_current_user)) -> Instrument:
    instrument = instrument_store.get_instrument(instrument_id)
    if instrument is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument not found")
    return instrument


@router.get("/map")
async def map_broker_symbol(
    broker: str = Query(...),
    token: str = Query(...),
    _: User = Depends(get_current_user),
) -> Instrument:
    instrument = instrument_store.get_instrument_by_token(token)
    if instrument and broker:
        return instrument
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instrument mapping not found")


@router.delete("")
async def delete_instruments(_: User = Depends(require_admin)) -> Dict[str, Any]:
    deleted = instrument_store.clear_instruments()
    return {"detail": "Instruments deleted", "deleted": deleted}
