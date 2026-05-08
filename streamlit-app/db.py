from pathlib import Path
import os

from sqlalchemy import create_engine

try:
    import streamlit as st  # type: ignore
    _HAS_ST = True
except Exception:
    _HAS_ST = False

try:
    import tomllib
except ImportError:
    import tomli as tomllib


BASE_DIR = Path(__file__).resolve().parents[1]
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"

# Streamlit 미사용 환경 (배치 / ETL) 용 모듈 전역 fallback
_ENGINE = None


def load_db_url():
    secrets = {}
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)

    # 폐쇄망 사내 PC 환경 — env / secrets.toml 둘 다 없을 때 즉시 작동을 위한
    # fallback. 이 password 는 streamlit-app/.streamlit/secrets.toml +
    # streamlit-app/pages/setting.ini 에도 평문으로 git commit 되어 있음
    # (사용자 의식적 결정, .gitignore 의 주석 참조). 외부 공개 시 즉시 회전 필요.
    return os.getenv(
        "DB_URL",
        secrets.get("DB_URL", "postgresql+psycopg2://postgres:!Q2w3e4r5t@localhost:5432/MTBA")
    )


def _build_engine():
    """SQLAlchemy 엔진 생성 — 단일 호출."""
    db_url = load_db_url()
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


# PERF #5 — Streamlit 환경에선 @st.cache_resource 로 워커-안전 싱글톤
# (멀티워커 / multipage 환경에서 같은 엔진 객체 공유, connection pool 누수 방지).
# Streamlit 미사용 환경 (배치 스크립트 / ETL) 에선 모듈 전역 _ENGINE fallback.
if _HAS_ST:
    @st.cache_resource(show_spinner=False)
    def get_engine():
        return _build_engine()
else:
    def get_engine():
        global _ENGINE
        if _ENGINE is None:
            _ENGINE = _build_engine()
        return _ENGINE
