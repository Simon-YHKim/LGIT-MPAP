"""
ui.vitals.theme — Vitals 글로벌 스타일 진입점 (Light + Dark)

페이지 첫 줄에서 `apply_vitals_theme()` 호출 → 와인레드 팔레트, LG EI 폰트,
Streamlit 기본 사이드바 hide, 카드/표/버튼 톤이 일괄 적용된다.

디자인 토큰 출처: docs/design/landing.html 의 :root 변수 + 사용자 피드백
반영본 (와인 강조 1점 정책, 8~12px radius, calm engineering 톤).

Dark mode (2026-05-07 추가):
- :root 는 light 기본값을 정의, [data-theme="dark"] 는 dark 오버라이드
- Streamlit iframe 샌드박스 우회를 위해 .stApp[data-theme=...] 셀렉터를
  병행하고, 매 rerun 마다 root 요소들에 data-theme 속성을 설정하는
  작은 <script> 를 함께 inject. body 클래스 (.vitals-dark) 도 동시에 부여 →
  어떤 wrapper 가 먼저 잡히든 토큰이 일관되게 적용.
- 함수 시그니처 호환성: apply_vitals_theme() 는 인자 없이 동작 (기존 호출
  사이트 모두 그대로 작동). 신규 옵셔널 파라미터 theme 만 추가.
"""
from __future__ import annotations
from typing import Literal, Optional
import streamlit as st

from .fonts import (
    font_face_block,
    FONT_BODY_STACK,
    FONT_DISPLAY_STACK,
    FONT_MONO_STACK,
)


_THEME_SESSION_KEY = "vitals_theme"  # 'light' | 'dark'


def get_current_theme() -> str:
    """현재 활성 Vitals 테마 ('light' 또는 'dark') 반환.

    session_state['vitals_theme'] 를 정규화 후 반환. 미설정/잘못된 값은 'light'.
    """
    raw = st.session_state.get(_THEME_SESSION_KEY, "light")
    return "dark" if raw == "dark" else "light"


def _set_theme(theme: str) -> None:
    """session_state 에 테마 저장 (정규화). 외부 직접 호출용 헬퍼."""
    st.session_state[_THEME_SESSION_KEY] = "dark" if theme == "dark" else "light"


