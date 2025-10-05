from pathlib import Path
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = "Trading Backend API"
    secret_key: str = Field("super-secret-key", env="SECRET_KEY")
    access_token_expire_minutes: int = 60 * 8
    algorithm: str = "HS256"
    data_dir: Path = Path("data")
    instrument_db_path: Path = Path("data") / "instruments.db"
    kite_api_key: str = Field("", env="KITE_API_KEY")
    kite_base_url: str = Field("https://api.kite.trade", env="KITE_BASE_URL")

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
