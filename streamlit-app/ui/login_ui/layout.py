import streamlit as st
import streamlit.components.v1 as components

# Vitals 컴포넌트 — LG Innotek 로고 PNG 를 base64 data URI 로 (외부 의존 0)
from ui.vitals import LOGO_WHITE_DATA_URI


def render_left_panel_background():
    st.markdown(
        """
        <div class="left-panel-bg"></div>
        """,
        unsafe_allow_html=True
    )


def render_top_brand():
    """상단 브랜드 행 — 다크 비디오 배경 위에 흰 LG Innotek 공식 로고 PNG +
    구분선 + 팀명 + 우측 ALL SYSTEMS OPERATIONAL 상태."""
    st.markdown(
        f"""
        <div class="landing-topbar">
            <div class="landing-brand">
                <img src="{LOGO_WHITE_DATA_URI}" alt="LG Innotek"
                     class="landing-brand__logo" />
                <span class="landing-brand__divider"></span>
                <span class="landing-brand__team">광학 MaxCapa TDR · 광학솔루션사업부 · 생산혁신센터 · Max Capa팀</span>
            </div>
            <div class="landing-status">ALL SYSTEMS OPERATIONAL</div>
        </div>
        <style>
        .landing-brand__logo {{
            height: 22px; width: auto; display: block;
            /* 흰 PNG — 다크 배경에 자연스럽게 올라감 */
        }}
        .landing-brand__name {{ display: none; }}  /* 텍스트 워드마크 폐기 */
        </style>
        """,
        unsafe_allow_html=True
    )


def render_auth_intro():
    st.markdown(
        """
        <div class="auth-eyebrow">PRODUCTIVITY ANALYTICS · SIGN IN</div>
        <h2 class="auth-title">&nbsp;&nbsp;로그인</h2>
        <p class="auth-sub">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;사내 계정 아이디만 입력하세요.</p>
        """,
        unsafe_allow_html=True
    )


def render_identity_block():
    """Vitals 브랜드 hero — 우리 landing.html 처럼 LG EI Headline 큰 타이포 + 와인 점."""
    st.markdown(
        """
        <div class="identity-block">
            <h3 class="identity-name">Vitals<span class="dot">.</span></h3>
            <p class="identity-sub">공정의 호흡을 데이터로 듣다.</p>
            <p class="identity-bu">광학솔루션 사업부 · CMP · UPH · MTBA · MaxCapa Chat</p>
        </div>
        <style>
        /* identity 블록 폰트를 LG EI Headline 으로 교체 + 56px hero 타이포 */
        .identity-name {
            font-family: var(--font-display) !important;
            font-size: 56px !important;
            font-weight: 700 !important;
            letter-spacing: -0.04em !important;
            line-height: 0.95 !important;
            color: var(--on-dark) !important;
            margin: 0 !important;
        }
        .identity-name .dot { color: var(--primary) !important; }
        .identity-sub {
            font-family: var(--font-body) !important;
            font-size: 18px !important;
            font-weight: 500 !important;
            color: var(--on-dark) !important;
            opacity: 0.92;
            margin: 14px 0 0 !important;
            letter-spacing: -0.01em !important;
            line-height: 1.4;
        }
        .identity-bu {
            font-family: var(--font-mono) !important;
            font-size: 11px !important;
            color: var(--on-dark-subtle) !important;
            letter-spacing: .08em !important;
            text-transform: uppercase;
            margin: 12px 0 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_system_status_panel():
    html = """
    <html>
    <head>
        <style>
            body {
                margin: 0;
                font-family: "Pretendard", "Malgun Gothic", sans-serif;
                background: transparent;
                color: white;
            }

            .status-card {
                width: 100%;
                /* Vitals 'rectangles only' — radius 제거 (status dot 원은 functional). */
                background: rgba(10,12,16,0.54);
                border: 1px solid rgba(255,255,255,0.10);
                box-shadow:
                    0 14px 30px rgba(0,0,0,0.18),
                    inset 0 1px 0 rgba(255,255,255,0.04);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                padding: 14px 16px 10px 16px;
                box-sizing: border-box;
            }

            .status-card-head {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
            }

            .status-card-title {
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: .1em;
                color: rgba(255,255,255,0.72);
                line-height: 1.2;
            }

            .status-card-hint {
                font-size: 10px;
                color: rgba(255,255,255,0.5);
                letter-spacing: .05em;
                line-height: 1.2;
            }

            .status-divider-line {
                border-top: 1px dashed rgba(255,255,255,0.08);
                margin: 4px 0;
            }

            .status-row {
                display: grid;
                grid-template-columns: 14px 1fr 70px;
                align-items: center;
                column-gap: 10px;
                padding: 6px 0;
            }

            .status-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                display: inline-block;
            }

            .status-dot--green {
                background: #1F8B4C;
                box-shadow: 0 0 0 3px rgba(31,139,76,0.18);
            }

            .status-dot--yellow {
                background: #B57F1B;
                box-shadow: 0 0 0 3px rgba(181,127,27,0.18);
            }

            .status-dot--red {
                background: #B23A48;
                box-shadow: 0 0 0 3px rgba(178,58,72,0.20);
            }

            .status-dot--x {
                width: 14px;
                height: 14px;
                border-radius: 0;
                box-shadow: none;
                color: rgba(255,255,255,0.75);
                font-size: 12px;
                line-height: 14px;
                text-align: center;
                font-weight: 700;
            }

            .status-label {
                min-width: 0;
                text-align: left;
                line-height: 1.25;
                color: rgba(255,255,255,0.92);
                font-size: 12px;
                font-weight: 500;
                word-break: keep-all;
            }

            .status-detail {
                text-align: right;
                color: rgba(255,255,255,0.56);
                font-size: 11px;
                font-weight: 500;
                line-height: 1.2;
                white-space: nowrap;
            }
        </style>
    </head>
    <body>
        <div class="status-card">
            <div class="status-card-head">
                <div class="status-card-title">SYSTEM STATUS</div>
                <div class="status-card-hint">last check 23:50</div>
            </div>
            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--green"></span>
                <div class="status-label">PostgreSQL (DB 접속 가능 여부)</div>
                <div class="status-detail">84 ms</div>
            </div>

            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--yellow"></span>
                <div class="status-label">Fast API (백엔드 서비스 사용 가능 여부)</div>
                <div class="status-detail">132 ms</div>
            </div>

            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--red"></span>
                <div class="status-label">vLLM API(대화형 AI 사용 가능 여부)</div>
                <div class="status-detail">612 ms</div>
            </div>

            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--green"></span>
                <div class="status-label">MES Refresh(최신 Data 업데이트 날짜)</div>
                <div class="status-detail">5/6</div>
            </div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=230, scrolling=False)

