# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore


# =========================================================
# CONFIG
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[1]
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"

# True 로 바꾸면 사용자 입력 테이블까지 전부 초기화
RESET_USER_TABLES = False

# 세션 종료 재시도 설정
TERMINATE_RETRY_COUNT = 10
TERMINATE_SLEEP_SEC = 1.0


# =========================================================
# DB CONFIG
# =========================================================

def load_db_url() -> str:
    secrets = {}
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)

    # 폐쇄망 사내 PC fallback — db.py 와 동일 패턴. password 는 secrets.toml +
    # setting.ini 에도 평문 commit 됨 (사용자 의식적 결정). 외부 공개 시 회전.
    return os.getenv(
        "DB_URL",
        secrets.get(
            "DB_URL",
            "postgresql+psycopg2://postgres:!Q2w3e4r5t@localhost:5432/MTBA"
        )
    )


DB_URL = load_db_url()
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)


def get_db_name() -> str:
    url = make_url(DB_URL)
    return url.database or "MTBA"


# =========================================================
# COMMON HELPERS
# =========================================================

def table_exists(conn, full_table_name: str) -> bool:
    return conn.execute(
        text("SELECT to_regclass(:table_name)"),
        {"table_name": full_table_name}
    ).scalar() is not None


def truncate_if_exists(conn, table_name: str) -> None:
    if table_exists(conn, table_name):
        print(f"[INFO] TRUNCATE: {table_name}")
        conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))
    else:
        print(f"[WARN] 테이블 없음 - 건너뜀: {table_name}")


def drop_if_exists(conn, obj_name: str, obj_type: str = "TABLE") -> None:
    print(f"[INFO] DROP {obj_type} IF EXISTS: {obj_name}")
    conn.execute(text(f"DROP {obj_type} IF EXISTS {obj_name} CASCADE"))


def refresh_mv_if_exists(conn, mv_name: str) -> None:
    if table_exists(conn, mv_name):
        print(f"[INFO] REFRESH MATERIALIZED VIEW: {mv_name}")
        conn.execute(text(f"REFRESH MATERIALIZED VIEW {mv_name}"))


def print_connection_info(conn) -> None:
    pid = conn.execute(text("SELECT pg_backend_pid()")).scalar()
    user = conn.execute(text("SELECT current_user")).scalar()
    db = conn.execute(text("SELECT current_database()")).scalar()
    print(f"[INFO] connected DB={db}, user={user}, pid={pid}")


# =========================================================
# SESSION TERMINATION
# =========================================================

def get_other_sessions(conn):
    sql = text("""
        SELECT pid, usename, application_name, state, query
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND pid <> pg_backend_pid()
    """)
    return conn.execute(sql).mappings().all()


def terminate_other_sessions(conn) -> int:
    sql = text("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = current_database()
          AND pid <> pg_backend_pid()
    """)
    res = conn.execute(sql).fetchall()
    print(f"[INFO] 종료 요청 세션 수 = {len(res)}")
    return len(res)


def wait_until_sessions_gone(conn) -> None:
    for i in range(1, TERMINATE_RETRY_COUNT + 1):
        rows = get_other_sessions(conn)
        if not rows:
            print("[INFO] 다른 세션 모두 종료됨")
            return

        print(f"[WARN] 아직 남은 세션 {len(rows)}개 (retry {i}/{TERMINATE_RETRY_COUNT})")
        terminate_other_sessions(conn)
        conn.commit()
        time.sleep(TERMINATE_SLEEP_SEC)

    rows = get_other_sessions(conn)
    if rows:
        raise RuntimeError("일부 DB 세션이 끝까지 종료되지 않았습니다.")


# =========================================================
# RESET LOGIC (Fast ETL 기준)
# =========================================================

def reset_mtba_fast_etl(conn) -> None:
    """
    Fast Incremental ETL 전용 초기화
    """

    print("[STEP] FACT TABLES 초기화")
    truncate_if_exists(conn, "mtba.fact_alarm_detail_daily")
    truncate_if_exists(conn, "mtba.fact_alarm_daily")
    truncate_if_exists(conn, "mtba.fact_runtime_daily")
    truncate_if_exists(conn, "mtba.fact_production_daily")

    print("[STEP] DIM TABLES 초기화")
    truncate_if_exists(conn, "mtba.dim_alarm")
    truncate_if_exists(conn, "mtba.dim_equipment")
    truncate_if_exists(conn, "mtba.dim_model")
    truncate_if_exists(conn, "mtba.dim_process")
    truncate_if_exists(conn, "mtba.dim_plant")
    truncate_if_exists(conn, "mtba.model_family_map")
    truncate_if_exists(conn, "mtba.model_family")

    print("[STEP] WATERMARK / ETL META 초기화")
    truncate_if_exists(conn, "mtba.etl_source_watermark")
    truncate_if_exists(conn, "mtba.etl_job_run_log")

    if RESET_USER_TABLES:
        print("[STEP] USER INPUT TABLES 초기화")
        truncate_if_exists(conn, "mtba.report_image")
        truncate_if_exists(conn, "mtba.report_note")
        truncate_if_exists(conn, "mtba.alarm_annotation")

    conn.commit()

    print("[STEP] MATERIALIZED VIEW REFRESH")
    refresh_mv_if_exists(conn, "mtba.mv_equipment_model_daily")
    refresh_mv_if_exists(conn, "mtba.mv_mtba_weekly_equipment")
    refresh_mv_if_exists(conn, "mtba.mv_mtba_weekly_process_stats")
    refresh_mv_if_exists(conn, "mtba.mv_alarm_weekly_equipment_detail")
    conn.commit()


# =========================================================
# MAIN
# =========================================================

def main():
    with engine.connect() as conn:
        print("=" * 90)
        print("[INFO] MTBA DB 강제 초기화 (Fast ETL 전용)")
        print("=" * 90)
        print_connection_info(conn)

        print("\n[1] 다른 DB 세션 종료")
        terminate_other_sessions(conn)
        conn.commit()

        wait_until_sessions_gone(conn)

        print("\n[2] Fast ETL 테이블 초기화")
        reset_mtba_fast_etl(conn)

        print("\n[3] 초기화 완료 확인")
        remaining = get_other_sessions(conn)
        print(f"[INFO] 남은 세션 수 = {len(remaining)}")

        print("=" * 90)
        print("[INFO] MTBA DB 초기화 완료 (Fast ETL 기준)")
        print("=" * 90)


if __name__ == "__main__":
    main()