def _build_css() -> str:
    """모든 글로벌 스타일을 한 덩어리로 빌드.

    light 토큰은 :root 에, dark 오버라이드는 [data-theme="dark"] 와
    .vitals-dark (body class) 양쪽에 정의 — Streamlit DOM 어디에 속성이 붙어도
    var() 가 정상 해상되도록.
    """
    return f"""
{font_face_block()}

:root {{
    /* Brand */
    --primary:        #A50034;
    --primary-dark:   #7E0027;
    --primary-tint:   #F8E5EC;

    /* Surfaces */
    --page-bg:        #F7F8FA;
    --card-bg:        #FFFFFF;
    --soft:           #F1F3F5;

    /* Borders */
    --border:         #E5E7EB;
    --border-strong:  #CBD0D6;

    /* Ink */
    --ink-body:       #1F2430;
    --ink-muted:      #6B7280;
    --ink-subtle:     #9CA3AF;

    /* Status (Good / Warn / Bad) */
    --status-good:    #1F8B4C;
    --status-warn:    #B57F1B;
    --status-bad:     #B23A48;
    --status-good-tint: #E6F4EA;
    --status-warn-tint: #FAF1DD;
    --status-bad-tint:  #FDECEF;

    /* On-dark (login video bg 등 다크 영역용) */
    --on-dark:           #FFFFFF;
    --on-dark-muted:     rgba(255,255,255,0.76);
    --on-dark-subtle:    rgba(255,255,255,0.56);
    --panel-dark:        rgba(12,14,18,0.68);
    --panel-border-dark: rgba(255,255,255,0.10);

    /* Fonts */
    --font-body:    {FONT_BODY_STACK};
    --font-display: {FONT_DISPLAY_STACK};
    --font-mono:    {FONT_MONO_STACK};

    /* Layout — Vitals 디자인 원칙: 직사각형. radius 토큰을 0 으로 통일.
       (이전 8/12 값은 streamlit-clone.css 의 --sc-radius 8/12 와 충돌해
       cascade 가 마지막 로드 순서에 좌우됐음.) */
    --radius:        0;
    --radius-card:   0;
    --shadow-card:   0 8px 22px -4px rgba(15,17,21,0.06);
    --shadow-elev:   0 30px 80px -20px rgba(0,0,0,0.55);
}}

/* Dark theme overrides — applied when ANY ancestor has data-theme="dark"
   OR body carries .vitals-dark. Both sets of selectors target the same
   var() group so cascade resolution always succeeds in Streamlit's nested
   shadow/iframe-ish DOM. */
:root[data-theme="dark"],
[data-theme="dark"],
body.vitals-dark,
body.vitals-dark .stApp,
.stApp[data-theme="dark"] {{
    --primary:        #A50034;
    --primary-dark:   #7E0027;
    --primary-tint:   #2A1218;

    --page-bg:        #0E1117;
    --card-bg:        #161B22;
    --soft:           #1A1F2A;

    --border:         #2A2F3A;
    --border-strong:  #3A4051;

    --ink-body:       #E5E7EB;
    --ink-muted:      #9CA3AF;
    --ink-subtle:     #6B7280;

    --status-good:    #2EA85C;
    --status-warn:    #D69E2E;
    --status-bad:     #E5495A;
    --status-good-tint: #0F2418;
    --status-warn-tint: #2A2210;
    --status-bad-tint:  #2E1318;

    --shadow-card:   0 8px 22px -4px rgba(0,0,0,0.45);
}}

/* Reset / base ---------------------------------------------------- */
html, body, [class*="css"] {{
    font-family: var(--font-body);
    word-break: keep-all;
}}
html, body {{
    background: var(--page-bg);
    color: var(--ink-body);
    -webkit-font-smoothing: antialiased;
}}
.stApp {{ background: var(--page-bg); }}

/* Streamlit 사이드바 — 우리 디자인 톤으로 스타일 (기본 표시, 페이지 이동에 사용)
   로그인 페이지는 ui/login_ui/styles.py 에서 별도 hide 함. */
/* 사용자 피드백 (2026-05-08): 사이드바 user profile 항상 최하단 sticky.
   stSidebar 의 column flex 안에서 stSidebarNav 가 전체 차지, user profile
   영역 (vit-sidebar-user) 이 margin-top:auto 로 push down. */
[data-testid="stSidebar"],
section[data-testid="stSidebar"] {{
    background: var(--card-bg) !important;
    border-right: 1px solid var(--border) !important;
    display: flex !important;
    flex-direction: column !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
    flex: 1 1 auto !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    color: var(--ink-muted) !important;
    border-radius: var(--radius) !important;
    transition: background .12s, color .12s !important;
}}
/* Vitals 사이드바 user profile + contact (apply_vitals_theme 가 inject) */
.vit-sidebar-user {{
    margin-top: auto;
    padding: 12px 16px;
    border-top: 1px solid var(--border);
    background: var(--card-bg);
    display: flex;
    align-items: center;
    gap: 10px;
}}
.vit-sidebar-user__avatar {{
    width: 32px; height: 32px;
    flex: 0 0 auto;
    background: var(--primary);
    color: #FFFFFF;
    display: grid;
    place-items: center;
    font-family: 'LG EI Headline', 'LG EI Text', sans-serif;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: -0.01em;
}}
.vit-sidebar-user__body {{
    flex: 1 1 auto;
    min-width: 0;
}}
.vit-sidebar-user__name {{
    font-family: 'LG EI Headline', 'LG EI Text', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: var(--ink-body);
    line-height: 1.2;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.vit-sidebar-user__email {{
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--ink-muted);
    line-height: 1.2;
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.vit-sidebar-user-contact {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--ink-muted);
    text-decoration: none;
    border-top: 1px dashed var(--border);
    transition: color 120ms;
}}
.vit-sidebar-user-contact:hover {{ color: var(--primary); }}
.vit-sidebar-user-contact svg {{ width: 13px; height: 13px; flex: 0 0 auto; }}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{
    background: var(--soft) !important;
    color: var(--ink-body) !important;
}}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
    color: var(--ink-body) !important;
    background: var(--primary-tint) !important;
    border-left: 3px solid var(--primary) !important;
    padding-left: 13px !important;
}}
[data-testid="stHeader"] {{ background: transparent !important; }}

/* Streamlit 기본 푸터 hide */
footer {{ visibility: hidden; }}

/* Streamlit 컨테이너 폭/패딩 — 사용자 피드백 (2026-05-08):
   · 16:9 모니터 최적화 — 상하 여백 최소.
   · 좌우 여백 = patch note 패턴 (1rem).
   · max-width 1640 → 100% (16:9 풀폭 활용).
   이전: padding-top 1.6rem, padding-bottom 1.2rem.
   지금: padding-top 0.5rem, padding-bottom 0.5rem (= preview --sc-pad-y). */
.block-container {{
    padding-top: 0.5rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 100% !important;
}}

/* Headings ------------------------------------------------------- */
h1, h2, h3, h4, h5, h6 {{
    font-family: var(--font-display);
    color: var(--ink-body);
    letter-spacing: -0.02em;
    word-break: keep-all;
}}

/* Streamlit form inputs (text/select/date) — 와인 포커스 링 ------ */
[data-baseweb="input"] > div,
[data-baseweb="select"] > div,
.stTextInput > div > div,
.stDateInput > div > div,
.stSelectbox > div > div {{
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: var(--card-bg) !important;
    color: var(--ink-body) !important;
    transition: border-color .15s, box-shadow .15s;
}}
[data-baseweb="input"]:focus-within > div,
[data-baseweb="select"]:focus-within > div,
.stTextInput > div > div:focus-within,
.stDateInput > div > div:focus-within {{
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px var(--primary-tint) !important;
}}

/* Streamlit buttons ---------------------------------------------- */
.stButton > button,
.stDownloadButton > button {{
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: var(--card-bg) !important;
    color: var(--ink-body) !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    transition: border-color .15s, background .15s, color .15s;
}}
.stButton > button:hover,
.stDownloadButton > button:hover {{
    border-color: var(--border-strong) !important;
    background: var(--soft) !important;
}}
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {{
    background: var(--primary) !important;
    border-color: var(--primary) !important;
    color: #FFFFFF !important;
}}
.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {{
    background: var(--primary-dark) !important;
    border-color: var(--primary-dark) !important;
    color: #FFFFFF !important;
}}

/* Streamlit tabs — 와인 활성 밑줄 */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0;
    border-bottom: 1px solid var(--border);
}}
.stTabs [data-baseweb="tab"] {{
    background: transparent !important;
    color: var(--ink-muted) !important;
    font-weight: 600 !important;
    border-bottom: 2px solid transparent !important;
}}
.stTabs [data-baseweb="tab"][aria-selected="true"] {{
    color: var(--ink-body) !important;
    border-bottom-color: var(--primary) !important;
}}

/* Status badge utility (Good / Warn / Bad) ----------------------- */
.vit-badge {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .05em;
    text-transform: uppercase;
    white-space: nowrap;
}}
.vit-badge--good   {{ background: var(--status-good-tint); color: var(--status-good); }}
.vit-badge--warn   {{ background: var(--status-warn-tint); color: var(--status-warn); }}
.vit-badge--subtle {{ background: var(--soft);             color: var(--ink-muted);  }}
.vit-badge__dot {{ width:5px; height:5px; border-radius:50%; background:currentColor; }}

/* Vitals brand-mark utility (with wine dot) ---------------------- */
.vit-brandmark {{
    font-family: var(--font-display);
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1;
    color: var(--ink-body);
}}
.vit-brandmark::after {{
    content: ".";
    color: var(--primary);
    font-weight: 700;
    margin-left: 0.02em;
}}

/* Theme toggle button (rendered by render_theme_toggle) --------- */
.vit-theme-toggle-wrap {{
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin: 0 0 4px 0;
}}
.vit-theme-toggle-wrap [data-testid="stButton"] > button {{
    width: 34px;
    height: 34px;
    padding: 0 !important;
    border-radius: 50% !important;
    border: 1px solid var(--border) !important;
    background: var(--card-bg) !important;
    color: var(--ink-body) !important;
    line-height: 1 !important;
}}
.vit-theme-toggle-wrap [data-testid="stButton"] > button:hover {{
    border-color: var(--primary) !important;
    color: var(--primary) !important;
}}
.vit-theme-toggle-wrap [data-testid="stButton"] > button svg {{
    width: 16px;
    height: 16px;
    display: inline-block;
    vertical-align: middle;
}}
"""