def render_patch_notes_panel(patch_posts):
    rows_html = ""

    # 최근 변동일 찾기 (태그 구분 없이 가장 최신 날짜)
    latest_update_str = "-"

    if patch_posts:
        latest_dt = max(created_at for _, _, _, created_at in patch_posts)
        latest_update_str = f"{latest_dt.month}/{latest_dt.day}"

    if not patch_posts:
        rows_html = """
        <div class="patch-empty">표시할 패치노트가 없습니다.</div>
        """
    else:
        for idx, (post_id, tag, title, created_at) in enumerate(patch_posts):
            tag_upper = (tag or "").upper()

            if tag_upper == "NEW":
                tag_class = "patch-tag-pill patch-tag-pill--new"
            elif tag_upper == "UPD":
                tag_class = "patch-tag-pill patch-tag-pill--upd"
            elif tag_upper == "FIX":
                tag_class = "patch-tag-pill patch-tag-pill--fix"
            else:
                tag_class = "patch-tag-pill patch-tag-pill--default"

            divider_html = '<div class="patch-divider-line"></div>' if idx > 0 else ""

            rows_html += f"""
            {divider_html}
            <div class="patch-row">
                <div class="patch-row-date">{created_at.strftime('%m-%d')}</div>
                <div class="patch-row-tag">
                    <span class="{tag_class}">{tag_upper}</span>
                </div>
                <div class="patch-row-title">
                    {title}
                </div>
            </div>
            """

    html = f"""
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                font-family: "Pretendard", "Malgun Gothic", sans-serif;
                background: transparent;
                color: white;
            }}

            .patch-card {{
                width: 100%;
                /* Vitals 'rectangles only' — radius 제거. */
                background: rgba(10,12,16,0.54);
                border: 1px solid rgba(255,255,255,0.10);
                box-shadow:
                    0 14px 30px rgba(0,0,0,0.18),
                    inset 0 1px 0 rgba(255,255,255,0.04);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                padding: 14px 16px 10px 16px;
                box-sizing: border-box;
            }}

            .patch-card-head {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
            }}

            .patch-card-title {{
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: .1em;
                color: rgba(255,255,255,0.72);
                line-height: 1.2;
            }}

            .patch-card-hint {{
                font-size: 10px;
                color: rgba(255,255,255,0.5);
                letter-spacing: .05em;
                line-height: 1.2;
            }}

            .patch-divider-line {{
                border-top: 1px dashed rgba(255,255,255,0.08);
                margin: 4px 0;
            }}

            .patch-row {{
                display: grid;
                grid-template-columns: 52px 56px 1fr;
                align-items: center;
                column-gap: 10px;
                padding: 5px 0;
            }}

            .patch-row-date {{
                color: rgba(255,255,255,0.72);
                font-size: 10px;
                font-weight: 700;
                letter-spacing: .05em;
                white-space: nowrap;
                line-height: 1.2;
            }}

            .patch-row-tag {{
                display: flex;
                align-items: center;
            }}

            .patch-row-title {{
                min-width: 0;
                text-align: left;
                line-height: 1.25;
                color: rgba(255,255,255,0.92);
                font-size: 12px;
                font-weight: 500;
                word-break: keep-all;
            }}

            .patch-tag-pill {{
                display: inline-block;
                padding: 2px 6px;
                /* Vitals 'rectangles only' — radius 제거. */
                font-size: 10px;
                font-weight: 700;
                line-height: 1.1;
                letter-spacing: .04em;
                white-space: nowrap;
            }}

            .patch-tag-pill--new {{
                background: rgba(31,139,76,0.24);
                border: 1px solid rgba(31,139,76,0.42);
                color: #d7ffe5;
            }}

            .patch-tag-pill--upd {{
                background: rgba(37,99,235,0.24);
                border: 1px solid rgba(37,99,235,0.42);
                color: #dbeafe;
            }}

            .patch-tag-pill--fix {{
                background: rgba(165,0,52,0.25);
                border: 1px solid rgba(165,0,52,0.40);
                color: #ffe4ec;
            }}

            .patch-tag-pill--default {{
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.16);
                color: #ffffff;
            }}

            .patch-empty {{
                color: rgba(255,255,255,0.62);
                font-size: 12px;
                padding: 6px 0 2px 0;
            }}
        </style>
    </head>
    <body>
        <div class="patch-card">
            <div class="patch-card-head">
                <div class="patch-card-title">PATCH NOTES · 최근 업데이트</div>
                <div class="patch-card-hint">last update {latest_update_str}</div>
            </div>
            <div class="patch-divider-line"></div>
            {rows_html}
        </div>
    </body>
    </html>
    """

    components.html(html, height=230, scrolling=False)

