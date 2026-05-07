import time
import streamlit as st

from tracking import log_page_view_once





def require_login(page_name: str = None, page_path: str = None, min_interval_sec: int = 5):

    if not st.session_state.get("login"):
        st.warning("로그인이 필요합니다. 잠시 후 로그인 페이지로 이동합니다.")
        time.sleep(1)
        st.switch_page("login.py")
        st.stop()

    # 로그인 상태면 페이지 조회 로그 기록
    if page_name:
        log_page_view_once(
            page_name=page_name,
            page_path=page_path,
            min_interval_sec=min_interval_sec
        )