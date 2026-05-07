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
            f'  <span class="vit-topnav__team">생산혁신센터 · Max Capa 팀</span>'
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

/* 본문이 채팅 패널 만큼 우측 여백 가지도록 호출자에서 .has-vit-chat 부여 */
body.has-vit-chat .block-container {{ padding-right: calc(var(--vit-chat-w) + 24px) !important; }}
</style>
<aside class="vit-chat" id="vit-chat" aria-label="MaxCapa Chat">
  <div class="vit-chat__resize" id="vit-chat-resize"></div>
  <header class="vit-chat__head">
    <h3 class="vit-chat__title">{title}</h3>
    <button type="button" class="vit-chat__collapse" aria-label="collapse">▸</button>
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
    <button type="button" class="vit-chat__send">질문 분석 및 실행 ▸</button>
  </div>
</aside>
<script>
(function() {{
    document.body.classList.add('has-vit-chat');
    var panel = document.getElementById('vit-chat');
    var handle = document.getElementById('vit-chat-resize');
    if (!panel || !handle) return;

    // localStorage 에서 폭 복원
    var saved = parseInt(localStorage.getItem('vitals.chat.w'), 10);
    if (saved && saved >= 280 && saved <= 720) {{
        document.documentElement.style.setProperty('--vit-chat-w', saved + 'px');
    }}

    // drag resize
    var dragging = false, startX = 0, startW = 0;
    function onMove(e) {{
        if (!dragging) return;
        var x = e.touches ? e.touches[0].clientX : e.clientX;
        var w = startW - (x - startX);
        if (w < 280) w = 280;
        if (w > 720) w = 720;
        document.documentElement.style.setProperty('--vit-chat-w', w + 'px');
    }}
    function onUp() {{
        if (!dragging) return;
        dragging = false;
        document.body.style.userSelect = '';
        var w = parseInt(getComputedStyle(document.documentElement)
                .getPropertyValue('--vit-chat-w'), 10);
        if (w) localStorage.setItem('vitals.chat.w', String(w));
    }}
    handle.addEventListener('mousedown', function(e) {{
        dragging = true;
        startX = e.clientX;
        startW = panel.offsetWidth;
        document.body.style.userSelect = 'none';
    }});
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    handle.addEventListener('touchstart', function(e) {{
        dragging = true;
        startX = e.touches[0].clientX;
        startW = panel.offsetWidth;
    }}, {{passive: true}});
    document.addEventListener('touchmove', onMove, {{passive: true}});
    document.addEventListener('touchend', onUp);
}})();
</script>
""",
        unsafe_allow_html=True,
    )


def render_lang_switcher(default: str = "KO") -> None:
    """톱nav 우측 언어 스위처 (장식용 — 실제 i18n 은 페이지에서 처리)."""
    st.markdown(
        f"""
<style>
.vit-lang {{ display:inline-flex; align-items:center; gap:6px;
    height:28px; padding:0 10px; background:#FFFFFF;
    border:1px solid var(--border); border-radius: var(--radius);
    font-family: var(--font-mono); font-size:11px; font-weight:600;
    color: var(--ink-body); cursor:pointer; }}
.vit-lang:hover {{ border-color: var(--border-strong); background: var(--soft); }}
</style>
<button type="button" class="vit-lang">🌐 {default} ▾</button>
""",
        unsafe_allow_html=True,
    )