def render_board_link_panel():
    st.markdown(
        """
        <div style="
            text-align: center;
            color: rgba(255,255,255,0.94);
            font-size: 18px;
            font-weight: 700;
            line-height: 1.35;
            margin-top: 8px;
            margin-bottom: 6px;
        ">
<svg width="6" height="6" viewBox="0 0 8 8" aria-hidden="true" style="display:inline-block;vertical-align:middle;"><circle cx="4" cy="4" r="3" fill="currentColor"/></svg>
        </div>
        <div style="
            text-align: center;
            color: rgba(255,255,255,0.94);
            font-size: 18px;
            font-weight: 700;
            line-height: 1.35;
            margin-top: 8px;
            margin-bottom: 6px;
        ">
            공지사항
        </div>
        <div style="
            text-align: center;
            color: rgba(255,255,255,0.56);
            font-size: 11px;
            line-height: 1.35;
            margin-bottom: 10px;
        ">
            공지 / 패치노트
        </div>
        <div style="
            text-align: center;
            color: rgba(255,255,255,0.94);
            font-size: 18px;
            font-weight: 700;
            line-height: 1.35;
            margin-top: 8px;
            margin-bottom: 6px;
        ">
<svg width="6" height="6" viewBox="0 0 8 8" aria-hidden="true" style="display:inline-block;vertical-align:middle;"><circle cx="4" cy="4" r="3" fill="currentColor"/></svg>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "[바로가기]",
        key="goto_board_card",
        use_container_width=True,
        type="secondary"
    ):
        st.switch_page("pages/8_Board.py")

def render_status_label_panel():
    st.markdown(
        """
        <div style="
            height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
        ">
            <div style="
                color: rgba(255,255,255,0.94);
                font-size: 18px;
                font-weight: 700;
                line-height: 1.35;
                margin-bottom: 6px;
            ">
    <svg width="6" height="6" viewBox="0 0 8 8" aria-hidden="true" style="display:inline-block;vertical-align:middle;"><circle cx="4" cy="4" r="3" fill="currentColor"/></svg>
            </div>
            <div style="
                color: rgba(255,255,255,0.94);
                font-size: 18px;
                font-weight: 700;
                line-height: 1.35;
                margin-bottom: 6px;
            ">
                시스템 상태
            </div>
            <div style="
                color: rgba(255,255,255,0.56);
                font-size: 11px;
                line-height: 1.35;
                margin-bottom: 6px;
            ">
                DB / API / 모델
            </div>
            <div style="
                color: rgba(255,255,255,0.94);
                font-size: 18px;
                font-weight: 700;
                line-height: 1.35;
            ">
    <svg width="6" height="6" viewBox="0 0 8 8" aria-hidden="true" style="display:inline-block;vertical-align:middle;"><circle cx="4" cy="4" r="3" fill="currentColor"/></svg>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_right_panels(patch_posts):
    # 1행: 시스템 상태
    status_label_col, status_card_col = st.columns([0.2, 0.8], gap="small")

    with status_label_col:
        render_status_label_panel()

    with status_card_col:
        render_system_status_panel()

    # 2행: 공지사항/패치노트
    link_col, patch_col = st.columns([0.2, 0.8], gap="small")

    with link_col:
        render_board_link_panel()

    with patch_col:
        render_patch_notes_panel(patch_posts)