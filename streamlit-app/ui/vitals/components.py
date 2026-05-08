"""
ui.vitals.components — 재사용 가능한 Vitals 레이아웃 컴포넌트

각 페이지가 직접 markdown HTML 을 작성하지 않고 이 함수들을 호출해
일관된 톱nav / 페이지 헤더 / 카드 / 채팅 패널을 그린다.

도면 기준: docs/design/landing.html, docs/design/home.html.
"""
from __future__ import annotations
import base64
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import streamlit as st

_ASSETS = Path(__file__).parent / "assets"


def _img_data_uri(filename: str) -> str:
    path = _ASSETS / filename
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


# 외부 페이지에서도 직접 사용 가능 (예: render_top_brand 안 img src)
LOGO_WHITE_DATA_URI = _img_data_uri("lg-innotek-logo-en-white.png")
LOGO_GRAY_DATA_URI = _img_data_uri("lg-innotek-logo-en-gray.png")


# 사이드바 7개 항목 (Intent Contract: 절대 순서·라벨 변경 X)
NAV_ITEMS: Sequence[Mapping[str, str]] = (
    {"key": "login", "label": "login",            "page": "login"},
    {"key": "home",  "label": "Home",             "page": "0_Home"},
    {"key": "cmp",   "label": "CMP Dashboard",    "page": "1_CMP_Dashboard"},
    {"key": "uph",   "label": "UPH Dashboard",    "page": "2_UPH_Dashboard"},
    {"key": "mtba",  "label": "MTBA Dashboard",   "page": "3_MTBA_Dashboard"},
    {"key": "detail","label": "MTBA Detail View", "page": "4_MTBA_Detail_View"},
    {"key": "chat",  "label": "MaxCapa Chat",     "page": "6_MaxCapa_Chat"},
)


def render_topnav(active: str = "home", show_brand: bool = True) -> None:
    """상단 가로 네비게이션. `active` = NAV_ITEMS 의 key (login/home/cmp/uph/mtba/detail/chat).
    Streamlit page links 는 st.page_link 로 라우팅 되지만 본 컴포넌트는
    시각적 일관성을 위해 markdown 으로 직접 렌더한다 (파일명 고정 라우팅).
    """
    items_html = "".join(
        f'<a class="vit-topnav__item{" vit-topnav__item--active" if item["key"] == active else ""}" '
        f'href="./{item["page"]}" target="_self">{item["label"]}</a>'
        for item in NAV_ITEMS
    )
    brand_html = ""
    if show_brand and LOGO_GRAY_DATA_URI:
        brand_html = (
            f'<div class="vit-topnav__brand">'
            f'  <img src="{LOGO_GRAY_DATA_URI}" alt="LG Innotek" class="vit-topnav__logo" />'
            f'  <span class="vit-topnav__divider"></span>'
            f'  <span class="vit-topnav__team">생산혁신센터 · Max Capa TDR</span>'
            f'</div>'
        )

    st.markdown(
        f"""
<style>
.vit-topnav {{
    display:flex; flex-direction:column; gap:0;
    margin: 0 -1rem 18px;
    padding: 0;
    background: #FFFFFF;
    border-bottom: 1px solid var(--border);
}}
.vit-topnav__row1 {{
    display:flex; align-items:center; justify-content:space-between;
    padding: 12px 24px 10px;
}}
.vit-topnav__brand {{ display:flex; align-items:center; gap:12px; }}
.vit-topnav__logo {{ height: 22px; width:auto; display:block; }}
.vit-topnav__divider {{ width:1px; height:18px; background: var(--border); }}
.vit-topnav__team {{ font-family: var(--font-mono); font-size:11px; font-weight:600;
    letter-spacing:.08em; color: var(--ink-subtle); text-transform: uppercase; }}
.vit-topnav__row2 {{
    display:flex; align-items:center; gap:0;
    padding: 0 16px;
    overflow-x: auto;
}}
.vit-topnav__item {{
    display:inline-flex; align-items:center;
    height:42px; padding: 0 16px;
    font-size:13px; font-weight:600;
    color: var(--ink-muted); text-decoration:none;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: color .12s, border-color .12s;
    white-space: nowrap;
}}
.vit-topnav__item:hover {{ color: var(--ink-body); }}
.vit-topnav__item--active {{
    color: var(--ink-body);
    border-bottom-color: var(--primary);
}}
</style>
<nav class="vit-topnav" role="navigation">
  <div class="vit-topnav__row1">
    {brand_html}
  </div>
  <div class="vit-topnav__row2">
    {items_html}
  </div>
</nav>
""",
        unsafe_allow_html=True,
    )


