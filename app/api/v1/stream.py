import json
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    subscriptions: Dict[str, List[str]] = {}
    try:
        while True:
            message = await websocket.receive_text()
            payload = json.loads(message)
            msg_type = payload.get("type")
            if msg_type == "auth":
                await websocket.send_json({"type": "system", "detail": "authenticated"})
            elif msg_type == "prices.subscribe":
                instrument_ids = payload.get("instrument_ids", [])
                subscriptions.setdefault("prices", []).extend(instrument_ids)
                await websocket.send_json({"type": "prices.subscribed", "data": instrument_ids})
            elif msg_type == "prices.unsubscribe":
                instrument_ids = payload.get("instrument_ids", [])
                current = subscriptions.get("prices", [])
                subscriptions["prices"] = [ins for ins in current if ins not in instrument_ids]
                await websocket.send_json({"type": "prices.unsubscribed", "data": instrument_ids})
            else:
                await websocket.send_json({"type": "error", "message": "Unsupported message"})
    except WebSocketDisconnect:
        return
