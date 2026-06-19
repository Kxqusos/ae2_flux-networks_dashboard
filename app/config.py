import os

from pydantic import BaseModel


class Settings(BaseModel):
    api_token: str
    ui_password: str
    db_path: str = "dashboard.db"
    retention_days: int = 7


def get_settings() -> Settings:
    api_token = os.environ.get("API_TOKEN", "")
    ui_password = os.environ.get("UI_PASSWORD", "")
    if not api_token:
        raise ValueError("API_TOKEN environment variable is required")
    if not ui_password:
        raise ValueError("UI_PASSWORD environment variable is required")

    return Settings(
        api_token=api_token,
        ui_password=ui_password,
        db_path=os.environ.get("DB_PATH", "dashboard.db"),
        retention_days=int(os.environ.get("RETENTION_DAYS", "7")),
    )
