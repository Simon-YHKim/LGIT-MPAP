import streamlit as st

# Vitals 디자인 시스템 진입점 — 와인 팔레트 + LG EI 폰트 + Streamlit 기본 hide.
# apply_global_styles() 호출 시 자동으로 vitals 테마가 먼저 적용된 뒤
# 그 위에 로그인 페이지 전용 다크 오버레이가 깔린다.
from ui.vitals import apply_vitals_theme


def apply_global_styles():
    # 1) Vitals 글로벌 (LG EI 폰트 base64 임베드, 와인 팔레트, 사이드바 hide) 먼저
    apply_vitals_theme()

    # 2) 로그인 페이지 전용 오버레이 — 다크 비디오 배경 위 흰 카드 톤
    st.markdown(
        """
        <style>
        /* 로그인 페이지에서만 사이드바·collapsed 컨트롤 hide
           (다른 페이지는 vitals 테마가 사이드바를 표시 — 페이지 이동에 사용) */
        [data-testid="stSidebar"],
        section[data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        /* :root 토큰은 vitals 테마에서 모두 정의됨. 여기선 페이지 전용 추가만.
           — Vitals 토큰 (--page-bg, --card-bg, --border, --soft, --ink-body 등)
             는 vitals 테마에서 이미 :root 에 정의되어 있어 여기서 직접 참조 가능. */
        :root {
            --on-dark:#FFFFFF;
            --on-dark-muted:rgba(255,255,255,0.76);
            --on-dark-subtle:rgba(255,255,255,0.56);
            --panel-dark:rgba(12,14,18,0.68);
            --panel-border-dark:rgba(255,255,255,0.10);
        }

        /* Vitals 토큰 — 우측 로그인 카드(light) 영역 명시적 사용 */
        .auth-card,
        .signup-card,
        .login-card {
            background: var(--card-bg, #FFFFFF) !important;
            border: 1px solid var(--border, #E5E7EB) !important;
            color: var(--ink-body, #1F2430) !important;
        }
        .auth-card label,
        .login-card label {
            color: var(--ink-muted, #6B7280) !important;
        }
        .auth-card input,
        .login-card input {
            background: var(--soft, #F1F3F5) !important;
            border: 1px solid var(--border, #E5E7EB) !important;
            color: var(--ink-body, #1F2430) !important;
        }
        /* page-head — 우리회사 LGIT 로고 + 캐치프레이즈 영역 마커 */
        .vit-page-head, .login-vit-head {
            color: var(--on-dark);
        }
        /* status 시맨틱 — 회원가입 폼 검증 메시지에서 사용 */
        .auth-status-good { color: var(--status-good, #1F8B4C) !important; }
        .auth-status-warn { color: var(--status-warn, #B57F1B) !important; }
        .auth-status-bad  { color: var(--status-bad,  #B23A48) !important; }

        /* 폰트 — vitals 의 LG EI 스택을 페이지 전체에 강제 적용 */
        html, body, [class*="css"] {
            font-family: var(--font-body) !important;
        }

        .stApp {
            background: transparent !important;
            color: var(--on-dark);
        }

        /* 상단 Streamlit 헤더와 겹치지 않도록 여백 */
        .block-container {
            /* 사용자 피드백 (2026-05-08): 로그인 좌우 분리 (4:3 → 16:9).
               max-width 1380 → 100% 풀폭. padding 좌우 80px 로 spread. */
            padding-top: 2.5rem !important;
            padding-bottom: 1.2rem !important;
            padding-left: 80px !important;
            padding-right: 80px !important;
            max-width: 100% !important;
        }

        /* 상단 브랜드 */
        .landing-topbar {
            display:flex;
            align-items:center;
            justify-content:space-between;
            margin-bottom: 30px;
            padding-top: 4px;
        }

        .landing-brand {
            display:flex;
            align-items:center;
            gap:12px;
            color: var(--on-dark);
            flex-wrap: wrap;
        }

        .landing-brand__name {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.01em;
            white-space: nowrap;
        }

        .landing-brand__divider {
            width:1px;
            height:16px;
            background:rgba(255,255,255,0.22);
            flex: 0 0 auto;
        }

        .landing-brand__team {
            font-size: 12px;
            color: var(--on-dark-subtle);
            letter-spacing: .08em;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .landing-status {
            font-size: 11px;
            color: var(--on-dark-muted);
            letter-spacing: .08em;
            text-transform: uppercase;
            white-space: nowrap;
        }

        .left-panel-bg {
            position: absolute;
            top: 36px;
            left: 0;
            width: 100%;
            height: 548px;
            /* Vitals 'rectangles only' — left-panel-bg 도 직사각형. */
            background: linear-gradient(
                180deg,
                rgba(255,255,255,0.075) 0%,
                rgba(255,255,255,0.035) 100%
            );
            border: 1px solid rgba(255,255,255,0.10);
            box-shadow:
                0 18px 42px rgba(0,0,0,0.26),
                inset 0 1px 0 rgba(255,255,255,0.05);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            pointer-events: none;
            z-index: 0;
        }

        /* 왼쪽 컬럼 안 요소가 배경판 위로 올라오게 */
        [data-testid="column"] {
            position: relative;
            z-index: 1;
        }

        /* 왼쪽 인증영역 내부 여백 */
        [data-testid="column"] > div > div:has(.auth-eyebrow) {
            padding: 30px 72px 12px 72px;
            max-width: 560px;
        }

        /* intro */
        .auth-eyebrow {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .09em;
            color: rgba(255,255,255,0.62);
            margin-bottom: 10px;
            padding-left: 2px;
            position: relative;
        }

        .auth-eyebrow::before {
            content: "";
            display: inline-block;
            width: 32px;
            height: 3px;
            background: var(--primary);
            /* Vitals 'rectangles only' — wine accent bar 도 직각. */
            margin-right: 10px;
            vertical-align: middle;
        }

        .auth-title {
            margin: 0 0 6px;
            font-size: 24px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.02em;
        }

        .auth-sub {
            margin: 0 0 20px;
            font-size: 13px;
            color: rgba(255,255,255,0.74);
            line-height: 1.55;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255,255,255,0.09);
        }

        /* 탭 */
        div[data-testid="stRadio"] {
            margin-bottom: 10px;
        }

        div[data-testid="stRadio"] > div {
            display: flex;
            justify-content: center;
            gap: 0;
            margin-top: 2px;
            margin-bottom: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.10);
            padding-bottom: 0;
            flex-wrap: nowrap !important;
        }

        div[data-testid="stRadio"] label {
            flex: 1 1 0;
            min-width: 0;
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            margin: 0 !important;
            min-height: auto !important;
        }

        div[data-testid="stRadio"] label > div:first-child {
            display: none !important;
        }

        div[data-testid="stRadio"] input[type="radio"] {
            display: none !important;
            visibility: hidden !important;
            position: absolute !important;
        }

        div[data-testid="stRadio"] label p {
            text-align: center;
            font-size: 14px !important;
            font-weight: 700 !important;
            color: rgba(255,255,255,0.58) !important;
            margin: 0 !important;
            padding: 12px 6px !important;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
            white-space: nowrap !important;
            word-break: keep-all !important;
            line-height: 1.2 !important;
        }

        div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div p {
            color: #ffffff !important;
            border-bottom: 2px solid var(--primary) !important;
        }

        div[data-testid="stRadio"] label:hover p {
            color: rgba(255,255,255,0.88) !important;
        }

        /* 입력 — Vitals 'rectangles only' */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div {
            border-radius: 0 !important;
            border: 1px solid rgba(255,255,255,0.08) !important;
            background: rgba(255,255,255,0.94) !important;
            box-shadow: 0 6px 16px rgba(0,0,0,0.12) !important;
        }

        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="select"] > div:focus-within {
            border-color: rgba(165,0,52,0.52) !important;
            box-shadow: 0 0 0 3px rgba(165,0,52,0.16) !important;
        }

        div[data-baseweb="input"] input {
            color: var(--ink-body) !important;
            font-weight: 500 !important;
        }

        /* 라벨 */
        label, .stTextInput label, .stSelectbox label {
            color: rgba(255,255,255,0.92) !important;
            font-weight: 600 !important;
        }

        [data-testid="stCaptionContainer"] {
            margin-bottom: 0.55rem;
            color: rgba(255,255,255,0.64) !important;
        }

        /* 버튼 — Vitals 'rectangles only' */
        .stButton > button,
        .stFormSubmitButton > button {
            border-radius: 0 !important;
            font-weight: 700 !important;
            min-height: 44px !important;
            transition: all 0.18s ease !important;
        }

        .stFormSubmitButton {
            margin-top: 10px;
        }

        /* 메인 CTA */
        .stFormSubmitButton button,
        div[data-testid="stFormSubmitButton"] button {
            width: 100% !important;
            background: linear-gradient(180deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(165,0,52,0.95) !important;
            box-shadow: 0 12px 28px rgba(165, 0, 52, 0.30) !important;
            letter-spacing: -0.01em;
        }

        .stFormSubmitButton button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            background: var(--primary-dark) !important;
            color: #ffffff !important;
            border: 1px solid var(--primary-dark) !important;
            transform: translateY(-1px);
            box-shadow: 0 16px 30px rgba(165, 0, 52, 0.34) !important;
        }

        .stFormSubmitButton button:focus,
        .stFormSubmitButton button:active,
        div[data-testid="stFormSubmitButton"] button:focus,
        div[data-testid="stFormSubmitButton"] button:active {
            background: var(--primary-dark) !important;
            color: #ffffff !important;
            border: 1px solid var(--primary-dark) !important;
            box-shadow: 0 0 0 0.2rem rgba(165, 0, 52, 0.22) !important;
        }

        /* 일반 버튼 */
        .stButton > button {
            background: rgba(255,255,255,0.06) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255,255,255,0.14) !important;
        }

        .stButton > button:hover {
            background: rgba(255,255,255,0.10) !important;
            border-color: rgba(255,255,255,0.22) !important;
        }

        /* 링크 버튼 */
        div[data-testid="stButton"] > button[kind="secondary"] {
            width: 100% !important;
            background: transparent !important;
            border: none !important;
            color: rgba(255,255,255,0.92) !important;
            padding: 0 !important;
            margin: 0 !important;
            min-height: 22px !important;
            height: auto !important;
            line-height: 1.25 !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            text-decoration: none !important;
            box-shadow: none !important;
            justify-content: flex-start !important;
            text-align: left !important;
            display: flex !important;
            align-items: center !important;
        }
        
        div[data-testid="stButton"] > button[kind="secondary"] * {
            text-align: left !important;
            justify-content: flex-start !important;
        }
        
        div[data-testid="stButton"] > button[kind="secondary"] p,
        div[data-testid="stButton"] > button[kind="secondary"] span,
        div[data-testid="stButton"] > button[kind="secondary"] div {
            text-align: left !important;
            width: 100% !important;
            margin: 0 !important;
        }
        
        div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background: transparent !important;
            color: #ffffff !important;
            text-decoration: underline !important;
        }
        
       


        /* 알림 — Vitals 'rectangles only' */
        [data-testid="stAlert"] {
            border-radius: 0;
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }

        /* 왼쪽 브랜딩 */
        .identity-block {
            margin-top: 34px;
            padding-left: 28px;
            padding-right: 20px;
        }
        
        .patch-row-title a {
            color: rgba(255,255,255,0.92);
            text-decoration: none;
            font-size: 12px;
            font-weight: 500;
            display: block;
            text-align: left;
            word-break: keep-all;
            line-height: 1.25;
        }
        
        .patch-row-title a:hover {
            color: #ffffff;
            text-decoration: underline;
        }


        .identity-name {
            margin: 0;
            font-size: 58px;
            font-weight: 800;
            line-height: 0.96;
            color: var(--on-dark);
            letter-spacing: -0.05em;
            text-shadow: 0 6px 24px rgba(0,0,0,0.24);
        }

        .identity-name .dot {
            color: var(--primary);
        }

        .identity-sub {
            margin: 16px 0 0;
            font-size: 18px;
            font-weight: 500;
            color: var(--on-dark);
            line-height: 1.45;
            opacity: 0.92;
            text-shadow: 0 4px 16px rgba(0,0,0,0.18);
        }

        .identity-bu {
            margin: 14px 0 0;
            font-size: 11px;
            color: var(--on-dark-subtle);
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        /* 오른쪽 패널 — Vitals 'rectangles only' */
        .side-panel {
            background: rgba(10,12,16,0.54);
            border: 1px solid rgba(255,255,255,0.10);
            padding: 15px 16px;
            color: var(--on-dark);
            margin-bottom: 14px;
            box-shadow:
                0 14px 30px rgba(0,0,0,0.18),
                inset 0 1px 0 rgba(255,255,255,0.04);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        .side-panel__head {
            display:flex;
            justify-content:space-between;
            align-items:center;
            margin-bottom: 10px;
        }

        .side-panel__title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .1em;
            color: var(--on-dark-muted);
        }

        .side-panel__hint {
            font-size: 10px;
            color: var(--on-dark-subtle);
            letter-spacing: .05em;
        }

        .status-item {
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap: 8px;
            padding: 8px 0;
            border-bottom: 1px dashed rgba(255,255,255,0.08);
            font-size: 13px;
        }

        .status-item:last-child {
            border-bottom: 0;
        }

        .status-left {
            display:flex;
            align-items:center;
            gap:10px;
        }

        .status-dot {
            width:7px;
            height:7px;
            border-radius:50%;
            background: var(--status-good);
            box-shadow: 0 0 0 3px rgba(31,139,76,0.18);
        }

        .status-dot.warn {
            background: var(--status-warn);
            box-shadow: 0 0 0 3px rgba(181,127,27,0.18);
        }

        .status-dot.bad {
            background: var(--status-bad);
            box-shadow: 0 0 0 3px rgba(178,58,72,0.20);
        }

        .status-label {
            color: var(--on-dark);
            font-weight: 600;
        }

        .status-detail {
            font-size: 11px;
            color: var(--on-dark-subtle);
        }

        .patch-item {
            padding: 8px 0;
            border-bottom: 1px dashed rgba(255,255,255,0.08);
            font-size: 12px;
            color: var(--on-dark);
            line-height: 1.5;
        }

        .patch-item:last-child {
            border-bottom: 0;
        }

        .patch-date {
            display:inline-block;
            width: 54px;
            color: var(--on-dark-muted);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .05em;
        }

        .patch-tag {
            display:inline-block;
            margin-right: 6px;
            padding: 1px 5px;
            /* Vitals 'rectangles only' — wine pill 도 직각. */
            background: rgba(165,0,52,0.25);
            border: 1px solid rgba(165,0,52,0.4);
            color: #fff;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .05em;
        }

        @media (max-width: 1100px) {
            .landing-topbar {
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }
        }

        @media (max-width: 980px) {
            .block-container {
                padding-top: 5rem !important;
            }

            .identity-name {
                font-size: 42px;
            }

            .identity-sub {
                font-size: 15px;
            }

            [data-testid="column"] > div > div:has(.auth-eyebrow) {
                padding: 24px 30px 10px 30px;
                max-width: 100%;
            }

            .left-panel-bg {
                height: 530px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )