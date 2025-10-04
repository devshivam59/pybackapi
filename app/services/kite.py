from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import httpx

from app.core.config import get_settings
from app.models.common import Instrument
from app.services.storage import get_db

logger = logging.getLogger(__name__)


class KiteService:
    """Simple helper for managing Kite Connect credentials and quote retrieval."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.kite_base_url.rstrip("/")
        self._default_api_key = settings.kite_api_key.strip()
        self._timeout = httpx.Timeout(8.0, connect=5.0, read=8.0, write=5.0)

    # ------------------------------------------------------------------
    # Credential management helpers
    # ------------------------------------------------------------------
    def set_credentials(
        self,
        *,
        api_key: str,
        access_token: str,
        valid_till: Optional[datetime] = None,
    ) -> None:
        """Persist credentials in the in-memory store."""

        db = get_db()
        db.kite_api_key = api_key.strip() or None
        db.kite_access_token = access_token.strip() or None
        db.kite_token_valid_till = valid_till
        db.kite_token_updated_at = datetime.utcnow()
        logger.info("Kite credentials updated; valid_till=%s", valid_till)

    def clear_credentials(self) -> None:
        db = get_db()
        db.kite_api_key = None
        db.kite_access_token = None
        db.kite_token_valid_till = None
        db.kite_token_updated_at = datetime.utcnow()
        logger.info("Cleared Kite credentials")

    def record_request_token(self, request_token: str) -> None:
        db = get_db()
        db.kite_last_request_token = request_token.strip()
        db.kite_request_token_at = datetime.utcnow()
        logger.info("Stored Kite request token")

    def _credentials(self) -> Dict[str, Any]:
        db = get_db()
        api_key = db.kite_api_key or self._default_api_key or None
        access_token = db.kite_access_token or None
        return {
            "api_key": api_key,
            "access_token": access_token,
            "valid_till": db.kite_token_valid_till,
            "updated_at": db.kite_token_updated_at,
            "request_token": db.kite_last_request_token,
            "request_token_at": db.kite_request_token_at,
        }

    def status(self) -> Dict[str, Any]:
        creds = self._credentials()
        api_key = creds["api_key"]
        access_token = creds["access_token"]
        return {
            "configured": bool(api_key and access_token),
            "api_key_last4": api_key[-4:] if api_key else None,
            "access_token_last4": access_token[-4:] if access_token else None,
            "valid_till": creds["valid_till"].isoformat() if creds["valid_till"] else None,
            "updated_at": creds["updated_at"].isoformat() if creds["updated_at"] else None,
            "request_token": creds["request_token"],
            "request_token_at": creds["request_token_at"].isoformat()
            if creds["request_token_at"]
            else None,
            "base_url": self._base_url,
        }

    # ------------------------------------------------------------------
    # Quote fetching helpers
    # ------------------------------------------------------------------
    def _build_auth_header(self, api_key: str, access_token: str) -> str:
        return f"token {api_key}:{access_token}"

    async def fetch_quotes(
        self, instruments: Iterable[Instrument]
    ) -> Dict[str, Dict[str, Any]]:
        """Return the latest quotes for the provided instruments."""

        instrument_list = list(instruments)
        if not instrument_list:
            return {}

        creds = self._credentials()
        api_key = creds["api_key"]
        access_token = creds["access_token"]
        if not api_key or not access_token:
            return {}

        token_map: Dict[str, Instrument] = {}
        for instrument in instrument_list:
            token = instrument.instrument_token
            if token:
                token_map[str(token)] = instrument

        if not token_map:
            return {}

        params = [("i", token) for token in token_map]
        headers = {
            "Authorization": self._build_auth_header(api_key, access_token),
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                response = await client.get("/quote", params=params, headers=headers)
                response.raise_for_status()
        except Exception as exc:  # pragma: no cover - network errors handled gracefully
            logger.warning("Failed to fetch Kite quotes: %s", exc)
            return {}

        payload = response.json().get("data", {}) if response.content else {}
        now_iso = datetime.utcnow().isoformat()
        results: Dict[str, Dict[str, Any]] = {}
        for token, instrument in token_map.items():
            quote = payload.get(token)
            if not quote:
                continue
            last_price = quote.get("last_price") or quote.get("last_traded_price")
            if last_price is None:
                continue
            timestamp = quote.get("timestamp") or quote.get("last_trade_time") or now_iso
            results[instrument.id] = {
                "ltp": float(last_price),
                "timestamp": timestamp,
                "source": "kite",
                "token": token,
            }
        return results

    async def ping(self) -> tuple[bool, str]:
        creds = self._credentials()
        api_key = creds["api_key"]
        access_token = creds["access_token"]
        if not api_key or not access_token:
            return False, "No Kite API key/access token configured"
        headers = {
            "Authorization": self._build_auth_header(api_key, access_token),
            "Accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout
            ) as client:
                response = await client.get("/marketstatus", headers=headers)
                response.raise_for_status()
        except Exception as exc:  # pragma: no cover - depends on network access
            logger.warning("Kite ping failed: %s", exc)
            return False, f"Ping failed: {exc}"
        return True, "Kite connectivity OK"


kite_service = KiteService()
