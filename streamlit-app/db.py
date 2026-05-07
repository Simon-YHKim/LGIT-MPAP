from pathlib import Path
import os

from sqlalchemy import create_engine

try:
    import tomllib
except ImportError:
    import tomli as tomllib


BASE_DIR = Path(__file__).resolve().parents[1]
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"

_ENGINE = None


def load_db_url():
    secrets = {}
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)

    return os.getenv(
        "DB_URL",
        secrets.get("DB_URL", "postgresql+psycopg2://postgres:!Q2w3e4r5t@localhost:5432/MTBA")
    )


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        db_url = load_db_url()
        _ENGINE = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=1800,
            future=True,
        )
    return _ENGINE