# Inline SVG icons (no emoji per repo policy) — sun for "switch to light",
# moon for "switch to dark". Stroked, currentColor — inherits from button text.
_SUN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="4"/>'
    '<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41'
    'M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>'
    '</svg>'
)
_MOON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/>'
    '</svg>'
)


def _theme_attr_script(theme: str) -> str:
    """매 rerun 시 root/body 에 data-theme 와 .vitals-dark 클래스를 동기화하는
    작은 inline <script>. Streamlit 의 outer document 와 실제 컴포넌트
    iframe 사이의 attribute drift 를 방어.

    NOTE: components.py:render_chat_panel 의 chat right-pad 는 더 이상
    body 클래스 의존이 아니라 :has(#vit-chat) CSS 셀렉터 기반이므로 본
    스크립트에서 has-vit-chat 정리 로직 불필요 (제거됨).
    """
    return f"""
<script>
(function() {{
  try {{
    var t = "{theme}";
    var root = window.parent && window.parent.document
        ? window.parent.document.documentElement : document.documentElement;
    var body = window.parent && window.parent.document
        ? window.parent.document.body : document.body;
    if (root) root.setAttribute('data-theme', t);
    if (body) {{
      body.setAttribute('data-theme', t);
      if (t === 'dark') body.classList.add('vitals-dark');
      else body.classList.remove('vitals-dark');
      var apps = body.querySelectorAll('.stApp');
      apps.forEach(function(a) {{ a.setAttribute('data-theme', t); }});
    }}
  }} catch (e) {{ /* SecurityError / cross-origin: components.v1.html iframe
       으로 감싸진 컨텍스트에서는 window.parent 접근이 차단됨. 본 함수는
       st.markdown 으로 inject 되는 게 정상 사용처이므로 같은 document.
       fallback 으로 자기 document 에라도 attribute 적용을 시도한 후 무시. */
    try {{
      document.documentElement.setAttribute('data-theme', "{theme}");
      document.body && document.body.setAttribute('data-theme', "{theme}");
    }} catch (e2) {{ /* swallow */ }}
  }}
}})();
</script>
"""


