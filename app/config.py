from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    access_token_expire_minutes: int


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("Set JWT_SECRET to a secret of at least 32 bytes in .env.")
    try:
        minutes = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    except ValueError as exc:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer.") from exc
    if minutes <= 0:
        raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be a positive integer.")
    return Settings(jwt_secret=secret, access_token_expire_minutes=minutes)