def render_page_header(eyebrow: str, title: str, sub: str = "", actions_html: str = "") -> None:
    """페이지 헤더 — eyebrow + H1 + sub + 우측 액션 슬롯."""
    actions_block = (
        f'<div class="vit-pagehead__actions">{actions_html}</div>' if actions_html else ""
    )
    st.markdown(
        f"""
<style>
.vit-pagehead {{
    display:flex; justify-content:space-between; align-items:flex-end;
    gap:24px; margin-bottom: 22px; flex-wrap:wrap;
}}
.vit-pagehead__main {{ flex:1; min-width:0; }}
.vit-pagehead__eyebrow {{
    font-size:11px; font-weight:700; text-transform:uppercase;
    letter-spacing:.1em; color: var(--ink-subtle); margin-bottom:8px;
}}
.vit-pagehead__title {{
    margin:0 0 6px; font-family: var(--font-display);
    font-size:32px; font-weight:700; letter-spacing:-0.025em;
    line-height:1.05; color: var(--ink-body);
}}
.vit-pagehead__sub {{
    margin:0; font-size:14px; color: var(--ink-muted); max-width:780px;
}}
</style>
<header class="vit-pagehead">
  <div class="vit-pagehead__main">
    <div class="vit-pagehead__eyebrow">{eyebrow}</div>
    <h1 class="vit-pagehead__title">{title}</h1>
    {f'<p class="vit-pagehead__sub">{sub}</p>' if sub else ''}
  </div>
  {actions_block}
</header>
""",
        unsafe_allow_html=True,
    )


def render_card(
    title: str,
    desc: str = "",
    badge: tuple[str, str] | None = None,  # (label, kind: "good"|"warn"|"subtle")
    meta: str = "",
    href: str = "#",
    icon_svg: str = "",
    disabled: bool = False,
) -> None:
    """단일 도구 카드 (S2 Home 스타일). 클릭하면 href 로 이동.
    Streamlit 안에서 markdown 으로 렌더되므로 폼 액션 등은 별도 컴포넌트로 처리.
    """
    badge_html = ""
    if badge:
        label, kind = badge
        badge_html = (
            f'<span class="vit-badge vit-badge--{kind}">'
            f'<span class="vit-badge__dot"></span>{label}</span>'
        )
    icon_html = (
        f'<div class="vit-card__icon">{icon_svg}</div>' if icon_svg else ""
    )
    disabled_attr = ' aria-disabled="true"' if disabled else ""

    st.markdown(
        f"""
<a class="vit-card" href="{href}" target="_self"{disabled_attr}>
  <div class="vit-card__head">
    {icon_html}
    {badge_html}
  </div>
  <div class="vit-card__body">
    <h3 class="vit-card__title">{title}</h3>
    {f'<p class="vit-card__desc">{desc}</p>' if desc else ''}
  </div>
  {f'<div class="vit-card__foot"><span>{meta}</span><span class="vit-card__arrow">→</span></div>' if meta else ''}
</a>
""",
        unsafe_allow_html=True,
    )