def apply_vitals_theme(theme: Optional[Literal["light", "dark", "auto"]] = None) -> None:
    """모든 페이지의 첫 줄에서 호출 — 와인 팔레트 + LG EI 폰트 + Streamlit 기본 hide.

    Args:
        theme: 'light' | 'dark' | 'auto' | None
            - None (default): session_state 기반. 미설정 시 'light'. 기존 호출 사이트
              호환을 위해 NO-arg 형태로 그대로 사용 가능.
            - 'auto': session_state 사용 (None 과 동일).
            - 'light' / 'dark': 강제 지정 + session_state 동기화.

    PERF #8 — 한 페이지의 매 rerun 마다 ~1.7MB CSS 재방출하는 비용 회피:
    페이지 단위 session_state key 로 첫 진입에만 st.markdown 호출. 단,
    테마가 변경되면 강제 재방출 (data-theme 토글 + 클래스 동기화 스크립트는
    매 rerun 마다 짧게 다시 inject — 페이지 전환 후에도 다크 상태 유지 보장).
    """
    # 1) 테마 결정
    if theme in ("light", "dark"):
        _set_theme(theme)
    current = get_current_theme()

    # 2) 페이지 식별 (rerun no-op 캐시 키)
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        page_key = (ctx.page_script_hash if ctx else None) or "default"
    except Exception:
        page_key = "default"

    flag_key = f"_vitals_theme_applied__{page_key}"
    last_theme_key = f"_vitals_theme_last__{page_key}"
    needs_css = (
        not st.session_state.get(flag_key)
        or st.session_state.get(last_theme_key) != current
    )

    if needs_css:
        st.markdown(f"<style>\n{_build_css()}\n</style>", unsafe_allow_html=True)
        st.session_state[flag_key] = True
        st.session_state[last_theme_key] = current

    # 3) data-theme 속성 동기화 — 매 rerun 마다 짧은 스크립트 inject (cheap).
    #    이게 있어야 페이지 nav 후에도 dark 가 유지된다.
    st.markdown(_theme_attr_script(current), unsafe_allow_html=True)

    # 4) 사이드바에 테마 토글 + user profile + 문의 메일 자동 부착.
    #    Streamlit 위젯은 매 rerun 마다 재선언되어야 하므로 sentinel 캐싱 없이
    #    항상 호출. 사이드바가 없는 페이지 (예: login.py 는 apply_vitals_theme
    #    자체를 부르지 않음) 는 영향 없음.
    try:
        render_theme_toggle(location="sidebar")
    except Exception:
        pass
    try:
        render_sidebar_user_profile()
    except Exception:
        pass


