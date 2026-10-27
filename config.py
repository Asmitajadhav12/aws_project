"""Application configuration.

Every value that differs between machines or is sensitive comes from the
environment (a local .env file). Nothing secret is hardcoded here.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load .env from the project root if it exists. In production the real
# environment variables simply take precedence.
load_dotenv(BASE_DIR / ".env")


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    # --- Flask ---------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")
    DEBUG = _as_bool(os.getenv("FLASK_DEBUG"), default=False)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _as_bool(os.getenv("SESSION_COOKIE_SECURE"), default=False)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=45)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "64")) * 1024 * 1024

    # --- MySQL ---------------------------------------------------------
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "retail_app")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "txn_rules_db")
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))

    # --- Paths ---------------------------------------------------------
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".xlsx"}

    # Rows per batch when importing a dataset file into MySQL.
    IMPORT_CHUNK_SIZE = int(os.getenv("IMPORT_CHUNK_SIZE", "5000"))