# 카드 그리드 글로벌 CSS (한 페이지에 한 번만 주입되도록 theme.py 에서 관리해도 됨)
CARD_GRID_CSS = """
<style>
.vit-card-grid {
    display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin-bottom:32px;
}
@media (max-width:1280px) { .vit-card-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width:980px)  { .vit-card-grid { grid-template-columns: 1fr; } }
.vit-card {
    display:flex; flex-direction:column; gap:14px; padding:20px;
    background: var(--card-bg); border:1px solid var(--border); border-radius:10px;
    position:relative; transition: border-color .15s, box-shadow .15s;
    min-height:160px; overflow:hidden;
    color: inherit; text-decoration:none;
}
.vit-card::before {
    content:""; position:absolute; left:0; top:0; bottom:0; width:0;
    background: var(--primary); transition: width .15s ease;
}
.vit-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-card); }
.vit-card:hover::before { width:3px; }
.vit-card[aria-disabled="true"] { cursor: not-allowed; opacity: 0.7; }
.vit-card[aria-disabled="true"]:hover { border-color: var(--border); box-shadow: none; }
.vit-card[aria-disabled="true"]:hover::before { width:0; }

.vit-card__head { display:flex; justify-content:space-between; align-items:flex-start; gap:10px; }
.vit-card__icon { width:36px; height:36px; border-radius:8px; background: var(--soft);
    display:flex; align-items:center; justify-content:center; flex:none; color: var(--ink-body); }
.vit-card__icon svg { width:18px; height:18px; }
.vit-card:hover .vit-card__icon { background: var(--primary-tint); color: var(--primary-dark); }
.vit-card__body { display:flex; flex-direction:column; gap:4px; flex:1; min-width:0; }
.vit-card__title { margin:0; font-family: var(--font-display); font-size:15px; font-weight:700;
    letter-spacing:-0.01em; color: var(--ink-body); }
.vit-card__desc  { margin:0; font-size:13px; color: var(--ink-muted); line-height:1.5; }
.vit-card__foot {
    display:flex; justify-content:space-between; align-items:center;
    margin-top:auto; padding-top:8px; border-top: 1px dashed var(--border);
    font-family: var(--font-mono); font-size:11px; color: var(--ink-subtle); letter-spacing:.04em;
}
.vit-card__arrow { color: var(--primary); font-family: var(--font-mono); font-size:14px;
    opacity:0; transform: translateX(-4px); transition: opacity .15s, transform .15s; }
.vit-card:hover .vit-card__arrow { opacity:1; transform: translateX(0); }
</style>
"""