def render_lang_picker(location: str = "sidebar") -> None:
    """Vitals 언어 선택기 — 사용자 피드백 (2026-05-08): 실 기능 구현.

    7 언어 (KO/EN/VI/PL/ID/ES/ZH) selectbox → st.session_state['vitals.lang']
    persist + 페이지 핵심 텍스트 swap (각 페이지가 _t() 헬퍼 사용 시).

    현재 구현은 demo — 사이드바 nav link 라벨은 Streamlit 자동 생성이라
    직접 swap 불가. 페이지 본문의 명시적 _t('home') 같은 호출처만 swap.
    """
    container = st.sidebar if location == "sidebar" else st
    options = [("KO", "한국어"), ("EN", "English"), ("VI", "Tiếng Việt"),
               ("PL", "Polski"), ("ID", "Bahasa Indonesia"),
               ("ES", "Español"), ("ZH", "中文")]
    current = st.session_state.get("vitals.lang", "KO")
    labels = [f"{code} · {name}" for code, name in options]
    codes = [code for code, _ in options]
    try:
        idx = codes.index(current)
    except ValueError:
        idx = 0
    picked_label = container.selectbox(
        "Lang", labels, index=idx, key="_vit_lang_picker",
        label_visibility="collapsed",
    )
    picked_code = picked_label.split(" · ")[0]
    if picked_code != current:
        st.session_state["vitals.lang"] = picked_code


# 간단 i18n dictionary — 페이지 코드가 _t('key') 로 사용.
_I18N_DICT = {
    "KO": {"home": "Home", "settings": "설정", "contact": "문의 메일"},
    "EN": {"home": "Home", "settings": "Settings", "contact": "Contact"},
    "VI": {"home": "Trang chủ", "settings": "Cài đặt", "contact": "Liên hệ"},
    "PL": {"home": "Główna", "settings": "Ustawienia", "contact": "Kontakt"},
    "ID": {"home": "Beranda", "settings": "Pengaturan", "contact": "Kontak"},
    "ES": {"home": "Inicio", "settings": "Ajustes", "contact": "Contacto"},
    "ZH": {"home": "首页", "settings": "设置", "contact": "联系"},
}


