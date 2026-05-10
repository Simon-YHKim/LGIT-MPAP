import streamlit as st

# Vitals 디자인 시스템 진입점 — 와인 팔레트 + LG EI 폰트 + Streamlit 기본 hide.
# apply_global_styles() 호출 시 자동으로 vitals 테마가 먼저 적용된 뒤
# 그 위에 로그인 페이지 전용 다크 오버레이가 깔린다.
# apply_vitals_theme 가 내부적으로 apply_clone_styles 도 호출 →
# preview-streamlit-clone.html 의 sc-* 모든 클래스가 자동 활성화.
from ui.vitals import apply_vitals_theme


def apply_global_styles():
    # 1) Vitals 글로벌 + clone CSS (둘 다 apply_vitals_theme 안에서 처리)
    apply_vitals_theme()

    # 2) 로그인 페이지 전용 오버레이 — 다크 비디오 배경 위 흰 카드 톤
    st.markdown(
        """
        <style>
        /* 2026-05-10 패스 1.5 — 시안 sec-login parity (preview-streamlit-clone.html
           line 2771-2772): sec-login 진입 시 body.is-login-active 클래스로 사이드바
           hide. login.py 가 components.html iframe 으로 parent body 에 클래스 add →
           다른 dashboard 페이지에는 클래스 없음 → cascade X, 사이드바 정상 표시. */
        body.is-login-active [data-testid="stSidebar"],
        body.is-login-active section[data-testid="stSidebar"],
        body.is-login-active [data-testid="stSidebarNav"],
        body.is-login-active [data-testid="stSidebarUserContent"],
        body.is-login-active [data-testid="collapsedControl"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            visibility: hidden !important;
        }
        /* 추가 강제 — body class race condition (streamlit 가 sidebar 먼저 그림 →
           components.html iframe 의 script 가 body class add) 대비. styles.py 는
           login.py 에서만 import 되므로 dashboard 페이지에는 영향 없음 (각 페이지가
           자체 inline css 를 다시 박는 구조). */
        [data-testid="stSidebar"],
        section[data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="stSidebarUserContent"],
        [data-testid="stSidebarHeader"],
        [data-testid="collapsedControl"],
        button[kind="headerNoPadding"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            visibility: hidden !important;
        }
        /* main 영역 left margin 0 — 사이드바 hide 후 컨텐츠가 좌측 끝까지 */
        [data-testid="stAppViewContainer"] > section:first-child + section,
        [data-testid="stAppViewContainer"] .main {
            margin-left: 0 !important;
            padding-left: 0 !important;
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

        /* 상단 Streamlit 헤더와 겹치지 않도록 여백
           사용자 피드백 (2026-05-08, 재): 영상이 viewport 풀 — 위·아래 여백 최소화.
           사용자 피드백 (2026-05-11) — overflow:hidden 으로 작은 viewport 에서 LG 로고
           가 잘리는 문제 → overflow:auto 로 변경. 콘텐츠가 100vh 안에 자연스럽게 들어가면
           스크롤바 안나옴, 넘치면 사용자가 스크롤 가능. 영상은 fixed bg 로 유지. */
        html, body { overflow: auto !important; }
        [data-testid="stAppViewContainer"] {
            min-height: 100vh !important;
            overflow: visible !important;
        }
        .block-container {
            /* 사용자 피드백 (2026-05-08): 로그인 좌우 분리 (4:3 → 16:9).
               max-width 1380 → 100% 풀폭. padding 좌우 80px 로 spread. */
            padding-top: 0.75rem !important;
            padding-bottom: 0.5rem !important;
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
        /* preview HTML parity: LG + Vitals + KO 가 좌측 cluster */
        .landing-topbar--cluster {
            justify-content: flex-start !important;
            gap: 24px;
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

        /* preview-streamlit-clone.html sec-login parity:
           좌측 column 460px / 가운데 1fr / 우측 column 360px.
           Streamlit native column 의 자동 stacking 을 보존하기 위해
           min-width 1380px 화면에서만 fixed-width 강제. 좁은 화면은
           기본 분수 비율 [0.32, 0.38, 0.30] 으로 fallback (stack 자동). */
        /* form 내부 + 회원가입 render_signup 의 nested columns 모두 카드 background X.
           render_signup 은 st.columns([0.01, 0.96, 0.03]) 으로 main_col wrap →
           이 nested stColumn 이 카드 스타일 cascade 받지 않도록 명시 */
        [data-testid="stColumn"] [data-testid="stHorizontalBlock"] [data-testid="stColumn"],
        [data-testid="stForm"] [data-testid="stColumn"] {
            background: transparent !important;
            box-shadow: none !important;
            padding: 0 !important;
            max-width: none !important;
            min-height: 0 !important;
            height: auto !important;
            flex: 1 1 auto !important;
        }
        /* nested stHorizontalBlock 안 stColumn 의 stVerticalBlock 도 transparent */
        [data-testid="stColumn"] [data-testid="stHorizontalBlock"] [data-testid="stVerticalBlock"] {
            background: transparent !important;
            box-shadow: none !important;
        }

        /* 2026-05-10 패스 5 — wine bar 가시화 fix.
           border-left 가 column wrapper 또는 상위 stack 에 가려질 가능성 →
           ::before pseudo + box-shadow inset 으로 이중 방어. */
        [data-testid="stMainBlockContainer"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child,
        [data-testid="stMain"] [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child,
        section.main [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child {
            background: rgba(255, 255, 255, 0.97) !important;
            border-radius: 0 !important;
            border: 0 !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            /* box-shadow inset 으로 wine bar (좌 4px) + drop shadow (외부) */
            box-shadow:
                inset 4px 0 0 0 #A50034,
                0 8px 32px -8px rgba(0, 0, 0, 0.18) !important;
            padding: 28px 36px 24px !important;
            box-sizing: border-box !important;
            position: relative !important;
            overflow: hidden !important;
            color: #1F2430 !important;
        }
        /* ::before pseudo 추가 — 일부 cascade 환경 대비 (이중 방어) */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child::before,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child::before {
            content: "" !important;
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 4px !important;
            height: 100% !important;
            background: #A50034 !important;
            z-index: 2 !important;
            pointer-events: none !important;
        }
        /* 2026-05-10 패스 4 — form 다음 모든 element hide (footer 제외).
           이전 패스 3의 :empty / :has 조건 selector 가 streamlit DOM 매칭 안 함.
           단순화: form 다음 stElementContainer 무조건 hide, footer 만 별도 통과. */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stForm"] ~ [data-testid="stElementContainer"] {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        /* 단, auth-card-foot 마크다운은 표시. .auth-card-foot 가진 stMarkdown 부모 살림. */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stForm"] ~ [data-testid="stElementContainer"]:has(.auth-card-foot) {
            display: block !important;
            height: auto !important;
            min-height: auto !important;
            margin: 18px 0 0 !important;
        }
        /* iframe (suffix script) 강제 hide — components.html 의 height 0 보강 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child iframe[title="st.iframe"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stIFrame"] {
            display: none !important;
            height: 0 !important;
            min-height: 0 !important;
            visibility: hidden !important;
        }
        /* 비밀번호 visibility toggle (눈 아이콘) hide — 시안에 없음 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child div[data-baseweb="input"] button,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[type="password"] ~ button,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child div[data-baseweb="input"] [aria-label*="password"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child div[data-baseweb="input"] [type="button"] {
            display: none !important;
        }
        /* 비밀번호 라벨 위치 — input 위에 겹치는 문제 fix. label margin-bottom 명시 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stWidgetLabel"] {
            margin: 12px 0 4px !important;
            padding: 0 !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stTextInput"] {
            margin: 0 0 12px !important;
        }
        /* 카드 안 buttons 직각 (시안 캡처 1: 로그인 버튼 직각) */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"] {
            border-radius: 0 !important;
        }
        /* 회원가입 primary button — 와인 채움 + 흰 글자 (login submit과 동일 톤) */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"] {
            background: #A50034 !important;
            border: 1px solid #A50034 !important;
            color: #FFFFFF !important;
            width: 100% !important;
            min-height: 40px !important;
            font-size: 13px !important;
            font-weight: 600 !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"]:hover {
            background: #7E0027 !important;
            border-color: #7E0027 !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"] p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }
        /* 회원가입 화면의 st.caption ("회사 이메일 인증 후 가입 가능합니다.") hide
           — 시안에는 없음 (캡처 2 매칭). 부모 stElementContainer 까지 hide 해야
           height 잔존 사라짐. */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stCaptionContainer"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stElementContainer"]:has([data-testid="stCaptionContainer"]) {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        /* iframe (suffix script + body class injection) 부모 stElementContainer 까지 hide */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stElementContainer"]:has(iframe[title="st.iframe"]),
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stElementContainer"]:has([data-testid="stIFrame"]),
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="element-container"]:has(iframe) {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        /* forgot password nested stHorizontalBlock 잔존 — login.py 에서 conditional
           제거 했지만 이전 cache 또는 다른 hidden 잔존 대비 nested column container
           자체도 hide */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stForm"] ~ [data-testid="stHorizontalBlock"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"]:not(:first-of-type):has([data-testid="stButton"]) {
            display: none !important;
            height: 0 !important;
        }
        /* 카드 안 success/error/info alert 톤 정리 — 카드 흰 배경에 어울리도록 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stAlert"] {
            margin: 8px 0 !important;
            padding: 6px 10px !important;
            font-size: 12px !important;
        }

        /* 2026-05-10 패스 9 — 사용자 요청 fix.
           1) footer 카드 바닥에 붙임
           2) 카드 안 폰트 통일 (인증 실패 시 폰트 변경 방지)
           3) "press enter to submit" instruction hide
           4) password input ID 와 동일 크기
           5) signup step 2 시안 매칭 시각 */

        /* (1) 패스 15 — 카드 height 자동 (이전 min-height 460 + margin-top auto 누적
           으로 카드가 viewport 풀 높이 차지 / STEP 2 시 빈 영역 발생 → fix). */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child > [data-testid="stVerticalBlock"] {
            display: block !important;
            min-height: 0 !important;
            height: auto !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stElementContainer"]:has(.auth-card-foot) {
            margin-top: 12px !important;
        }
        /* nested column 자동 stack 방지 — 좁은 폭에서도 horizontal 강제 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 8px !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            width: auto !important;
        }

        /* (2) stApp 전역 광역 폰트 — form submit 후 rerun 시 cascade 깨짐 fix.
           이전 패스: 카드/identity 만 scope → form submit 후 다른 element 가
           Noto Sans KR 시스템 fallback (사용자 dev tool 검증). */
        [data-testid="stApp"],
        [data-testid="stApp"] *,
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] *,
        body.is-login-active,
        body.is-login-active * {
            font-family: 'LG EI Text', 'LG Smart', 'Malgun Gothic', system-ui, sans-serif !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child *,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child *,
        [data-testid="stAlert"],
        [data-testid="stAlert"] * {
            font-family: 'LG EI Text', 'LG Smart', 'Malgun Gothic', system-ui, sans-serif !important;
        }
        /* alert (error/success) — 카드 폰트 강제 + 사이즈 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stAlert"] *,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stAlertContentError"] *,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stAlertContentSuccess"] *,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [role="alert"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [role="alert"] * {
            font-family: 'LG EI Text', 'LG Smart', 'Malgun Gothic', system-ui, sans-serif !important;
            font-size: 12px !important;
        }
        /* (2-mono) landing.html mono 적용 위치 — IBM Plex Mono 강제.
           광역 룰 후에 정의되어 cascade 후순위 우선 (specificity 동등 시 후순위 win). */
        .auth-card-foot,
        .auth-card-foot *,
        .auth-card-foot span,
        .auth-card-foot__ver,
        .auth-suffix-hint,
        .signup-timer-hint,
        .signup-timer,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child .id-suffix-injected,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[aria-label*="인증코드"] {
            font-family: 'LG EI Text', 'LG Smart', 'Malgun Gothic', system-ui, sans-serif !important;
        }
        /* (2-display) Vitals. hero — LG EI Headline 강제 (광역 룰 후 cascade 우선).
           form submit 후 rerun 시에도 유지되도록 매우 specific selector. */
        body.is-login-active .identity-name,
        body.is-login-active .identity-name *,
        body.is-login-active .identity-name .dot,
        body.is-login-active h3.identity-name,
        [data-testid="stApp"] .identity-name,
        [data-testid="stApp"] .identity-name *,
        [data-testid="stApp"] h3.identity-name,
        .identity-block .identity-name,
        .identity-block .identity-name *,
        h3.identity-name {
            font-family: 'LG EI Headline', 'LG EI Text', 'LG Smart', 'Malgun Gothic', sans-serif !important;
            font-size: 88px !important;
            font-weight: 700 !important;
            letter-spacing: -0.04em !important;
            line-height: 0.95 !important;
        }
        body.is-login-active .identity-name .dot,
        [data-testid="stApp"] .identity-name .dot,
        .identity-block .identity-name .dot {
            color: #A50034 !important;
        }

        /* (7) 반응형 — 화면 작아져도 카드 크기 유지 + 폰트 비율 유지.
           시안 .auth-card 는 width 100% / max-width 460. 좁은 화면에서도 작아짐 X. */
        @media (max-width: 1280px) {
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child {
                min-width: 380px !important;
                padding: 24px 28px 20px !important;
            }
        }
        @media (max-width: 980px) {
            [data-testid="stHorizontalBlock"]:first-of-type {
                flex-direction: column !important;
                gap: 20px !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child {
                min-width: 320px !important;
                width: 100% !important;
                max-width: 460px !important;
                margin: 0 auto !important;
            }
            .identity-name {
                font-size: 64px !important;
            }
        }
        @media (max-width: 640px) {
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child {
                min-width: 280px !important;
                padding: 20px 20px 16px !important;
            }
            .identity-name {
                font-size: 48px !important;
            }
            .identity-sub {
                font-size: 14px !important;
            }
        }
        /* 카드 자체 width — 시안 캡처 2 매칭: 460-525px 폭 / 480px height 자연.
           이전 460 강제 → 캡처 1처럼 좁아 nested column 압축 → 폭 늘림. */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child {
            min-width: 460px !important;
            max-width: 525px !important;
            width: 100% !important;
            flex: 0 0 auto !important;
        }
        /* 카드 안 element 사이 spacing — 시안 캡처 2 매칭 (자연 호흡감) */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stTextInput"] {
            margin: 0 0 14px !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child .signup-sent-msg {
            margin: 4px 0 12px !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child .signup-timer-hint {
            margin: -4px 0 18px !important;
        }
        /* 회원가입 완료 button — 시안과 같이 큰 button (column 폭 충분) */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"] {
            min-height: 44px !important;
            padding: 8px 16px !important;
        }

        /* 패스 14 — signup STEP 2 의 nested column 안 secondary/right button 을
           link 형태로 (시안 캡처 2 의 "← 이메일 수정" / "인증코드 재발송"). */
        /* 카드 안 nested stHorizontalBlock 의 두 번째 column (right) 안 button → link */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child [data-testid="stButton"] button {
            background: transparent !important;
            color: #6B7280 !important;
            border: 0 !important;
            border-radius: 0 !important;
            padding: 4px 0 !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            min-height: 28px !important;
            height: auto !important;
            box-shadow: none !important;
            text-decoration: none !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button:hover,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child [data-testid="stButton"] button:hover {
            background: transparent !important;
            color: #A50034 !important;
            text-decoration: underline !important;
        }
        /* nested column 의 link button text (p 태그) 강제 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stButton"] button p,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child [data-testid="stButton"] button p {
            color: #6B7280 !important;
            font-weight: 500 !important;
            font-size: 12px !important;
        }
        /* 단, 첫 번째 column (왼쪽 - 회원가입 완료 / 인증 확인) 의 button 은 wine primary 유지 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"] {
            background: #A50034 !important;
            color: #FFFFFF !important;
            border-radius: 0 !important;
            min-height: 40px !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"] p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
            font-size: 13px !important;
        }

        /* (6) UI 가운데 정렬 — streamlit 1.55 DOM 정확 매칭.
           이전 패스 10 의 stMainBlockContainer 가 1.55 에서 매칭 안 됨.
           실제 1.55 구조: stApp > stAppViewContainer > main.main > .block-container */
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"] {
            min-height: 100vh !important;
        }
        /* 사용자 피드백 (2026-05-11) — 이전: vertical center → 1006px viewport 에서
           내용 (topbar + 카드 + 푸터) 이 100vh 초과 시 양쪽으로 잘려 LG/Vitals 브랜드
           가 위로 사라짐. flex-start 로 변경 → 항상 위에서부터 쌓임. 좁은 viewport
           에서 scroll 차단되어도 brand + auth-card 는 보장. */
        section.main,
        [data-testid="stMain"],
        .main {
            display: flex !important;
            align-items: stretch !important;
            justify-content: flex-start !important;
            min-height: 100vh !important;
            flex-direction: column !important;
        }
        section.main > .block-container,
        [data-testid="stMain"] > .block-container,
        .main > .block-container {
            margin: 0 auto !important;
            width: 100% !important;
        }
        /* 첫 row (auth + identity) 의 vertical alignment center */
        [data-testid="stHorizontalBlock"]:first-of-type {
            align-items: center !important;
        }

        /* (3) "Press Enter to submit form" / "Press Enter to apply" instruction hide */
        [data-testid="InputInstructions"],
        [data-testid="stTextInputInstructions"],
        [data-testid="stWidgetLabelHelp"],
        [data-testid="stTextInput"] + small,
        [data-testid="stTextInput"] [data-testid*="Instruction"],
        [data-testid="stForm"] [data-testid*="Instruction"],
        .stTextInput [class*="Instruction"] {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }

        /* (4) password input ID 와 동일 width/padding/height */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stTextInput"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stTextInput"] [data-baseweb="input"] {
            width: 100% !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[type="password"] {
            padding: 8px 130px 8px 12px !important;
            height: 38px !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[type="text"] {
            height: 38px !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }

        /* (5) signup step 2 시안 매칭 시각 (preview-streamlit-clone.html line 221-238) */
        .signup-sent-msg {
            margin: 6px 0 8px !important;
            font-size: 13px !important;
            color: #6B7280 !important;
            font-family: 'LG EI Text', 'LG Smart', 'Malgun Gothic', system-ui, sans-serif !important;
        }
        .signup-timer-hint {
            margin: -6px 0 12px !important;
            font-size: 11px !important;
            color: #9CA3AF !important;
            font-family: 'LG EI Text', sans-serif !important;
        }
        .signup-timer {
            color: #B23A48 !important;
            font-weight: 700 !important;
            margin-left: 4px !important;
            font-family: 'LG EI Text', sans-serif !important;
        }
        /* 인증코드 input — 6자리 mono + 가운데 정렬 + letter-spacing */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[aria-label*="인증코드"] {
            letter-spacing: 0.4em !important;
            font-family: 'LG EI Text', sans-serif !important;
            text-align: center !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            padding-right: 12px !important;  /* 6자리는 suffix 없으니 padding 12 */
        }
        /* form 자체의 자투리 padding/margin/background 0 */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stForm"] {
            background: transparent !important;
            border: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            box-shadow: none !important;
        }
        /* input wrap (baseweb) — 시안 line 2820-2828 흰색 강제 (광역 selector) */
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child div[data-baseweb="input"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child div[data-baseweb="input"] > div {
            background: #FFFFFF !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 8px !important;
            box-shadow: none !important;
        }
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child div[data-baseweb="input"] input,
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[type="text"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[type="password"],
        [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input[type="email"] {
            background: #FFFFFF !important;
            color: #1F2430 !important;
            border: 0 !important;
            font-size: 13px !important;
        }
        @media (min-width: 1380px) {
            /* 첫 row 의 좌측 column (auth-card row) 에만 fixed 460 + 카드 톤
               시안 정확 측정: w 460 / padding 30 32 28 / form 자연 높이.
               min-height 480 제거 — form 길이 짧을 때 카드 안 빈 영역 생기는 문제 fix. */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:first-child,
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child {
                max-width: 460px !important;
                flex: 0 0 460px !important;
                width: 460px !important;
                min-height: 0 !important;
                height: auto !important;
                overflow: hidden !important;
            }
            /* 480px 안에 모든 form fit — 정확한 streamlit element margin tight */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stElementContainer"] {
                margin-bottom: 0 !important;
                margin-top: 0 !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stMarkdown"] {
                margin: 0 !important;
            }
            /* form 내부 vertical spacing 의 streamlit default gap 0 */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stVerticalBlock"] {
                gap: 0 !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stRadio"] {
                margin: 0 0 12px !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stTextInput"] {
                margin-bottom: 8px !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stForm"] {
                background: transparent !important;
                border: 0 !important;
                padding: 0 !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] {
                margin-top: 6px !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button {
                height: 40px !important;
                min-height: 40px !important;
            }
            /* stWidgetLabel (아이디/비밀번호 라벨) margin 줄임 */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stWidgetLabel"] {
                margin-bottom: 2px !important;
                padding-bottom: 0 !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stWidgetLabel"] p {
                margin: 0 !important;
                font-size: 12px !important;
            }
            /* input — streamlit native height 유지 (38). 시안과 미세 차이지만
               자연스러운 입력 UX 우선. */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child input {
                font-size: 14px !important;
            }
            /* radio horizontal tight */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stRadio"] [role="radiogroup"] {
                gap: 12px !important;
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stRadio"] label {
                padding: 4px 0 !important;
                margin: 0 !important;
                min-height: 0 !important;
            }
            /* iframe (suffix script) — components.html 이 height 230~270 강제하므로
               컨테이너까지 전부 hide. script 만 실행되면 됨, 시각 표시 X */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child iframe[title="st.iframe"],
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stIFrame"] {
                height: 0 !important;
                min-height: 0 !important;
                max-height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
                border: 0 !important;
                visibility: hidden !important;
                display: block !important;  /* script 실행은 되도록 */
            }
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stIFrame"] > div {
                height: 0 !important;
                min-height: 0 !important;
            }
            /* stHeading (.auth-title h2) wrapper margin */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:first-child [data-testid="stHeadingWithActionElements"] {
                margin: 0 !important;
                padding: 0 !important;
            }
            /* auth-card-foot 위 spacing 줄여서 480 안에 fit */
            .auth-card-foot {
                margin-top: 10px !important;
            }
            .auth-suffix-hint {
                margin: -2px 0 6px !important;
            }
            /* 첫 row 의 우측 column (panels) 360px */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:last-child,
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:last-child {
                max-width: 360px !important;
                flex: 0 0 360px !important;
                width: 360px !important;
            }
            /* 첫 row 의 가운데 spacer */
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"]:nth-child(2),
            [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="stColumn"]:nth-child(2) {
                flex: 1 1 auto !important;
            }
            /* identity-block 은 columns 밖 markdown 으로 박힘.
               max-width 460 + 좌측 정렬로 첫 row 좌측 카드 아래에 시각 정렬. */
            .identity-block {
                max-width: 460px;
                margin-top: 24px;
                margin-bottom: 24px;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2),
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
                flex: 1 1 auto !important;
                max-width: none !important;
                width: auto !important;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child,
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
                max-width: 360px !important;
                flex: 0 0 360px !important;
                width: 360px !important;
            }
        }

        /* deprecated — stContainer testid 는 streamlit 1.55 에 없음.
           카드 톤은 위 media query 의 stColumn 자체에 적용. */

        /* 좌측 column 안의 모든 form 요소를 light 톤으로 (흰 카드 위 가독성) */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .stTextInput input,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .stTextInput input {
            background: #F1F3F5 !important;
            border: 1px solid #E5E7EB !important;
            color: #1F2430 !important;
        }
        /* form 의 stTextInput / stRadio 라벨만 회색 — submit button 안의
           label/p 는 와인 button 위에 흰 글자로 보존되어야 함 */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stTextInput"] label,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stTextInput"] label p,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stRadio"] label p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stTextInput"] label,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stTextInput"] label p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stRadio"] label p {
            color: #6B7280 !important;
        }
        /* submit button — Streamlit 1.55 는 secondaryFormSubmit kind 를 쓴다.
           preview HTML 의 .btn--primary 와인 채움 상태를 강제. 텍스트는 흰. */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child button[kind="primaryFormSubmit"],
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child button[kind="secondaryFormSubmit"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child button[kind="primaryFormSubmit"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child button[kind="secondaryFormSubmit"] {
            background: #A50034 !important;
            border-color: #A50034 !important;
            color: #FFFFFF !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child button[kind="secondaryFormSubmit"]:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child button[kind="secondaryFormSubmit"]:hover {
            background: #7E0027 !important;
            border-color: #7E0027 !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button p,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child button[kind="primaryFormSubmit"] p,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child button[kind="secondaryFormSubmit"] p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child button[kind="primaryFormSubmit"] p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child button[kind="secondaryFormSubmit"] p {
            color: #FFFFFF !important;
            font-weight: 600 !important;
        }
        /* 시안 정확 매칭 — 더 specific selector 가 위 layout.py inline style 을
           override 하지 않도록 주의. 시안 측정값:
             eyebrow rgb(156, 163, 175) = #9CA3AF
             title   rgb(16,  18,  24)  = #101218
             sub     rgb(107, 114, 128) = #6B7280  (그대로) */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .auth-eyebrow,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .auth-eyebrow {
            color: #9CA3AF !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .auth-title,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .auth-title {
            color: #101218 !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .auth-sub,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .auth-sub {
            color: #6B7280 !important;
        }
        /* 시안 sec-login parity 강제 — 카드 안에서 다크 톤 룰 (line 460-497) 무효화.
           layout.py render_auth_intro 인라인 룰이 다시 덮여 시안 사이즈/마진/색이
           무너지는 것 fix (2026-05-10 패스 1). */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .auth-eyebrow,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .auth-eyebrow {
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            margin: 0 0 6px !important;
            padding: 0 !important;
            line-height: 1 !important;
        }
        /* 시안에는 eyebrow 앞 wine bar 없음 — styles.py line 471 ::before 제거 */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .auth-eyebrow::before,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .auth-eyebrow::before {
            display: none !important;
            content: none !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .auth-title,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .auth-title {
            font-size: 22px !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em !important;
            margin: 0 0 4px !important;
            padding: 0 !important;
            line-height: 1.2 !important;
            text-shadow: none !important;
            font-family: 'LG EI Headline', 'LG EI Text', 'LG Smart', 'Malgun Gothic', sans-serif !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .auth-sub,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .auth-sub {
            font-size: 13px !important;
            font-weight: 400 !important;
            margin: 0 0 16px !important;
            padding: 0 !important;
            line-height: 1.4 !important;
            border-bottom: 0 !important;
            text-shadow: none !important;
        }
        /* 로그인 / 회원가입 탭 (radio horizontal) 의 텍스트 색상 light 톤 */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stRadio"] label,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stRadio"] label {
            color: #1F2430 !important;
        }
        /* 시안 sec-login tabs parity (streamlit-clone.css line 2757-2781).
           카드 안 흰 배경에서 다크 톤 line 535 룰 cascade 무효화. */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div[data-testid="stRadio"] label p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child div[data-testid="stRadio"] label p {
            color: #6B7280 !important;
            font-weight: 600 !important;
            font-size: 13px !important;
            padding: 8px 4px !important;
            border-bottom: 2px solid transparent !important;
        }
        /* 선택된 탭 — 시안 .tab--active: ink-body 검정 + wine border-bottom */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child div[data-testid="stRadio"] label[data-baseweb="radio"] input:checked + div p {
            color: #101218 !important;
            border-bottom-color: var(--primary, #A50034) !important;
        }
        /* hover — 시안 .tab:not(.tab--active):hover */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div[data-testid="stRadio"] label:hover p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child div[data-testid="stRadio"] label:hover p {
            color: #101218 !important;
        }
        /* radio 그룹 컨테이너 — 카드 안에선 다크 라인 (rgba 0.10) 대신 라이트 */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div[data-testid="stRadio"] > div,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child div[data-testid="stRadio"] > div {
            border-bottom: 1px solid #E5E7EB !important;
            margin-bottom: 14px !important;
        }
        /* 카드 안 input — 시안 streamlit-clone.css line 2820-2828:
           border-radius 8px / 흰 배경 / E5E7EB border. 다크 톤 line 558-565 무효화. */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div[data-baseweb="input"] > div,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child div[data-baseweb="input"] > div {
            border-radius: 8px !important;
            border: 1px solid #E5E7EB !important;
            background: #FFFFFF !important;
            box-shadow: none !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child div[data-baseweb="input"] > div:focus-within,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child div[data-baseweb="input"] > div:focus-within {
            border-color: var(--primary, #A50034) !important;
            box-shadow: 0 0 0 3px rgba(165, 0, 52, 0.16) !important;
        }
        /* 카드 안 input 자체 — 흰 카드 배경에 어울리는 회색 light fill */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child .stTextInput input,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child .stTextInput input {
            background: transparent !important;
            border: 0 !important;
            color: #1F2430 !important;
            font-size: 13px !important;
        }
        /* 카드 안 submit button — radius 8 (시안 button parity) */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button {
            border-radius: 8px !important;
            min-height: 40px !important;
            font-size: 13px !important;
        }

        /* 사용자 피드백 (2026-05-11) — 붉은 버튼(로그인/회원가입) 주변 그라데이션 음영 제거.
           Streamlit BaseWeb 기본 button 의 background-image, box-shadow, filter 가
           cascade 우회로 살아남는 것을 차단. 모든 state 에서 truly flat solid wine. */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="primary"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"],
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child button[kind="primaryFormSubmit"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child button[kind="primaryFormSubmit"] {
            background: #A50034 !important;
            background-image: none !important;
            background-color: #A50034 !important;
            background-clip: padding-box !important;
            border: 1px solid #A50034 !important;
            color: #FFFFFF !important;
            box-shadow: none !important;
            text-shadow: none !important;
            filter: none !important;
            outline: 0 !important;
            transform: none !important;
            -webkit-appearance: none !important;
            appearance: none !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="primary"]:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"]:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child button[kind="primaryFormSubmit"]:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child button[kind="primaryFormSubmit"]:hover {
            background: #7E0027 !important;
            background-image: none !important;
            background-color: #7E0027 !important;
            border: 1px solid #7E0027 !important;
            color: #FFFFFF !important;
            box-shadow: none !important;
            text-shadow: none !important;
            filter: none !important;
            outline: 0 !important;
            transform: none !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button:focus,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button:active,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"] button:focus-visible,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button:focus,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button:active,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] button:focus-visible,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="primary"]:focus,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="primary"]:active,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"]:focus,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="primary"]:active {
            background: #7E0027 !important;
            background-image: none !important;
            background-color: #7E0027 !important;
            border: 1px solid #7E0027 !important;
            color: #FFFFFF !important;
            box-shadow: none !important;
            text-shadow: none !important;
            filter: none !important;
            outline: 0 !important;
            transform: none !important;
        }
        /* stFormSubmitButton wrapper container — drop shadow / border 제거 */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stFormSubmitButton"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stFormSubmitButton"] {
            box-shadow: none !important;
            background: transparent !important;
            filter: none !important;
        }

        /* identity hero (Vitals. + 캐치프레이즈) 는 auth-card 밖 영역 →
           styles 의 다른 곳에서 정의된 흰 글자 (var(--on-dark)) 유지.
           좌측 column 의 stContainer 가 아닌 자식 (stMarkdown 등) 은
           위 흰 카드 룰의 영향을 받지 않음. */

        /* @lginnotek.com suffix 는 login.py 의 components.html script 가
           parent DOM 의 첫 stTextInputRootElement 에 직접 .id-suffix-injected
           span 을 attach. ::after pseudo-element 는 :first-of-type 이
           streamlit 의 모든 stTextInput 에 cascade 되어 비밀번호 input 에도
           잘못 적용되므로 사용하지 않음 (2026-05-10 검증). */
        /* preview-streamlit-clone.html parity: forgot password link 시안 X →
           시각만 hide. reset 흐름 자체는 백엔드 보존. 사용자는 다른 방식으로
           reset 접근 가능 (또는 다음 commit 에서 footer 영역에 작은 link 추가). */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"]:has(button[kind="secondary"]),
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"]:has(button[kind="secondary"]) {
            display: none !important;
        }

        /* preview-streamlit-clone.html parity: forgot password 를 link 처럼.
           카드 내부 작은 회색 글자로. type="secondary" button 을 background
           투명 + border 0 + 작은 회색 텍스트로 변환. */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="secondary"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="secondary"] {
            background: transparent !important;
            border: 0 !important;
            color: #9CA3AF !important;
            padding: 6px 0 !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            text-align: left !important;
            box-shadow: none !important;
            justify-content: flex-start !important;
            min-height: 0 !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="secondary"]:hover,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="secondary"]:hover {
            color: var(--primary, #A50034) !important;
            background: transparent !important;
            text-decoration: underline !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="secondary"] p,
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="secondary"] p {
            color: inherit !important;
            font-size: 12px !important;
            margin: 0 !important;
        }
        /* signup STEP 2 의 "이메일 수정" / "인증코드 재발송" 은 실제 link control.
           이전 forgot-password 숨김 룰 때문에 secondary button 전체가 사라지던 것을 복원. */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"]:has(button[kind="secondary"]),
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"]:has(button[kind="secondary"]) {
            display: block !important;
            visibility: visible !important;
            height: auto !important;
            margin: -6px 0 12px !important;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child [data-testid="stButton"] button[kind="secondary"],
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child [data-testid="stButton"] button[kind="secondary"] {
            width: auto !important;
            min-height: 22px !important;
        }

        /* @lginnotek.com 자동 적용 hint */
        .auth-suffix-hint {
            font-size: 11px;
            color: #9CA3AF;
            margin: -4px 0 8px 2px;
            line-height: 1.3;
        }
        /* @lginnotek.com suffix 는 components.html iframe 안 script 가
           parent DOM 의 stTextInputRootElement 안에 직접 span (.id-suffix-injected)
           을 inject. CSS 만으로는 ::after 가 streamlit DOM 에 안 먹어서 JS 사용. */

        .left-panel-bg {
            /* deprecated — column 자체에 background 적용으로 대체 (위 media query).
               이 div 는 호환성 위해 함수만 호출되고 display: none. */
            display: none;
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: transparent;
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
            background: var(--primary) !important;
            color: #ffffff !important;
            border: 1px solid rgba(165,0,52,0.95) !important;
            box-shadow: none !important;
            filter: none !important;
            letter-spacing: -0.01em;
        }

        .stFormSubmitButton button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            background: var(--primary-dark) !important;
            color: #ffffff !important;
            border: 1px solid var(--primary-dark) !important;
            transform: translateY(-1px);
            box-shadow: none !important;
            filter: none !important;
        }

        .stFormSubmitButton button:focus,
        .stFormSubmitButton button:active,
        div[data-testid="stFormSubmitButton"] button:focus,
        div[data-testid="stFormSubmitButton"] button:active {
            background: var(--primary-dark) !important;
            color: #ffffff !important;
            border: 1px solid var(--primary-dark) !important;
            box-shadow: none !important;
            filter: none !important;
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
            font-size: 88px !important;
            font-weight: 800;
            line-height: 0.96;
            color: var(--on-dark);
            letter-spacing: -0.05em;
            text-shadow: 0 6px 24px rgba(0,0,0,0.24);
        }

        .identity-name .dot {
            color: #A50034 !important;
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

        /* 사용자 피드백 (2026-05-11) — 1100px 브레이크포인트가 일반 노트북(1006px)
           에서 활성화되어 LG 로고+Vitals 워드마크가 KO 위로 stack → viewport 위로
           잘려 보임. 800px 로 낮춰 표준 노트북에서 row layout 유지. */
        @media (max-width: 800px) {
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
