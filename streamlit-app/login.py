import streamlit as st
import psycopg2
import bcrypt
import random
import win32com.client
import pythoncom
import time
import re
import base64
from pathlib import Path
from ui.login_ui.styles import apply_global_styles
from ui.login_ui.layout import (
    render_top_brand,
    render_left_panel_background,
    render_auth_intro,
    render_identity_block,
    render_right_panels,
)

from datetime import datetime, timedelta
from tracking import (
    create_login_session,
    close_login_session
)


# ===============================
# Page Config (반드시 최상단)
# ===============================
st.set_page_config(
    page_title="설비생산성 분석 플랫폼",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# ==================================================
# 부서 목록 (회원가입 시 사용)
# ==================================================
DEPARTMENTS = [
    "선택하세요",
    "CM FOL생산기술팀",
    "CM MOL생산기술팀",
    "CM EOL생산기술팀",
    "CM Tele생산팀",
    "CM Wide생산팀",
    "DM 생산기술팀",
    "DM 생산팀",
    "Actuator생산팀",
    "MaxCapa팀",
    "광학사업부 기타",
    "본사 기타",
]


# ==================================================
# DB 연결
# ==================================================
def get_conn():
    return psycopg2.connect(
        host=st.secrets["db"]["host"],
        dbname=st.secrets["db"]["name"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        port=st.secrets["db"]["port"],
    )


# ==================================================
# 이미 가입된 이메일인지 확인
# ==================================================
def is_existing_user(email: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT 1 FROM users WHERE email=%s;",
        (email,)
    )

    exists = cur.fetchone() is not None

    cur.close()
    conn.close()
    return exists




# ==================================================
# 회사 이메일 도메인
# ==================================================
COMPANY_EMAIL_DOMAIN = "lginnotek.com"


def normalize_login_email(user_input: str) -> str:
    user_input = user_input.strip().lower()

    # 이미 이메일 형태면 그대로 사용
    if "@" in user_input:
        return user_input

    # 아이디만 입력한 경우 도메인 자동 추가
    return f"{user_input}@{COMPANY_EMAIL_DOMAIN}"


# ==================================================
# 허용 이메일 도메인
# ==================================================
ALLOWED_DOMAINS = [
    "lginnotek.com",
]


def is_allowed_email(email: str) -> bool:
    if "@" not in email:
        return False

    domain = email.split("@")[-1].lower()
    return domain in ALLOWED_DOMAINS


# ============================
# Session State 초기화
# ============================
if "signup_step" not in st.session_state:
    st.session_state.signup_step = 1

if "signup_email" not in st.session_state:
    st.session_state.signup_email = None

if "view" not in st.session_state:
    st.session_state.view = "login"

if "reset_email" not in st.session_state:
    st.session_state.reset_email = None

if "reset_step" not in st.session_state:
    st.session_state.reset_step = None

if "reset_done" not in st.session_state:
    st.session_state.reset_done = False

if "login_view" not in st.session_state:
    st.session_state.login_view = "home"

if "change_pw_done" not in st.session_state:
    st.session_state.change_pw_done = False

if "login" not in st.session_state:
    st.session_state.login = False

if "login_user_prefill" not in st.session_state:
    st.session_state.login_user_prefill = ""

if "login_user_input" not in st.session_state:
    st.session_state.login_user_input = ""

if "next_view" not in st.session_state:
    st.session_state.next_view = None

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "last_logged_page" not in st.session_state:
    st.session_state.last_logged_page = None

if "last_logged_time" not in st.session_state:
    st.session_state.last_logged_time = 0

if "role" not in st.session_state:
    st.session_state.role = "user"

if "selected_post_id" not in st.session_state:
    st.session_state.selected_post_id = None

# ==================================================
# 인증코드 정책
# ==================================================
MAX_AUTH_FAIL_COUNT = 5

# ==================================================
# 로그인 정책
# ==================================================
MAX_LOGIN_FAIL_COUNT = 5


# ==================================================
# 비밀번호 처리
# ==================================================
def validate_password(password: str, email: str) -> tuple[bool, str]:
    kinds = 0

    if re.search(r"[a-z]", password):
        kinds += 1
    if re.search(r"[A-Z]", password):
        kinds += 1
    if re.search(r"[0-9]", password):
        kinds += 1
    if re.search(r"[^\w]", password):
        kinds += 1

    length = len(password)

    # 길이 규칙
    if kinds >= 3 and length < 8:
        return False, "비밀번호는 3종류 이상 조합 시 최소 8자리 이상이어야 합니다."
    if kinds == 2 and length < 10:
        return False, "비밀번호는 2종류 조합 시 최소 10자리 이상이어야 합니다."
    if kinds < 2:
        return False, "비밀번호는 최소 2종류 이상 조합되어야 합니다."

    # 이메일 아이디 포함 금지
    email_id = email.split("@")[0].lower()
    if email_id in password.lower():
        return False, "비밀번호에 계정 아이디를 포함할 수 없습니다."

    # 연속 문자 / 숫자 금지
    forbidden_sequences = [
        "1234", "2345", "3456", "4567",
        "abcd", "bcde", "cdef",
        "qwer", "asdf", "zxcv"
    ]
    pw_lower = password.lower()
    for seq in forbidden_sequences:
        if seq in pw_lower:
            return False, "연속된 문자 또는 숫자는 사용할 수 없습니다."

    return True, ""


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def update_user_password(email, new_password):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users
        SET password_hash=%s,
            password_changed_at=NOW()
        WHERE email = %s;
        """,
        (hash_password(new_password), email)
    )

    conn.commit()
    cur.close()
    conn.close()


# ==================================================
# 인증코드 처리
# ==================================================
def generate_code():
    return str(random.randint(100000, 999999))


def save_auth_code(email, code):
    conn = get_conn()
    cur = conn.cursor()
    expires_at = datetime.now() + timedelta(minutes=10)

    cur.execute(
        """
        INSERT INTO email_auth_codes (email, code, expires_at, fail_count)
        VALUES (%s, %s, %s, 0) ON CONFLICT (email)
        DO
        UPDATE SET
            code=%s,
            expires_at=%s,
            fail_count=0;
        """,
        (email, code, expires_at, code, expires_at),
    )

    conn.commit()
    cur.close()
    conn.close()


def verify_auth_code(email, input_code):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT code, expires_at, fail_count
        FROM email_auth_codes
        WHERE email = %s;
        """,
        (email,),
    )

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return False, "인증 요청 내역이 없습니다"

    code, expires_at, fail_count = row

    # 실패 횟수 초과
    if fail_count >= MAX_AUTH_FAIL_COUNT:
        cur.close()
        conn.close()
        return False, "인증코드 실패 횟수를 초과했습니다. 새로 발급받으세요"

    # 만료
    if datetime.now() > expires_at:
        cur.close()
        conn.close()
        return False, "인증코드가 만료되었습니다"

    # 코드 불일치 → 실패 횟수 증가
    if input_code != code:
        cur.execute(
            """
            UPDATE email_auth_codes
            SET fail_count = fail_count + 1
            WHERE email = %s;
            """,
            (email,),
        )
        conn.commit()
        cur.close()
        conn.close()
        return False, f"인증 실패 ({fail_count + 1}/{MAX_AUTH_FAIL_COUNT})"

    # 성공 시 삭제
    cur.execute(
        "DELETE FROM email_auth_codes WHERE email=%s;",
        (email,),
    )
    conn.commit()
    cur.close()
    conn.close()
    return True, None


# ==================================================
# outlook COM 방식 메일 발송
# ==================================================
def send_auth_email(to_email, code):
    """
    인증코드 메일 발송 (Outlook COM 방식)
    - Streamlit 스레드 환경 대응
    - 공용 계정 maxcapa@lginnotek.com 로그인된 Outlook 사용
    """
    try:
        pythoncom.CoInitialize()

        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)

        mail.To = to_email
        mail.Subject = "[설비 생산성 분석 플랫폼] 회원가입 인증코드"
        mail.Body = f"""설비 생산성 분석 플랫폼 회원가입 인증코드입니다.

인증코드: {code}
유효시간: 10분

본 메일은 자동 발송 메일입니다.
"""
        mail.Send()

    except Exception as e:
        st.error("메일 발송에 실패했습니다. Outlook/계정 상태를 확인하세요.")
        raise e

    finally:
        pythoncom.CoUninitialize()


