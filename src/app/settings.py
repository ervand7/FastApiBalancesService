import os

import dotenv
from pydantic import PostgresDsn

dotenv.load_dotenv()


class Settings:
    service_name: str = "Balance Service"
    debug: bool = os.getenv("DEBUG", "false").lower() in ("true", "1")
    app_port: int = int(os.getenv("APP_PORT", 8000))
    log_level: str = os.getenv("LOG_LEVEL", "info")

    # Database settings
    db_dsn: PostgresDsn = os.getenv(
        "DATABASE_URL",
    )

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    return Settings()
