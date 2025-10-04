from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import (
    admin,
    auth,
    automations,
    instruments,
    ledger,
    market,
    notifications,
    orders,
    portfolio,
    reports,
    system,
    watchlists,
    wallet,
)
from app.api.v1.stream import router as stream_router
from app.core.security import get_password_hash
from app.models.user import User
from app.services.instrument_store import instrument_store
from app.services.storage import get_db

app = FastAPI(title="Trading Backend API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1_prefix = "/v1"
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(instruments.router, prefix=api_v1_prefix)
app.include_router(market.router, prefix=api_v1_prefix)
app.include_router(watchlists.router, prefix=api_v1_prefix)
app.include_router(orders.router, prefix=api_v1_prefix)
app.include_router(portfolio.router, prefix=api_v1_prefix)
app.include_router(wallet.router, prefix=api_v1_prefix)
app.include_router(ledger.router, prefix=api_v1_prefix)
app.include_router(reports.router, prefix=api_v1_prefix)
app.include_router(notifications.router, prefix=api_v1_prefix)
app.include_router(admin.router, prefix=api_v1_prefix)
app.include_router(system.router, prefix=api_v1_prefix)
app.include_router(automations.router, prefix=api_v1_prefix)
app.include_router(stream_router, prefix=api_v1_prefix)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
async def bootstrap() -> None:
    instrument_store.initialize()
    db = get_db()
    if not any("admin" in user.roles for user in db.users.values()):
        admin_user = User(
            email="admin@example.com",
            name="Platform Admin",
            roles=["admin", "client"],
        )
        admin_user.password_hash = get_password_hash("admin123")  # type: ignore[attr-defined]
        db.users[admin_user.id] = admin_user
        db.get_or_create_wallet(admin_user.id)


if FRONTEND_DIR.exists():

    @app.get("/", include_in_schema=False)
    async def serve_frontend() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

else:

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Trading Backend API", "version": "v1"}