# ==================================================
# 사용자 처리
# ==================================================
def create_user(email, password, department):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users (email, password_hash, department, is_verified)
        VALUES (%s, %s, %s, TRUE) ON CONFLICT (email) DO NOTHING;
        """,
        (email, hash_password(password), department),
    )

    if cur.rowcount == 0:
        conn.rollback()
        cur.close()
        conn.close()
        return False

    conn.commit()
    cur.close()
    conn.close()
    return True


def login_user(email, password):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT password_hash,
               department,
               role,
               login_fail_count,
               password_changed_at
        FROM users
        WHERE email = %s
          AND is_verified = TRUE;
        """,
        (email,),
    )

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return False, "이메일 또는 비밀번호 오류"

    password_hash, department, role, fail_count, password_changed_at = row

    # 실패 횟수 초과 시 차단
    if fail_count >= MAX_LOGIN_FAIL_COUNT:
        cur.close()
        conn.close()
        return False, "로그인 실패 횟수를 초과했습니다. 관리자에게 문의하세요"

    # 비밀번호 불일치 → 실패 횟수 증가
    if not verify_password(password, password_hash):
        cur.execute(
            """
            UPDATE users
            SET login_fail_count = login_fail_count + 1
            WHERE email = %s;
            """,
            (email,),
        )
        conn.commit()
        cur.close()
        conn.close()

        return False, f"로그인 실패 ({fail_count + 1}/{MAX_LOGIN_FAIL_COUNT})"

    # 로그인 성공 → 실패 횟수 초기화
    cur.execute(
        """
        UPDATE users
        SET login_fail_count = 0
        WHERE email = %s;
        """,
        (email,),
    )

    days = (datetime.now() - password_changed_at).days
    password_expired = days >= 90

    conn.commit()
    cur.close()
    conn.close()

    return True, {
        "department": department,
        "role": role,
        "password_expired": password_expired
    }

