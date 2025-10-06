from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1.api import api_router
import os

app = FastAPI(title="Trading Backend API")

# Mount static files
static_files_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_files_path, 'index.html'))