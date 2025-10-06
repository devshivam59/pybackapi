from fastapi import APIRouter
from .endpoints import instrument

api_router = APIRouter()
api_router.include_router(instrument.router, prefix="/instruments", tags=["instruments"])