# ==================================================
# 비밀번호 변경
# ==================================================
def render_change_password():
    st.subheader("🔑 비밀번호 변경")

    if st.session_state.change_pw_done:
        st.success("✅ 비밀번호 변경이 완료되었습니다.")
        st.info("잠시 후 이전 화면으로 이동합니다.")
        time.sleep(2)

        st.session_state.change_pw_done = False
        st.session_state.login_view = "home"
        st.rerun()

    current_pw = st.text_input(
        "현재 비밀번호",
        type="password",
        key="change_pw_current"
    )

    new_pw1 = st.text_input(
        "새 비밀번호",
        type="password",
        key="change_pw_new1"
    )

    new_pw2 = st.text_input(
        "새 비밀번호 확인",
        type="password",
        key="change_pw_new2"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("변경 적용", key="change_pw_submit"):
            ok, _ = login_user(
                st.session_state.user_email,
                current_pw
            )

            if not ok:
                st.error("현재 비밀번호가 올바르지 않습니다.")
            elif new_pw1 != new_pw2:
                st.error("새 비밀번호가 일치하지 않습니다.")
            else:
                ok, msg = validate_password(
                    new_pw1,
                    st.session_state.user_email
                )
                if not ok:
                    st.error(msg)
                else:
                    update_user_password(
                        st.session_state.user_email,
                        new_pw1
                    )
                    st.session_state.change_pw_done = True
                    st.rerun()

    with col2:
        if st.button("취소", key="change_pw_cancel"):
            st.session_state.login_view = "home"
            st.rerun()


# --------------------------------------------------
# 로그인 상태
# --------------------------------------------------
if st.session_state.login:
    st.success(f"✅ 로그인: {st.session_state.user_email}")
    st.write(f"부서: **{st.session_state.department}**")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("🔑 비밀번호 변경"):
            st.session_state.login_view = "change_password"
            st.rerun()

    with col2:
        if st.button("🚪 로그아웃"):
            # 로그인 세션 종료
            if st.session_state.get("session_id"):
                close_login_session(st.session_state.session_id, reason="logout")


            st.session_state.login = False
            st.session_state.session_id = None
            st.session_state.last_logged_page = None
            st.session_state.last_logged_time = 0
            st.session_state.role = "user"
            st.session_state.selected_post_id = None

            st.session_state.view = "login"
            st.session_state.login_view = "home"
            st.session_state.signup_step = 1
            st.session_state.signup_email = None
            st.session_state.reset_email = None
            st.session_state.reset_step = None
            st.session_state.reset_done = False
            st.session_state.change_pw_done = False
            st.session_state.login_user_prefill = ""
            st.session_state.login_user_input = ""

            st.rerun()

    st.divider()

    if st.session_state.login_view == "home":
        st.info("👉 여기서 기존 UPH / MTBA 화면 호출")
    elif st.session_state.login_view == "change_password":
        render_change_password()

    st.stop()


# --------------------------------------------------
# 로그인 화면
# --------------------------------------------------
def render_login():
    with st.form(key="login_form", clear_on_submit=False):
        # 회원가입 완료 후 전달된 메일 자동 입력
        if st.session_state.login_user_prefill:
            st.session_state.login_user_input = st.session_state.login_user_prefill
            st.session_state.login_user_prefill = ""

        user_id = st.text_input(
            "아이디",
            key="login_user_input"
        )
        password = st.text_input(
            "비밀번호",
            type="password",
            key="login_pw"
        )

        submitted = st.form_submit_button(
            "로그인",
            use_container_width=True
        )

        if submitted:
            email = normalize_login_email(user_id)

            ok, result = login_user(email, password)

            if ok:
                st.session_state.login = True
                st.session_state.user_email = email
                st.session_state.department = result["department"]
                st.session_state.role = result["role"]

                # 로그인 세션 생성
                session_id = create_login_session(email, result["department"])
                st.session_state.session_id = session_id
                st.session_state.last_logged_page = None
                st.session_state.last_logged_time = 0

                if result["password_expired"]:
                    st.warning(
                        "🔒 비밀번호 사용 기간이 90일을 초과했습니다. 변경이 필요합니다."
                    )
                    st.session_state.login_view = "change_password"
                else:
                    st.switch_page("pages/0_Home.py")

                st.rerun()
            else:
                st.error(result)

    # 비밀번호 찾기 버튼을 살짝 오른쪽으로 배치
    left_spacer, button_col = st.columns([0.01, 0.99])
    with button_col:
        if st.button("비밀번호를 잊으셨나요?", key="goto_reset", type="secondary"):
            st.session_state.view = "reset_password"
            st.rerun()


# --------------------------------------------------
# 회원가입 화면
# --------------------------------------------------
def render_signup():
    left_spacer, main_col, right_spacer = st.columns([0.01, 0.96, 0.03])

    with main_col:
        st.caption("회사 이메일 인증 후 가입 가능합니다.")

        email = st.text_input(
            "회사 이메일",
            value=st.session_state.signup_email if st.session_state.signup_email else "",
            key="signup_email_input"
        )

        # STEP 1: 이메일 입력 + 인증코드 발송
        if st.button("인증코드 발송", key="signup_send_code_btn"):
            email = email.strip().lower()

            if not email:
                st.error("이메일을 입력하세요.")
            elif not is_allowed_email(email):
                st.error("회사 이메일만 가능합니다.")
            elif is_existing_user(email):
                st.error("이미 가입된 계정입니다. 로그인하세요.")
            else:
                code = generate_code()
                save_auth_code(email, code)
                send_auth_email(email, code)

                st.session_state.signup_email = email
                st.session_state.signup_step = 2

                st.success("✅ 인증코드가 이메일로 발송되었습니다.")
                st.rerun()

        # STEP 2: 인증코드 입력
        if st.session_state.signup_step >= 2:
            code_input = st.text_input(
                "인증코드 입력",
                key="signup_code_input"
            )

            if st.button("인증 확인", key="signup_verify_btn"):
                ok, msg = verify_auth_code(
                    st.session_state.signup_email,
                    code_input
                )
                if ok:
                    st.session_state.signup_step = 3
                    st.success("✅ 이메일 인증이 완료되었습니다.")
                    st.rerun()
                else:
                    st.error(msg)

        # STEP 3: 비밀번호 설정
        if st.session_state.signup_step >= 3:
            pw1 = st.text_input("비밀번호", type="password", key="signup_pw1")
            pw2 = st.text_input("비밀번호 확인", type="password", key="signup_pw2")
            dept = st.selectbox("부서 선택", DEPARTMENTS, key="signup_dept")

            if st.button("회원가입 완료", key="signup_done_btn"):
                if pw1 != pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif dept == "선택하세요":
                    st.error("부서를 선택하세요.")
                else:
                    ok, msg = validate_password(
                        pw1,
                        st.session_state.signup_email
                    )
                    if not ok:
                        st.error(msg)
                    else:
                        created = create_user(
                            st.session_state.signup_email,
                            pw1,
                            dept
                        )

                        if not created:
                            st.error("이미 가입된 계정입니다. 로그인하세요.")
                        else:
                            st.success("✅ 가입이 완료되었습니다. 로그인 해주세요.")
                            st.info("잠시 후 로그인 화면으로 이동합니다.")
                            time.sleep(1.5)

                            # 가입된 메일을 로그인창에 자동 입력
                            signed_email = st.session_state.signup_email

                            if "login_user_input" in st.session_state:
                                del st.session_state["login_user_input"]

                            st.session_state.login_user_prefill = signed_email

                            # 상태 초기화 + 로그인 화면 이동
                            st.session_state.signup_step = 1
                            st.session_state.signup_email = None
                            st.session_state.next_view = "login"
                            st.rerun()

# --------------------------------------------------
# 비밀번호 재설정 화면
# --------------------------------------------------
def render_reset_password():
    left_spacer, main_col, right_spacer = st.columns([0.01, 0.96, 0.03])

    with main_col:
        st.subheader("비밀번호 재설정")

        if st.button("로그인으로 돌아가기", key="back_to_login_btn"):
            st.session_state.view = "login"
            st.session_state.reset_step = None
            st.session_state.reset_done = False
            st.rerun()

        email = st.text_input("회사 이메일", key="reset_email_input")

        if st.button("인증코드 발송", key="send_code2_btn"):
            email = email.strip().lower()

            if not is_existing_user(email):
                st.error("가입되지 않은 이메일입니다.")
            else:
                code = generate_code()
                save_auth_code(email, code)
                send_auth_email(email, code)
                st.session_state.reset_email = email
                st.session_state.reset_step = 2
                st.success("인증코드를 발송했습니다.")
                st.rerun()

        if st.session_state.get("reset_step") == 2:
            code_input = st.text_input("인증코드", key="reset_code_input")
            if st.button("인증 확인", key="reset_verify_btn"):
                ok, msg = verify_auth_code(st.session_state.reset_email, code_input)
                if ok:
                    st.session_state.reset_step = 3
                    st.rerun()
                else:
                    st.error(msg)

        if st.session_state.get("reset_step") == 3:
            pw1 = st.text_input("새 비밀번호", type="password", key="reset_pw1")
            pw2 = st.text_input("새 비밀번호 확인", type="password", key="reset_pw2")
            if st.button("비밀번호 변경", key="reset_change_btn"):
                if pw1 != pw2:
                    st.error("비밀번호 불일치")
                else:
                    ok, msg = validate_password(
                        pw1,
                        st.session_state.reset_email
                    )
                    if not ok:
                        st.error(msg)
                    else:
                        update_user_password(st.session_state.reset_email, pw1)
                        st.session_state.reset_done = True
                        st.rerun()

        if st.session_state.reset_done:
            st.success("✅ 비밀번호 변경이 완료되었습니다.")
            st.info("잠시 후 로그인 화면으로 이동합니다.")
            time.sleep(2)

            # 재설정한 메일도 로그인 입력창에 자동 주입
            reset_email = st.session_state.reset_email

            if "login_user_input" in st.session_state:
                del st.session_state["login_user_input"]

            st.session_state.login_user_prefill = reset_email

            st.session_state.reset_done = False
            st.session_state.reset_step = None
            st.session_state.reset_email = None
            st.session_state.next_view = "login"
            st.rerun()

def get_recent_patch_posts(limit=4):
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, tag, title, created_at
            FROM board_posts
            WHERE category = 'patch'
              AND is_published = TRUE
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (limit,)
        )

        rows = cur.fetchall()
        return rows

    except Exception:
        return []

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_board_posts(category="patch"):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, category, tag, title, created_by, created_at
        FROM board_posts
        WHERE category = %s
          AND is_published = TRUE
        ORDER BY created_at DESC;
        """,
        (category,)
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_board_post_detail(post_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, category, tag, title, content, created_by, created_at, updated_at
        FROM board_posts
        WHERE id = %s
          AND is_published = TRUE;
        """,
        (post_id,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def create_board_post(category, tag, title, content, created_by):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO board_posts (category, tag, title, content, created_by)
        VALUES (%s, %s, %s, %s, %s);
        """,
        (category, tag, title, content, created_by)
    )

    conn.commit()
    cur.close()
    conn.close()

def render_image_background():
    """
    페이지 전체 배경 이미지 렌더링
    - img/bgi.png 사용
    - 화면 크기에 따라 cover
    - 중앙 기준 정렬
    - 남는 영역은 검정색
    """
    BASE_DIR = Path(__file__).resolve().parent
    img_path = BASE_DIR / "img" / "bgi.png"

    if not img_path.exists():
        st.warning(f"배경 이미지 파일을 찾을 수 없습니다: {img_path}")
        return

    with open(img_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
        html, body {{
            background: #1F2430 !important;
        }}

        .stApp {{
            background-color: #1F2430 !important;
            background-image: url("data:image/png;base64,{encoded}") !important;
            background-repeat: no-repeat !important;
            background-position: center center !important;
            background-size: cover !important;
            background-attachment: fixed !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}

        .main {{
            background: transparent !important;
        }}

        .main .block-container {{
            background: transparent !important;
        }}

        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def render_video_background():
    """
    페이지 전체 배경 동영상 렌더링
    - img/bgi.mp4 사용
    - 화면 크기에 따라 cover
    - 중앙 기준 정렬
    - 남는 영역은 검정색
    - 자동재생 / 음소거 / 반복
    - 검정 반투명 오버레이 적용
    """
    BASE_DIR = Path(__file__).resolve().parent
    video_path = BASE_DIR / "img" / "bgi.mp4"

    if not video_path.exists():
        st.warning(f"배경 동영상 파일을 찾을 수 없습니다: {video_path}")
        return

    with open(video_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <style>
        html, body {{
            background: #1F2430 !important;
        }}

        .stApp {{
            background: transparent !important;
        }}

        [data-testid="stAppViewContainer"] {{
            background: transparent !important;
        }}

        .main {{
            background: transparent !important;
        }}

        .main .block-container {{
            background: transparent !important;
        }}

        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        .video-background-wrap {{
            position: fixed;
            inset: 0;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
            background: #1F2430;
            z-index: -9999;
            pointer-events: none;
        }}

        .video-background-wrap video {{
            position: absolute;
            top: 50%;
            left: 50%;
            min-width: 100%;
            min-height: 100%;
            width: auto;
            height: auto;
            transform: translate(-50%, -50%);
            object-fit: cover;
            background: #1F2430;
        }}

        .video-background-overlay {{
            position: absolute;
            inset: 0;
            background: rgba(0, 0, 0, 0.65);
        }}
        </style>

        <div class="video-background-wrap">
            <video id="vit-bg-video" autoplay muted loop playsinline preload="auto">
                <source src="data:video/mp4;base64,{encoded}" type="video/mp4">
            </video>
            <div class="video-background-overlay"></div>
        </div>

        <script>
        // 탭 전환 / 앱 백그라운드 후 복귀 시 자동 재개 + 매 3초 안전망
        // (모바일 브라우저 자동재생 정책 우회 — muted + playsinline 필수)
        (function() {{
            function safePlay() {{
                var v = document.getElementById('vit-bg-video');
                if (!v) return;
                v.muted = true;
                if (v.paused) {{
                    var p = v.play();
                    if (p && p.catch) p.catch(function(){{}});
                }}
            }}
            document.addEventListener('visibilitychange', function() {{
                if (!document.hidden) safePlay();
            }});
            window.addEventListener('focus', safePlay);
            window.addEventListener('pageshow', safePlay);
            // 사용자 첫 제스처에 무조건 재생 (자동재생 막힐 때 백업)
            ['touchstart','pointerdown','click','keydown','scroll'].forEach(function(ev) {{
                document.addEventListener(ev, safePlay, {{ passive: true }});
            }});
            // 안전망 — 페이지 표시 중일 때 3초마다 idempotent 재생 호출
            setInterval(function() {{
                if (!document.hidden) safePlay();
            }}, 3000);
        }})();
        </script>
        """,
        unsafe_allow_html=True
    )

# --------------------------------------------------
# 로그인 / 회원가입 / 비밀번호재설정 공통 카드
# --------------------------------------------------
apply_global_styles()
render_video_background()
#render_image_background()
render_top_brand()

left_col, _, right_col = st.columns([0.35, 0.20, 0.45])

with left_col:
    render_left_panel_background()

    with st.container():
        render_auth_intro()

        if st.session_state.next_view is not None:
            st.session_state.view = st.session_state.next_view
            st.session_state.next_view = None

        if st.session_state.view == "reset_password":
            render_reset_password()
        else:
            menu = st.radio(
                "auth_tab",
                options=["login", "signup"],
                index=0 if st.session_state.view == "login" else 1,
                format_func=lambda x: "로그인" if x == "login" else "회원가입",
                horizontal=True,
                label_visibility="collapsed",
                key=f"auth_tab_radio_{st.session_state.view}"
            )

            if menu != st.session_state.view:
                st.session_state.view = menu
                st.rerun()

            if st.session_state.view == "login":
                render_login()
            else:
                render_signup()

    render_identity_block()

recent_patch_posts = get_recent_patch_posts(limit=4)

with right_col:
    render_right_panels(recent_patch_posts)