def render_chat_panel(
    title: str = "MaxCapa Chat",
    placeholder: str = "질문을 입력하세요 — 예) FOL-A R50 7일 ITAS UPH 추이",
    examples: Iterable[str] = (
        "FOL-A R50 최근 7일 ITAS UPH 추이",
        "어제 MTBA Top 10",
        "Lens AA 공정 30일 알람 추이",
        "R53A APS Test 이번주 평균 UPH",
    ),
) -> None:
    """우측 고정 리사이저블 채팅 패널 (S8 MaxCapa Chat).
    `position: fixed` 라 페이지 본문 위에 띄우는 구조. 페이지 본문엔
    `padding-right: var(--vit-chat-w, 360px)` 식으로 여백 주는 책임이
    호출자에게 있다 (페이지마다 채팅 표시 여부가 다를 수 있음).
    """
    examples_html = "".join(
        f'<button type="button" class="vit-chat__ex">{ex}</button>'
        for ex in examples
    )

    st.markdown(
        f"""
<style>
:root {{ --vit-chat-w: 360px; }}
.vit-chat {{
    position: fixed;
    top: 0; right: 0; bottom: 0;
    width: var(--vit-chat-w);
    background: #FFFFFF;
    border-left: 1px solid var(--border);
    box-shadow: -8px 0 24px -8px rgba(15,17,21,0.06);
    display:flex; flex-direction:column;
    z-index: 50;
    transition: width .15s ease;
}}
.vit-chat__resize {{
    position:absolute; left:-2px; top:0; bottom:0;
    width: 4px; cursor: col-resize;
    background: transparent;
}}
.vit-chat__resize:hover {{ background: var(--primary-tint); }}
.vit-chat__head {{
    display:flex; justify-content:space-between; align-items:center;
    padding: 14px 16px; border-bottom: 1px solid var(--border);
}}
.vit-chat__title {{ margin:0; font-family: var(--font-display); font-size:15px;
    font-weight:700; letter-spacing:-0.01em; color: var(--ink-body); }}
.vit-chat__title::after {{ content:"."; color: var(--primary); margin-left:1px; }}
.vit-chat__collapse {{
    background:transparent; border:0; cursor:pointer;
    color: var(--ink-muted); font-family: var(--font-mono);
    font-size:11px; padding:4px 6px;
}}
.vit-chat__body {{ flex:1; overflow-y:auto; padding: 16px;
    display:flex; flex-direction:column; gap:12px; }}
.vit-chat__hint {{
    background:#FFFFFF; border:1px solid var(--border); border-left: 4px solid var(--primary);
    border-radius: var(--radius); padding:10px 12px; font-size:12px; color: var(--ink-body);
    line-height:1.5;
}}
.vit-chat__hint code {{
    font-family: var(--font-mono); background: var(--soft);
    padding: 1px 6px; border-radius: 4px; font-size:11px;
    color: var(--primary-dark); font-weight:600;
}}
.vit-chat__ex-list {{ display:flex; flex-direction:column; gap:6px; }}
.vit-chat__ex {{
    text-align:left; background:transparent; border: 1px solid var(--border);
    border-radius: var(--radius); padding: 8px 10px;
    font-size:12px; color: var(--ink-body); cursor:pointer;
    transition: border-color .12s, background .12s;
}}
.vit-chat__ex:hover {{ border-color: var(--primary); background: var(--primary-tint); }}
.vit-chat__composer {{
    border-top: 1px solid var(--border);
    padding: 10px 12px;
    background: #FFFFFF;
    display:flex; flex-direction:column; gap:6px;
}}
.vit-chat__textarea {{
    width:100%; min-height:60px; resize:vertical;
    border: 1px solid var(--border-strong); border-radius: var(--radius);
    padding: 10px 12px; font-family: var(--font-body); font-size:14px;
    color: var(--ink-body); outline: none;
}}
.vit-chat__textarea:focus {{
    border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-tint);
}}
.vit-chat__send {{
    align-self: flex-end;
    background: var(--primary); color:#FFFFFF;
    border:0; border-radius: var(--radius);
    padding: 8px 14px; font-weight:700; font-size:13px; cursor:pointer;
}}
.vit-chat__send:hover {{ background: var(--primary-dark); }}

/* 본문이 채팅 패널 만큼 우측 여백 가지도록 — :has() 셀렉터 (Chrome 105+ /
   Safari 15.4+ / Firefox 121+) 로 JS 의존 없이 처리. Streamlit 의 st.markdown
   이 inline <script> 를 sanitize 하는 버전에서도 안전. */
body:has(#vit-chat) .block-container {{
    padding-right: calc(var(--vit-chat-w) + 24px) !important;
}}
</style>
<aside class="vit-chat" id="vit-chat" aria-label="MaxCapa Chat">
  <header class="vit-chat__head">
    <h3 class="vit-chat__title">{title}</h3>
    <button type="button" class="vit-chat__collapse" aria-label="collapse"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg></button>
  </header>
  <div class="vit-chat__body">
    <div class="vit-chat__hint">
      기본 조회는 MES UPH(<code>uph_input_runtime_daily_model</code>),
      질문에 ITAS 를 명시하면 ITAS UPH(<code>itas_uph_result</code>)로 분기합니다.
    </div>
    <div class="vit-chat__eyebrow" style="font-size:10px;font-weight:700;
         letter-spacing:.1em;color:var(--ink-subtle);text-transform:uppercase;
         margin-top:4px;">지원 예시</div>
    <div class="vit-chat__ex-list">
      {examples_html}
    </div>
  </div>
  <div class="vit-chat__composer">
    <textarea class="vit-chat__textarea" placeholder="{placeholder}"></textarea>
    <button type="button" class="vit-chat__send">질문 분석 및 실행 <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg></button>
  </div>
</aside>
<!--
  이전 버전엔 inline <script> 로 (1) body.has-vit-chat 클래스 부여 (2) drag
  resize (3) localStorage 폭 복원 — 총 ~50줄. 그러나 Streamlit 의 일부
  버전이 st.markdown 의 <script> 를 sanitize 해서 dead code 였음.
  - (1) 본문 padding 은 위 :has() 로 대체.
  - (2) drag resize 는 핵심 기능 아님 — 제거. 원할 시 streamlit_extras 의
        custom Component 또는 components.v1.html iframe 로 재도입.
  - (3) localStorage 폭은 사용자가 모르는 기능이라 제거 무영향.
-->
""",
        unsafe_allow_html=True,
    )


_GLOBE_SVG = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="10"/>'
    '<line x1="2" y1="12" x2="22" y2="12"/>'
    '<path d="M12 2 a15 15 0 0 1 0 20 a15 15 0 0 1 0 -20"/>'
    '</svg>'
)
_CHEVRON_DOWN_SVG = (
    '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<polyline points="6 9 12 15 18 9"/>'
    '</svg>'
)


