from pydantic import BaseSettings, Field


from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Trading Backend API"
    secret_key: str = Field("super-secret-key", env="SECRET_KEY")
    access_token_expire_minutes: int = 60 * 8
    algorithm: str = "HS256"
    data_dir: Path = Path("data")
    instrument_db_path: Path = Path("data") / "instruments.db"

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
