import os
import sqlite3
from datetime import datetime

import streamlit as st

DB_PATH = os.path.join(os.path.dirname(__file__), "access_log/access_logs.db")


def init_access_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_time TEXT NOT NULL,
                page_name TEXT NOT NULL,
                client_ip TEXT,
                forwarded_for TEXT,
                user_agent TEXT,
                host TEXT,
                url TEXT,
                session_key TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ip_counter (
                client_ip TEXT PRIMARY KEY,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_access_time TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()



def get_client_ip() -> str:
    """
    우선순위:
    1) Streamlit 공식 API의 st.context.ip_address
    2) reverse proxy 환경용 X-Forwarded-For / X-Real-IP 헤더 fallback
    """
    try:
        ip = st.context.ip_address
        if ip:
            return str(ip)
    except Exception:
        pass

    try:
        headers = st.context.headers
        xff = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()

        xri = headers.get("x-real-ip") or headers.get("X-Real-IP")
        if xri:
            return xri.strip()
    except Exception:
        pass

    return "UNKNOWN"



def _build_session_key(page_name: str) -> str:
    session_key_name = f"_access_session_key::{page_name}"
    session_key = st.session_state.get(session_key_name)
    if not session_key:
        session_key = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{page_name}_{id(st.session_state)}"
        st.session_state[session_key_name] = session_key
    return session_key



def log_page_access(page_name: str, db_path: str = DB_PATH):
    """
    각 페이지 스크립트 상단에서 1회 호출.
    같은 브라우저 세션에서 같은 페이지가 rerun되어도 중복 기록하지 않음.
    페이지별로 독립 플래그를 사용하므로, home -> subpage 이동 시 각각 1회 기록됨.
    """
    logged_flag = f"_access_logged::{page_name}"
    if st.session_state.get(logged_flag, False):
        return

    init_access_db(db_path)

    try:
        headers = st.context.headers
    except Exception:
        headers = {}

    client_ip = get_client_ip()
    forwarded_for = headers.get("x-forwarded-for", "") if headers else ""
    user_agent = headers.get("user-agent", "") if headers else ""
    host = headers.get("host", "") if headers else ""

    try:
        current_url = str(st.context.url)
    except Exception:
        current_url = ""

    session_key = _build_session_key(page_name)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            INSERT INTO access_log (
                access_time, page_name, client_ip, forwarded_for,
                user_agent, host, url, session_key
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (now, page_name, client_ip, forwarded_for, user_agent, host, current_url, session_key),
        )

        conn.execute(
            """
            INSERT INTO ip_counter (client_ip, access_count, last_access_time)
            VALUES (?, 1, ?)
            ON CONFLICT(client_ip)
            DO UPDATE SET
                access_count = access_count + 1,
                last_access_time = excluded.last_access_time
            """,
            (client_ip, now),
        )
        conn.commit()
        st.session_state[logged_flag] = True
    except Exception as e:
        print(f"[ACCESS_LOG_ERROR][{page_name}] {e}")
    finally:
        conn.close()