def render_lang_switcher(default: str = "KO") -> None:
    """톱nav 우측 언어 스위처 (장식용 — 실제 i18n 은 페이지에서 처리).

    AI-slop 방지: emoji 사용 금지 정책에 따라 stroked SVG 글로브 + chevron 사용.
    """
    st.markdown(
        f"""
<style>
.vit-lang {{ display:inline-flex; align-items:center; gap:6px;
    height:28px; padding:0 10px; background:#FFFFFF;
    border:1px solid var(--border); border-radius: var(--radius);
    font-family: var(--font-mono); font-size:11px; font-weight:600;
    color: var(--ink-body); cursor:pointer; }}
.vit-lang:hover {{ border-color: var(--border-strong); background: var(--soft); }}
.vit-lang svg {{ display:block; }}
</style>
<button type="button" class="vit-lang">{_GLOBE_SVG} {default} {_CHEVRON_DOWN_SVG}</button>
""",
        unsafe_allow_html=True,
    )


# ============================================================================
# STAGE 2 primitives — preview HTML 의 시각 구조를 streamlit-app 페이지에서
# 재사용하기 위한 함수 모음. 모든 함수는 CSS-only injection (st.markdown
# unsafe_allow_html=True) — 인터랙션이 필요한 모달/필터 적용은 Streamlit
# native 위젯 (st.dialog / st.button / st.toast / st.download_button) 으로
# bridge 한다. 인라인 <script> 는 st.markdown 에서 stripped 되므로 절대 의존 X.
# ============================================================================

# 페이지별 CSS 중복 주입 방지 sentinel.
_CSS_FLAG_KEY = "_vitals_components_css_injected"


def _inject_components_css_once() -> None:
    """모든 primitive 가 공유하는 CSS 를 페이지당 1회만 주입.

    이전엔 각 render_* 가 자체 <style> 블록을 출력해서 rerun 마다 중복 주입.
    이 함수는 st.session_state 에 sentinel 을 두고 1회만 emit.
    """
    if st.session_state.get(_CSS_FLAG_KEY):
        return
    st.session_state[_CSS_FLAG_KEY] = True
    st.markdown(
        """
<style>
/* === Vitals primitives — 공유 CSS (페이지당 1회) ===================== */

/* render_top_strip: 페이지 상단 6px 와인 가로 (Vitals identity) */
.vit-top-strip { height:6px; background: var(--primary); margin: 0 -1rem 12px; }

/* render_sub_head: 좌측 4px 와인 세로 + 제목 + 메타 */
.vit-sub-head { display:flex; align-items:center; gap:10px;
    padding: 6px 0 8px; margin: 14px 0 12px;
    border-bottom: 1px solid var(--border); }
.vit-sub-head__bar { width:4px; height:18px; background: var(--primary);
    flex: 0 0 auto; }
.vit-sub-head__title { font-family: var(--font-display);
    font-size:15px; font-weight:600; color: var(--ink-body); margin:0;
    line-height:1.2; }
.vit-sub-head__meta { margin-left:auto; font-size:11px;
    color: var(--ink-muted); }

/* render_nav_card: 좌측 3px 와인 세로 + 제목/설명 */
.vit-nav-card-grid { display:grid; grid-template-columns: repeat(3, 1fr);
    gap: 14px; margin: 12px 0 18px; }
.vit-nav-card { position:relative; padding: 14px 16px 14px 22px;
    background: var(--card-bg); border: 1px solid var(--border);
    text-decoration:none; color: var(--ink-body);
    transition: border-color 120ms; }
.vit-nav-card::before { content:""; position:absolute; left:0; top:0;
    bottom:0; width:3px; background: var(--primary); }
.vit-nav-card:hover { border-color: var(--primary); }
.vit-nav-card__title { font-family: var(--font-display);
    font-size:14px; font-weight:600; color: var(--ink-body);
    margin: 0 0 4px; }
.vit-nav-card__desc { font-size:12px; color: var(--ink-muted); margin:0;
    line-height: 1.45; }

/* render_toast 의 컨테이너 — Streamlit st.toast 가 이미 native 토스트를
   제공하므로 본 클래스는 fallback / 추가 스타일링용 */
.vit-toast-host { position:fixed; right:16px; bottom:16px; z-index:9999;
    display:flex; flex-direction:column; gap:8px; pointer-events:none; }

/* render_sidebar_tree: 사이드바 트리 그룹 헤드 + 자식 링크 */
.vit-tree-group { padding: 4px 0 8px; }
.vit-tree-group__head { display:flex; align-items:center; gap:6px;
    padding: 6px 8px; font-family: var(--font-display);
    font-size:12px; font-weight:600; color: var(--ink-muted);
    letter-spacing: 0.04em; text-transform: uppercase; cursor:pointer;
    user-select:none; }
.vit-tree-group__caret { width:10px; height:10px; transition: transform 120ms; }
.vit-tree-group.is-collapsed .vit-tree-group__caret { transform: rotate(-90deg); }
.vit-tree-group__list { padding: 2px 0 0 6px; }
.vit-tree-group.is-collapsed .vit-tree-group__list { display:none; }
.vit-tree-link { display:flex; align-items:center; gap:8px;
    padding: 6px 10px 6px 14px; position:relative;
    font-size: 13px; color: var(--ink-body);
    text-decoration:none; line-height:1.3; }
.vit-tree-link:hover { background: var(--soft); }
.vit-tree-link.is-active { font-weight: 600; color: var(--ink-body); }
.vit-tree-link.is-active::before { content:""; position:absolute;
    left:0; top:6px; bottom:6px; width:3px; background: var(--primary); }
</style>
""",
        unsafe_allow_html=True,
    )


