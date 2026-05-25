from pathlib import Path

from pydantic import EmailStr
from pydantic_settings import BaseSettings


ROOT_DIR = Path(__file__).resolve().parents[2]
_env_candidates = (ROOT_DIR / ".env", ROOT_DIR.parent / ".env")
ENV_FILE = next((p for p in _env_candidates if p.exists()), _env_candidates[0])


class Settings(BaseSettings):
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str
    SCHEMA_NAME: str
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    GROQ_API_KEY: str

    class Config:
        env_file = ENV_FILE


settings = Settings()
