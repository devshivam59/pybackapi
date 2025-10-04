from __future__ import annotations

import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from io import TextIOBase
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple
from uuid import NAMESPACE_URL, uuid5

from rapidfuzz import fuzz, process

from app.core.config import get_settings
from app.models.common import Instrument, InstrumentImport

REQUIRED_COLUMNS = {
    "instrument_token",
    "exchange_token",
    "tradingsymbol",
    "name",
    "last_price",
    "expiry",
    "strike",
    "tick_size",
    "lot_size",
    "instrument_type",
    "segment",
    "exchange",
}


class InstrumentStore:
    """SQLite-backed store for instrument metadata and import tracking."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        batch_size: int = 2000,
        max_candidates: int = 2000,
    ) -> None:
        settings = get_settings()
        self.db_path = Path(db_path or settings.instrument_db_path)
        self.batch_size = batch_size
        self.max_candidates = max_candidates
        self._initialized = False
        self._namespace = uuid5(NAMESPACE_URL, "pybackapi.instrument")

    def initialize(self) -> None:
        if self._initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA cache_size=-131072;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS instruments (
                    instrument_id TEXT PRIMARY KEY,
                    instrument_token TEXT NOT NULL UNIQUE,
                    exchange_token TEXT NOT NULL,
                    tradingsymbol TEXT NOT NULL,
                    name TEXT,
                    last_price REAL DEFAULT 0,
                    expiry TEXT,
                    strike REAL,
                    tick_size REAL NOT NULL,
                    lot_size INTEGER NOT NULL,
                    instrument_type TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_instruments_tradingsymbol
                ON instruments(tradingsymbol)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_instruments_tradingsymbol_nocase
                ON instruments(tradingsymbol COLLATE NOCASE)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_instruments_segment
                ON instruments(segment)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_instruments_exchange
                ON instruments(exchange)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_instruments_instrument_type
                ON instruments(instrument_type)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS instrument_imports (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    rows_in INTEGER DEFAULT 0,
                    rows_ok INTEGER DEFAULT 0,
                    rows_err INTEGER DEFAULT 0,
                    status TEXT NOT NULL,
                    errors TEXT,
                    log_url TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        self._initialized = True

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        self.initialize()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def start_import(self, source: str) -> InstrumentImport:
        record = InstrumentImport(source=source, status="processing")
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO instrument_imports (
                    id, source, started_at, status, rows_in, rows_ok, rows_err, errors, log_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.source,
                    record.started_at.isoformat(),
                    record.status,
                    record.rows_in,
                    record.rows_ok,
                    record.rows_err,
                    json.dumps(record.errors),
                    record.log_url,
                ),
            )
        return record

    def finish_import(
        self,
        import_id: str,
        rows_in: int,
        rows_ok: int,
        rows_err: int,
        errors: Sequence[str],
    ) -> InstrumentImport:
        status = "completed" if rows_err == 0 else "completed_with_errors"
        finished_at = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE instrument_imports
                SET finished_at = ?, rows_in = ?, rows_ok = ?, rows_err = ?, status = ?, errors = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    rows_in,
                    rows_ok,
                    rows_err,
                    status,
                    json.dumps(list(errors)),
                    import_id,
                ),
            )
        return self.get_import(import_id)

    def fail_import(self, import_id: str, errors: Sequence[str]) -> InstrumentImport:
        finished_at = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE instrument_imports
                SET finished_at = ?, status = ?, errors = ?
                WHERE id = ?
                """,
                (finished_at, "failed", json.dumps(list(errors)), import_id),
            )
        return self.get_import(import_id)

    def get_import(self, import_id: str) -> InstrumentImport:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM instrument_imports WHERE id = ?",
                (import_id,),
            ).fetchone()
        if row is None:
            raise KeyError(import_id)
        return self._row_to_import(row)

    def list_imports(self) -> List[InstrumentImport]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM instrument_imports ORDER BY started_at DESC",
            ).fetchall()
        return [self._row_to_import(row) for row in rows]

    def import_csv(
        self,
        csv_stream: TextIOBase,
        *,
        replace_existing: bool = False,
    ) -> Tuple[int, int, int, List[str]]:
        reader = csv.DictReader(csv_stream)
        if not reader.fieldnames:
            raise ValueError("CSV file is missing headers")
        normalized_headers = {header.strip() for header in reader.fieldnames if header}
        missing = REQUIRED_COLUMNS - normalized_headers
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

        rows_in = rows_ok = rows_err = 0
        errors: List[str] = []
        batch: List[Tuple] = []
        now = datetime.utcnow

        with self._get_connection() as conn:
            existing_ids = self._load_existing_ids(conn)
            if replace_existing:
                conn.execute("DELETE FROM instruments")
            for row in reader:
                rows_in += 1
                try:
                    normalized = self._prepare_row(row, now(), existing_ids)
                except ValueError as exc:  # noqa: PERF203
                    rows_err += 1
                    errors.append(f"Row {rows_in}: {exc}")
                    continue
                batch.append(normalized)
                rows_ok += 1
                if len(batch) >= self.batch_size:
                    self._bulk_upsert(conn, batch)
                    batch.clear()
            if batch:
                self._bulk_upsert(conn, batch)
        return rows_in, rows_ok, rows_err, errors

    def _bulk_upsert(self, conn: sqlite3.Connection, batch: Sequence[Tuple]) -> None:
        conn.executemany(
            """
            INSERT INTO instruments (
                instrument_id,
                instrument_token,
                exchange_token,
                tradingsymbol,
                name,
                last_price,
                expiry,
                strike,
                tick_size,
                lot_size,
                instrument_type,
                segment,
                exchange,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(instrument_token) DO UPDATE SET
                exchange_token = excluded.exchange_token,
                tradingsymbol = excluded.tradingsymbol,
                name = excluded.name,
                last_price = excluded.last_price,
                expiry = excluded.expiry,
                strike = excluded.strike,
                tick_size = excluded.tick_size,
                lot_size = excluded.lot_size,
                instrument_type = excluded.instrument_type,
                segment = excluded.segment,
                exchange = excluded.exchange,
                updated_at = excluded.updated_at
            """,
            batch,
        )

    def _prepare_row(
        self,
        row: dict,
        timestamp: datetime,
        existing_ids: Dict[str, str],
    ) -> Tuple:
        def clean_str(value: Optional[str]) -> str:
            return (value or "").strip()

        def parse_float(value: Optional[str], field: str, *, required: bool = False) -> float:
            if value is None or value == "":
                if required:
                    raise ValueError(f"{field} is required")
                return 0.0
            try:
                return float(value)
            except ValueError as exc:  # noqa: B904
                raise ValueError(f"Invalid float for {field}: {value}") from exc

        def parse_int(value: Optional[str], field: str, *, required: bool = False) -> int:
            if value is None or value == "":
                if required:
                    raise ValueError(f"{field} is required")
                return 0
            try:
                return int(float(value))
            except ValueError as exc:  # noqa: B904
                raise ValueError(f"Invalid integer for {field}: {value}") from exc

        instrument_token = clean_str(row.get("instrument_token"))
        if not instrument_token:
            raise ValueError("instrument_token is required")
        exchange_token = clean_str(row.get("exchange_token"))
        if not exchange_token:
            raise ValueError("exchange_token is required")
        tradingsymbol = clean_str(row.get("tradingsymbol"))
        if not tradingsymbol:
            raise ValueError("tradingsymbol is required")
        name = clean_str(row.get("name")) or None
        expiry = clean_str(row.get("expiry")) or None
        instrument_type = clean_str(row.get("instrument_type"))
        segment = clean_str(row.get("segment"))
        exchange = clean_str(row.get("exchange"))
        if not instrument_type:
            raise ValueError("instrument_type is required")
        if not segment:
            raise ValueError("segment is required")
        if not exchange:
            raise ValueError("exchange is required")

        instrument_type = instrument_type.upper()
        segment = segment.upper()
        exchange = exchange.upper()

        key = self._make_key(exchange, instrument_token)
        instrument_id = existing_ids.get(key)
        if instrument_id is None:
            instrument_id = self._generate_instrument_id(exchange, instrument_token)
            existing_ids[key] = instrument_id

        return (
            instrument_id,
            instrument_token,
            exchange_token,
            tradingsymbol,
            name,
            parse_float(row.get("last_price"), "last_price"),
            expiry,
            parse_float(row.get("strike"), "strike"),
            parse_float(row.get("tick_size"), "tick_size", required=True),
            parse_int(row.get("lot_size"), "lot_size", required=True),
            instrument_type,
            segment,
            exchange,
            timestamp.isoformat(),
            timestamp.isoformat(),
        )

    def _generate_instrument_id(self, exchange: str, instrument_token: str) -> str:
        seed = f"{exchange}:{instrument_token}"
        return f"ins_{uuid5(self._namespace, seed).hex}"

    def _load_existing_ids(self, conn: sqlite3.Connection) -> Dict[str, str]:
        rows = conn.execute(
            "SELECT instrument_token, exchange, instrument_id FROM instruments",
        ).fetchall()
        return {
            self._make_key(row["exchange"], row["instrument_token"]): row["instrument_id"]
            for row in rows
        }

    @staticmethod
    def _make_key(exchange: str, instrument_token: str) -> str:
        return f"{exchange.upper()}:{instrument_token}"

    def clear_instruments(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM instruments")
            total = int(cursor.fetchone()[0])
            conn.execute("DELETE FROM instruments")
        return total

    def count_instruments(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM instruments")
            result = cursor.fetchone()
        return int(result[0]) if result else 0

    def get_instruments_by_ids(self, instrument_ids: Sequence[str]) -> List[Instrument]:
        if not instrument_ids:
            return []
        placeholders = ",".join("?" for _ in instrument_ids)
        with self._get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM instruments WHERE instrument_id IN ({placeholders})",
                list(instrument_ids),
            ).fetchall()
        row_map = {row["instrument_id"]: self._row_to_instrument(row) for row in rows}
        return [row_map[instrument_id] for instrument_id in instrument_ids if instrument_id in row_map]

    def get_instrument(self, instrument_id: str) -> Optional[Instrument]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM instruments WHERE instrument_id = ?",
                (instrument_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_instrument(row)

    def get_instrument_by_token(self, instrument_token: str) -> Optional[Instrument]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM instruments WHERE instrument_token = ?",
                (instrument_token,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_instrument(row)

    def search(
        self,
        *,
        query: Optional[str],
        segment: Optional[str],
        exchange: Optional[str],
        instrument_type: Optional[str],
        limit: int,
        offset: int,
    ) -> Tuple[List[Instrument], Optional[str], int]:
        where_clauses = ["1=1"]
        params: List[str] = []
        if segment:
            where_clauses.append("segment = ?")
            params.append(segment)
        if exchange:
            where_clauses.append("exchange = ?")
            params.append(exchange)
        if instrument_type:
            where_clauses.append("instrument_type = ?")
            params.append(instrument_type)

        base_where = " AND ".join(where_clauses)
        total = 0

        with self._get_connection() as conn:
            if query:
                like_term = f"%{query}%"
                like_where = (
                    f"{base_where} AND ("
                    " tradingsymbol LIKE ? COLLATE NOCASE OR"
                    " name LIKE ? COLLATE NOCASE OR"
                    " instrument_token LIKE ?"
                    ")"
                )
                like_params = params + [like_term, like_term, like_term]
                count_row = conn.execute(
                    f"SELECT COUNT(*) as total FROM instruments WHERE {like_where}",
                    like_params,
                ).fetchone()
                total = int(count_row["total"]) if count_row else 0
                candidate_limit = max(min(self.max_candidates, offset + limit * 2), limit)
                candidate_rows = conn.execute(
                    f"""
                    SELECT * FROM instruments
                    WHERE {like_where}
                    ORDER BY tradingsymbol COLLATE NOCASE
                    LIMIT ?
                    """,
                    like_params + [candidate_limit],
                ).fetchall()
                if not candidate_rows and not total:
                    return [], None, 0
                row_map = {row["instrument_id"]: row for row in candidate_rows}
                if not row_map:
                    return [], None, total
                choices = {
                    instrument_id: f"{row['tradingsymbol']} {row['name'] or ''}"
                    for instrument_id, row in row_map.items()
                }
                matches = process.extract(
                    query,
                    choices,
                    scorer=fuzz.WRatio,
                    limit=offset + limit,
                )
                ordered_ids = [match[0] for match in matches]
                sliced_ids = ordered_ids[offset : offset + limit]
                instruments = [self._row_to_instrument(row_map[row_id]) for row_id in sliced_ids]
                total = min(total, len(ordered_ids)) if total else len(ordered_ids)
            else:
                count_row = conn.execute(
                    f"SELECT COUNT(*) as total FROM instruments WHERE {base_where}",
                    params,
                ).fetchone()
                total = int(count_row["total"]) if count_row else 0
                rows = conn.execute(
                    f"""
                    SELECT * FROM instruments
                    WHERE {base_where}
                    ORDER BY tradingsymbol COLLATE NOCASE
                    LIMIT ? OFFSET ?
                    """,
                    params + [limit, offset],
                ).fetchall()
                instruments = [self._row_to_instrument(row) for row in rows]

        next_cursor: Optional[str] = None
        if offset + limit < total:
            next_cursor = str(offset + limit)
        return instruments, next_cursor, total

    def _row_to_instrument(self, row: sqlite3.Row) -> Instrument:
        return Instrument(
            id=row["instrument_id"],
            instrument_token=row["instrument_token"],
            exchange_token=row["exchange_token"],
            tradingsymbol=row["tradingsymbol"],
            name=row["name"],
            last_price=row["last_price"] or 0.0,
            expiry=row["expiry"],
            strike=row["strike"],
            tick_size=row["tick_size"],
            lot_size=row["lot_size"],
            instrument_type=row["instrument_type"],
            segment=row["segment"],
            exchange=row["exchange"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_import(self, row: sqlite3.Row) -> InstrumentImport:
        return InstrumentImport(
            id=row["id"],
            source=row["source"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"])
            if row["finished_at"]
            else None,
            rows_in=row["rows_in"],
            rows_ok=row["rows_ok"],
            rows_err=row["rows_err"],
            status=row["status"],
            errors=json.loads(row["errors"]) if row["errors"] else [],
            log_url=row["log_url"],
        )


instrument_store = InstrumentStore()