def render_top_strip() -> None:
    """페이지 최상단 와인 6px 가로 strip (Vitals identity bar).

    사용: 모든 sc-page-section 도입부에 1회. 매 페이지 진입 시 동일 위치.
    """
    _inject_components_css_once()
    st.markdown('<div class="vit-top-strip" aria-hidden="true"></div>',
                unsafe_allow_html=True)


def render_sub_head(title: str, meta: str = "") -> None:
    """좌측 4px 와인 세로 + 제목 + 우측 메타 텍스트.

    사용: sc-page-section 안의 sub-head 영역. preview 에선 cmp-sub-head 와 동등.
    HTML 만 주입 — 인터랙션 없음. Streamlit 의 unsafe_allow_html sanitizer 가
    title/meta 의 HTML 을 그대로 통과시키므로 호출 측에서 escape 책임.
    """
    _inject_components_css_once()
    from html import escape as _e
    meta_html = (
        f'<span class="vit-sub-head__meta">{_e(str(meta))}</span>' if meta else ""
    )
    st.markdown(
        f'<div class="vit-sub-head">'
        f'  <span class="vit-sub-head__bar" aria-hidden="true"></span>'
        f'  <h3 class="vit-sub-head__title">{_e(str(title))}</h3>'
        f'  {meta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_nav_card_grid(cards: Sequence[Mapping[str, str]]) -> None:
    """3-열 nav 카드 그리드. 각 카드 = {title, desc, page} dict.

    page 는 streamlit-app/pages/ 의 파일명 stem (예: "1_CMP_Dashboard").
    href 는 ./<page> 로 root-relative — Streamlit 의 default routing 과 일치.
    """
    _inject_components_css_once()
    from html import escape as _e
    items = "".join(
        f'<a class="vit-nav-card" href="./{_e(c["page"])}" target="_self">'
        f'  <p class="vit-nav-card__title">{_e(c["title"])}</p>'
        f'  <p class="vit-nav-card__desc">{_e(c.get("desc", ""))}</p>'
        f'</a>'
        for c in cards
    )
    st.markdown(f'<div class="vit-nav-card-grid">{items}</div>',
                unsafe_allow_html=True)


def render_toast(message: str, *, kind: str = "info") -> None:
    """Streamlit native st.toast 로 사용자 피드백 emit.

    kind: "info" / "success" / "warning" / "error" — Streamlit 1.27+ 의
    st.toast 는 icon 만 받으므로 kind 별 icon 매핑.
    """
    icon_map = {"info": "i", "success": "✓", "warning": "!", "error": "x"}
    icon = icon_map.get(kind, "i")
    st.toast(message, icon=icon)


def render_csv_export(df, *, label: str = "CSV 내려받기",
                      filename: str = "export.csv",
                      key: str | None = None) -> None:
    """Streamlit native st.download_button 으로 CSV 다운로드.

    UTF-8 BOM 포함 (Excel 한글 호환). df 는 pandas.DataFrame.
    """
    csv_bytes = ("﻿" + df.to_csv(index=False)).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv; charset=utf-8",
        key=key,
        use_container_width=False,
    )


