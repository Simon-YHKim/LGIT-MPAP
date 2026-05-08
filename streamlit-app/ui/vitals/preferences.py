"""
ui.vitals.preferences — Per-user UI preferences (theme, locale).

Schema (lazy-created on first call):
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id    TEXT PRIMARY KEY,
        theme      TEXT,
        locale     TEXT,
        updated_at TIMESTAMP DEFAULT NOW()
    )

All queries are parameterized via SQLAlchemy text() — no string interpolation.
Engine is shared via db.get_engine() to honor PERF #5 (cached singleton).

Designed to fail soft: any DB error is logged via st.toast (if available) and
swallowed, so a transient DB outage never blocks page render.
"""
from __future__ import annotations
from typing import Optional

from sqlalchemy import text

# db 는 streamlit-app 루트 모듈. 호출 측은 항상 streamlit-app 을 cwd 로 실행.
try:
    from db import get_engine
except Exception:  # pragma: no cover - defensive for non-Streamlit contexts
    get_engine = None  # type: ignore


_DDL = """
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id    TEXT PRIMARY KEY,
    theme      TEXT,
    locale     TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
)
"""

_ensured = False


def _ensure_schema() -> None:
    """idempotent — 첫 호출에만 DDL 실행."""
    global _ensured
    if _ensured or get_engine is None:
        return
    try:
        eng = get_engine()
        with eng.begin() as cx:
            cx.execute(text(_DDL))
        _ensured = True
    except Exception:
        # DB 미가동/권한 등은 silent — 페이지 렌더 막지 않음
        pass


def get_user_theme_pref(user_id: str) -> Optional[str]:
    """저장된 사용자 테마 ('light' | 'dark') 반환. 없거나 오류면 None."""
    if not user_id or get_engine is None:
        return None
    _ensure_schema()
    try:
        eng = get_engine()
        with eng.connect() as cx:
            row = cx.execute(
                text("SELECT theme FROM user_preferences WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()
        if not row:
            return None
        val = row[0]
        return val if val in ("light", "dark") else None
    except Exception:
        return None


def save_user_theme_pref(user_id: str, theme: str) -> bool:
    """사용자 테마 저장 (UPSERT). 성공 시 True, 실패 시 False."""
    if not user_id or get_engine is None:
        return False
    if theme not in ("light", "dark"):
        return False
    _ensure_schema()
    try:
        eng = get_engine()
        with eng.begin() as cx:
            cx.execute(
                text(
                    """
                    INSERT INTO user_preferences (user_id, theme, updated_at)
                    VALUES (:uid, :theme, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET theme = EXCLUDED.theme,
                        updated_at = NOW()
                    """
                ),
                {"uid": user_id, "theme": theme},
            )
        return True
    except Exception:
        return False


def get_user_locale_pref(user_id: str) -> Optional[str]:
    """저장된 locale 반환 (현재는 read-only 헬퍼 — 향후 i18n 연계용)."""
    if not user_id or get_engine is None:
        return None
    _ensure_schema()
    try:
        eng = get_engine()
        with eng.connect() as cx:
            row = cx.execute(
                text("SELECT locale FROM user_preferences WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def save_user_locale_pref(user_id: str, locale: str) -> bool:
    if not user_id or get_engine is None or not locale:
        return False
    _ensure_schema()
    try:
        eng = get_engine()
        with eng.begin() as cx:
            cx.execute(
                text(
                    """
                    INSERT INTO user_preferences (user_id, locale, updated_at)
                    VALUES (:uid, :locale, NOW())
                    ON CONFLICT (user_id) DO UPDATE
                    SET locale = EXCLUDED.locale,
                        updated_at = NOW()
                    """
                ),
                {"uid": user_id, "locale": locale},
            )
        return True
    except Exception:
        return False


__all__ = [
    "get_user_theme_pref",
    "save_user_theme_pref",
    "get_user_locale_pref",
    "save_user_locale_pref",
]