def _t(key: str, default: Optional[str] = None) -> str:
    """현재 lang 의 dict 에서 key 찾아 텍스트 반환. 미존재 시 default 또는 key 자체."""
    code = st.session_state.get("vitals.lang", "KO")
    return _I18N_DICT.get(code, {}).get(key, default if default is not None else key)


def render_sidebar_user_profile() -> None:
    """사이드바 최하단 user profile + 설정 + 문의 메일.

    사용자 피드백 (2026-05-08):
      · 항상 사이드바 최하단 sticky (CSS margin-top:auto in apply_vitals_theme).
      · 설정 버튼 = 향후 settings_modal trigger (현재 toast 알림).
      · 문의 메일 버튼 = mailto: link (이전 페이지 footer 의 sc-contact-box
        에서 사이드바로 이동).
    """
    user_email = st.session_state.get("user_email") or st.session_state.get("user_id") or ""
    user_name = st.session_state.get("user_name") or (user_email.split("@")[0] if user_email else "")
    avatar = (user_name[:2] if user_name else (user_email[:2] if user_email else "??")).upper()

    from html import escape as _e
    st.sidebar.markdown(
        f'<div class="vit-sidebar-user">'
        f'  <div class="vit-sidebar-user__avatar">{_e(avatar)}</div>'
        f'  <div class="vit-sidebar-user__body">'
        f'    <div class="vit-sidebar-user__name">{_e(user_name or "Guest")}</div>'
        f'    <div class="vit-sidebar-user__email">{_e(user_email or "—")}</div>'
        f'  </div>'
        f'</div>'
        f'<a class="vit-sidebar-user-contact" href="mailto:max.capa@lginnotek.com">'
        f'  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'       stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>'
        f'    <polyline points="22 6 12 13 2 6"/></svg>'
        f'  <span>문의 메일 보내기</span>'
        f'</a>',
        unsafe_allow_html=True,
    )


def render_theme_toggle(location: str = "sidebar") -> None:
    """테마 토글 버튼 렌더링.

    Args:
        location: 'sidebar' (기본) | 'inline' (현재 위치).

    UX:
        - 라벨은 'Dark' / 'Light' 텍스트 (이모지 금지 정책). SVG 아이콘은 옆에
          별도 markdown 으로 표시.
        - 클릭 시 session_state 토글 → DB persist (best-effort) → st.rerun()
        - DB persist 실패해도 페이지 렌더 진행 — 세션 내 토글은 항상 동작.
    """
    current = get_current_theme()
    next_theme = "dark" if current == "light" else "light"
    icon_html = _MOON_SVG if current == "light" else _SUN_SVG
    label = "Dark" if current == "light" else "Light"
    aria = f"Switch to {next_theme} mode"

    container = st.sidebar if location == "sidebar" else st

    container.markdown(
        f'<div class="vit-theme-toggle-wrap" title="{aria}">{icon_html}</div>',
        unsafe_allow_html=True,
    )
    clicked = container.button(
        label,
        key="vitals_theme_toggle",  # stable key — Streamlit 이 동일 위젯으로 추적
        help=aria,
        use_container_width=False,
    )

    if clicked:
        _set_theme(next_theme)
        # DB persist (best-effort)
        try:
            user_id = st.session_state.get("user_email") or st.session_state.get("user_id")
            if user_id:
                from .preferences import save_user_theme_pref
                save_user_theme_pref(str(user_id), next_theme)
        except Exception:
            pass
        st.rerun()


__all__ = [
    "apply_vitals_theme",
    "get_current_theme",
    "render_theme_toggle",
]