def render_modal_static(title: str, body_html: str, *,
                        modal_id: str,
                        close_label: str = "닫기") -> None:
    """정적 (display-only) 모달 — preview HTML 의 .vit-modal-backdrop 패턴 재현.

    JS 인터랙션이 필요한 (트리거 버튼 클릭, ESC, backdrop 클릭) 경우엔
    st.dialog (Streamlit native) 를 쓰는 게 안전함. 본 함수는 단순 표시용.

    body_html 은 호출 측에서 escape 한 안전한 HTML 만 전달할 것.
    """
    _inject_components_css_once()
    from html import escape as _e
    title_e = _e(str(title))
    cl_e = _e(str(close_label))
    mid = _e(str(modal_id))
    st.markdown(
        f'<div class="vit-modal-backdrop" id="{mid}" aria-hidden="false">'
        f'  <div class="vit-modal" role="dialog" aria-modal="true" '
        f'       aria-labelledby="{mid}-title">'
        f'    <div class="vit-modal__head">'
        f'      <h3 class="vit-modal__title" id="{mid}-title">{title_e}</h3>'
        f'      <button type="button" class="vit-modal__close" '
        f'              aria-label="{cl_e}">×</button>'
        f'    </div>'
        f'    <div class="vit-modal__body">{body_html}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_sidebar_tree(groups: Sequence[Mapping[str, object]],
                        active_key: str = "") -> None:
    """사이드바 트리 그룹 (Home / MTBA 등).

    groups = [{"label": "Home", "items": [{"key":"home","label":"홈","page":"0_Home"}, ...]}]
    active_key 와 일치하는 자식 링크에 .is-active 와 와인 bar 표시.
    """
    _inject_components_css_once()
    from html import escape as _e
    parts = []
    for g in groups:
        items = g.get("items", []) or []
        any_active = any(it.get("key") == active_key for it in items)
        head_label = _e(str(g.get("label", "")))
        item_html = "".join(
            f'<a class="vit-tree-link{" is-active" if it.get("key") == active_key else ""}" '
            f'   href="./{_e(str(it.get("page","")))}" target="_self">'
            f'  {_e(str(it.get("label","")))}</a>'
            for it in items
        )
        collapsed_cls = "" if any_active else " is-collapsed"
        parts.append(
            f'<div class="vit-tree-group{collapsed_cls}">'
            f'  <div class="vit-tree-group__head">'
            f'    <span class="vit-tree-group__caret">{_CHEVRON_DOWN_SVG}</span>'
            f'    <span>{head_label}</span>'
            f'  </div>'
            f'  <div class="vit-tree-group__list">{item_html}</div>'
            f'</div>'
        )
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_filter_block(*, on_apply: str = "조회",
                        on_reset: str = "초기화") -> dict:
    """cmp-filter 의 행 — 모델/공정/기간 필터.

    Streamlit native 위젯 사용 (selectbox / multiselect / date_input) 으로
    인터랙션 = st.session_state 통한 rerun. 호출자가 with-block 안에서
    위젯들을 자유 배치하고, 본 함수는 button 두 개만 표준으로 emit.

    Returns: {"apply": bool, "reset": bool} — 클릭 여부.

    예:
        with st.container():
            render_sub_head("Filters", "모델·공정·기간")
            col1, col2, col3, col4 = st.columns([2,2,2,2])
            with col1: model = st.selectbox(...)
            ...
            actions = render_filter_block()
            if actions["reset"]: ...
            if actions["apply"]: ...
    """
    _inject_components_css_once()
    cols = st.columns([1, 1, 6])
    apply_clicked = cols[0].button(on_apply, type="primary", key="_vit_filter_apply",
                                    use_container_width=True)
    reset_clicked = cols[1].button(on_reset, key="_vit_filter_reset",
                                    use_container_width=True)
    return {"apply": bool(apply_clicked), "reset": bool(reset_clicked)}
