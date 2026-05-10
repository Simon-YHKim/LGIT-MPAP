import streamlit as st
import streamlit.components.v1 as components
from html import escape

# Vitals 컴포넌트 — LG Innotek 로고 PNG 를 base64 data URI 로 (외부 의존 0)
from ui.vitals import LOGO_WHITE_DATA_URI


def render_left_panel_background():
    st.markdown(
        """
        <div class="left-panel-bg"></div>
        """,
        unsafe_allow_html=True
    )


def render_top_brand(current_lang="KO"):
    """상단 브랜드 행 — 다크 비디오 배경 위.
    LG Innotek 공식 로고 PNG + 1px 회색 divider + 'Vitals' wordmark + 우측
    ALL SYSTEMS OPERATIONAL 상태.

    이전: 로고 옆에 '광학 MaxCapa TDR · 광학솔루션사업부 · 생산혁신센터 · Max Capa팀'
    부제 텍스트 표시. 사용자 피드백 (2026-05-08): 부제 제거 + 'Vitals' 워드마크
    배치로 균형. 회사 정보는 한 곳 (identity-block hero) 에서만.
    """
    # preview-streamlit-clone.html sec-login (line 132-159) brand-row parity:
    # LG 로고 + Vitals 워드마크 + KO ▾ lang dropdown (7개국 menu).
    # ALL SYSTEMS OPERATIONAL 은 우측 하단 ops-row 로 이동 → 여기서는 lang.
    # preview HTML brand-row 의도: LG + Vitals + KO 가 모두 좌측에 cluster.
    # 우측은 비움 (이전엔 ALL SYSTEMS OPERATIONAL 이 우측에 있었으나 그건
    # 우하단 ops-row 로 이미 이동).
    lang_options = [
        ("KO", "한국어"),
        ("EN", "English"),
        ("VI", "Tiếng Việt"),
        ("PL", "Polski"),
        ("ID", "Bahasa Indonesia"),
        ("ES", "Español"),
        ("ZH", "中文"),
    ]
    lang_codes = {code for code, _ in lang_options}
    current_code = (current_lang or "KO").upper()
    if current_code not in lang_codes:
        current_code = "KO"
    lang_items_html = "\n".join(
        f"""
                    <a class="landing-lang__item{' landing-lang__item--active' if code == current_code else ''}" href="?lang={code}" role="menuitem">
                        <span>{label}</span><span class="landing-lang__item-code">{code}</span>
                    </a>
        """
        for code, label in lang_options
    )

    st.markdown(
        f"""
        <div class="landing-topbar landing-topbar--cluster">
            <div class="landing-brand">
                <img src="{LOGO_WHITE_DATA_URI}" alt="LG Innotek"
                     class="landing-brand__logo" />
                <span class="landing-brand__divider"></span>
                <span class="landing-brand__wordmark">Vitals<span class="landing-brand__dot">.</span></span>
            </div>
            <div class="landing-lang" id="login-lang">
                <button type="button" class="landing-lang__btn" id="login-lang-btn">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="width:14px;height:14px;"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>
                    <span>{current_code}</span>
                    <span class="landing-lang__caret">▾</span>
                </button>
                <div class="landing-lang__menu" role="menu">
{lang_items_html}
                </div>
            </div>
        </div>
        <style>
        .landing-brand__logo {{
            height: 22px; width: auto; display: block;
            /* 흰 PNG — 다크 배경에 자연스럽게 올라감 */
        }}
        .landing-brand__name {{ display: none; }}  /* 텍스트 워드마크 폐기 */
        .landing-brand__wordmark {{
            font-family: var(--font-display, 'LG EI Headline', 'LG EI Text', sans-serif);
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--on-dark, rgba(255,255,255,0.96));
            line-height: 1;
            white-space: nowrap;
        }}
        .landing-brand__dot {{
            color: var(--primary, #A50034);
            margin-left: 0.02em;
        }}
        .landing-lang {{
            position: relative;
            display: inline-block;
            z-index: 200;
        }}
        .landing-lang__btn {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.18);
            color: var(--on-dark, rgba(255,255,255,0.92));
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: .06em;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer !important;
            line-height: 1;
            font-family: var(--font-body) !important;
            user-select: none;
            position: relative;
            z-index: 201;
        }}
        .landing-lang__btn:hover {{
            background: rgba(255,255,255,0.14);
            border-color: rgba(255,255,255,0.28);
        }}
        .landing-lang__caret {{
            opacity: 0.7;
            font-size: 10px;
            margin-left: 2px;
        }}
        .landing-lang__menu {{
            position: absolute;
            right: 0;
            top: calc(100% + 6px);
            background: rgba(12,14,18,0.96);
            border: 1px solid rgba(255,255,255,0.18);
            box-shadow: 0 14px 30px rgba(0,0,0,0.32);
            min-width: 200px;
            display: none;
            z-index: 9999;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }}
        .landing-lang.is-open .landing-lang__menu,
        .landing-lang:focus-within .landing-lang__menu {{
            display: block;
        }}
        /* 사용자 피드백 (2026-05-11) — :hover 만으로 열리던 것 제거 (mobile/touch 누락).
           is-open 클래스 (JS 토글) 와 :focus-within (키보드) 양쪽 지원. */
        .landing-lang__item {{
            background: transparent;
            border: 0;
            color: rgba(255,255,255,0.88);
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            width: 100%;
            font-size: 12px;
            cursor: pointer;
            font-family: var(--font-body) !important;
            text-align: left;
            text-decoration: none !important;
            box-sizing: border-box;
        }}
        .landing-lang__item:hover {{
            background: rgba(255,255,255,0.06);
        }}
        .landing-lang__item--active {{
            color: var(--primary-tint, #F8E5EC);
            font-weight: 700;
        }}
        .landing-lang__item-code {{
            font-family: 'LG EI Text', sans-serif;
            font-size: 10px;
            color: rgba(255,255,255,0.56);
            letter-spacing: .08em;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    components.html(
        """
        <script>
        (function attachLangDropdown() {
          try {
            const d = window.parent.document;
            const wrap = d.getElementById("login-lang");
            const btn = d.getElementById("login-lang-btn");
            // 사용자 피드백 (2026-05-11) — DOM ready race 대비 retry.
            // Streamlit iframe 이 부모 markdown 보다 먼저 로드되는 경우 setTimeout 으로 재시도.
            if (!wrap || !btn) {
              setTimeout(attachLangDropdown, 200);
              return;
            }
            if (btn.dataset.vitalsBound === "1") return;
            btn.dataset.vitalsBound = "1";
            btn.setAttribute("aria-haspopup", "menu");
            btn.setAttribute("aria-expanded", "false");
            btn.style.cursor = "pointer";
            btn.addEventListener("click", function(ev) {
              ev.preventDefault();
              ev.stopPropagation();
              const open = wrap.classList.toggle("is-open");
              btn.setAttribute("aria-expanded", open ? "true" : "false");
            });
            d.addEventListener("click", function(ev) {
              if (!wrap.contains(ev.target)) {
                wrap.classList.remove("is-open");
                btn.setAttribute("aria-expanded", "false");
              }
            });
            wrap.querySelectorAll(".landing-lang__item").forEach(function(item) {
              item.style.cursor = "pointer";
              item.addEventListener("click", function(ev) {
                ev.preventDefault();
                ev.stopPropagation();
                // 우선순위 1: data-lang-code attribute (가장 신뢰)
                let code = item.dataset.langCode;
                // 우선순위 2: <a href="?lang=XX"> 의 href query (a 태그일 때)
                if (!code && item.tagName === "A" && item.href) {
                  try {
                    const u = new URL(item.href, window.parent.location.origin);
                    code = u.searchParams.get("lang");
                  } catch (e) {}
                }
                // 우선순위 3: child .landing-lang__item-code 텍스트
                if (!code) {
                  const codeEl = item.querySelector(".landing-lang__item-code");
                  code = codeEl ? codeEl.textContent.trim() : "KO";
                }
                code = (code || "KO").toUpperCase();
                const url = new URL(window.parent.location.href);
                url.searchParams.set("lang", code);
                window.parent.location.href = url.toString();
              });
            });
          } catch (e) {
            // 한 번 실패 시 재시도
            setTimeout(attachLangDropdown, 400);
          }
        })();
        </script>
        """,
        height=0,
    )


def render_auth_intro():
    """preview-streamlit-clone.html sec-login auth-card 정확 측정값 매칭:
    - eyebrow: 11px / 700 / #9CA3AF / margin-bottom 6px
    - title: 22px / 700 / #101218 / margin-bottom 4px (NOT 36px)
    - sub: 12-13px / 400 / #6B7280
    """
    st.markdown(
        """
        <div class="auth-eyebrow">PRODUCTIVITY ANALYTICS · SIGN IN</div>
        <h2 class="auth-title">로그인</h2>
        <p class="auth-sub">사내 계정 아이디만 입력하세요.</p>
        <style>
        .auth-eyebrow {
            color: #9CA3AF !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            margin: 0 0 6px !important;
            line-height: 1 !important;
        }
        .auth-title {
            color: #101218 !important;
            font-size: 22px !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em !important;
            margin: 0 0 4px !important;
            padding: 0 !important;
            line-height: 1.2 !important;
            font-family: var(--font-display, 'LG EI Headline', 'LG EI Text', sans-serif) !important;
        }
        .auth-sub {
            color: #6B7280 !important;
            font-size: 13px !important;
            font-weight: 400 !important;
            margin: 0 0 22px !important;
            line-height: 1.4 !important;
        }
        /* streamlit 의 stHeading wrapper 가 title 에 추가 padding 부여하는 것 fix */
        [data-testid="stHeadingWithActionElements"] {
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_auth_card_footer():
    """preview-streamlit-clone.html sec-login (line 242-245) parity:
    auth-card 하단 footer — 좌측 '문의 · 생산혁신센터 Max Capa TDR' + 우측 'v0.4.2'."""
    st.markdown(
        """
        <div class="auth-card-foot">
            <span>문의 · 생산혁신센터 Max Capa TDR</span>
            <span class="auth-card-foot__ver">v0.4.2</span>
        </div>
        <style>
        .auth-card-foot {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: #9CA3AF;
            margin-top: 18px;
            padding-top: 12px;
            border-top: 1px solid #E5E7EB;
            background: transparent;
        }
        /* footer 가 들어 있는 stMarkdown wrapper 의 background 제거 —
           카드 안 작은 흰 박스 같은 시각 충돌 방지 */
        [data-testid="stMarkdown"]:has(.auth-card-foot) {
            background: transparent !important;
            box-shadow: none !important;
            padding: 0 !important;
        }
        .auth-card-foot__ver {
            font-family: 'LG EI Text', sans-serif;
            letter-spacing: .04em;
            color: #6B7280;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def _build_changelog_rows(patch_posts):
    if not patch_posts:
        return '<div class="login-changelog__empty">표시할 변경 이력이 없습니다.</div>'

    rows_html = ""
    for row in patch_posts[:20]:
        if len(row) >= 6:
            _, _, tag, title, _, created_at = row[:6]
        else:
            _, tag, title, created_at = row[:4]

        tag_upper = (tag or "NOTE").upper()
        date_text = created_at.strftime("%m-%d") if hasattr(created_at, "strftime") else "-"
        rows_html += (
            '<div class="login-changelog__row">'
            f'<span class="login-changelog__tag">{escape(tag_upper)}</span>'
            f'<span class="login-changelog__title">{escape(title or "-")}</span>'
            f'<span class="login-changelog__date">{escape(date_text)}</span>'
            '</div>'
        )
    return rows_html


def render_right_bottom_meta(patch_posts=None):
    """preview-streamlit-clone.html sec-login (line 318-333) parity:
    우측 panels 아래 ops-row + foot-row.
    - ops-row: 'ALL SYSTEMS OPERATIONAL · 2026-05-07 · VITALS V0.4.2'
    - foot-row: '생산혁신센터 Max Capa TDR · 사내망 전용 · 변경 로그 전체 보기 →'."""
    changelog_rows = _build_changelog_rows(patch_posts or [])
    html = """
        <div class="ops-row">
            <span class="ops-row__group">
                <span class="ops-row__dot" aria-hidden="true"></span>
                <span>ALL SYSTEMS OPERATIONAL</span>
            </span>
            <span class="ops-row__sep" aria-hidden="true">·</span>
            <span>2026-05-07</span>
            <span class="ops-row__sep" aria-hidden="true">·</span>
            <span>VITALS V0.4.2</span>
        </div>
        <div class="foot-row">
            <span>생산혁신센터 Max Capa TDR · 사내망 전용</span>
            <a class="foot-row__link" href="/Patch_Note" target="_self">변경 로그 전체 보기 →</a>
        </div>
        <style>
        .ops-row {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 14px;
            font-family: 'LG EI Text', sans-serif;
            font-size: 10px;
            color: rgba(255,255,255,0.62);
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .ops-row__group {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .ops-row__dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #1F8B4C;
            box-shadow: 0 0 0 2px rgba(31,139,76,0.18);
            display: inline-block;
        }
        .ops-row__sep {
            color: rgba(255,255,255,0.32);
        }
        .foot-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 8px;
            font-size: 11px;
            color: rgba(255,255,255,0.56);
            gap: 14px;
            position: relative;
        }
        .foot-row__link {
            color: rgba(255,255,255,0.78) !important;
            text-decoration: none;
            font-size: 11px;
            cursor: pointer;
            list-style: none;
            white-space: nowrap;
        }
        .foot-row__link::-webkit-details-marker {
            display: none;
        }
        .foot-row__link:hover {
            color: var(--primary-tint, #F8E5EC) !important;
            text-decoration: underline;
        }
        .login-changelog {
            position: relative;
        }
        .login-changelog__panel {
            position: absolute;
            right: 0;
            bottom: calc(100% + 10px);
            width: 360px;
            max-height: 320px;
            overflow-y: auto;
            padding: 10px 12px;
            background: rgba(12,14,18,0.96);
            border: 1px solid rgba(255,255,255,0.14);
            box-shadow: 0 18px 40px rgba(0,0,0,0.32);
            z-index: 120;
        }
        .login-changelog__head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 8px;
            margin-bottom: 4px;
            border-bottom: 1px solid rgba(255,255,255,0.10);
            color: rgba(255,255,255,0.70);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: .08em;
        }
        .login-changelog__row {
            display: grid;
            grid-template-columns: 40px 1fr 42px;
            align-items: center;
            gap: 8px;
            min-height: 28px;
            border-bottom: 1px dashed rgba(255,255,255,0.08);
            color: rgba(255,255,255,0.88);
        }
        .login-changelog__row:last-child {
            border-bottom: 0;
        }
        .login-changelog__tag {
            color: #F8E5EC;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: .04em;
        }
        .login-changelog__title {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 11px;
        }
        .login-changelog__date {
            text-align: right;
            color: rgba(255,255,255,0.56);
            font-size: 10px;
            font-weight: 700;
        }
        .login-changelog__empty {
            padding: 10px 0 4px;
            color: rgba(255,255,255,0.62);
            font-size: 11px;
        }
        </style>
        """
    st.markdown(html.replace("__CHANGELOG_ROWS__", changelog_rows), unsafe_allow_html=True)


def render_identity_block():
    """Vitals 브랜드 hero — landing.html 처럼 LG EI Headline 큰 타이포 + 와인 점.

    이전: 'Vitals' + 캐치프레이즈 + '광학솔루션 사업부 · CMP · UPH · MTBA · MaxCapa Chat' BU 라인.
    사용자 피드백 (2026-05-08): BU 라인 제거 — 분석 도메인 나열은 hero 가
    아닌 Home 의 카테고리 카드에서 표현.
    """
    st.markdown(
        """
        <div class="identity-block">
            <h3 class="identity-name">Vitals<span class="dot">.</span></h3>
            <p class="identity-sub">공정의 호흡을 데이터로 듣다.</p>
        </div>
        <style>
        /* identity 블록 폰트를 LG EI Headline 으로 교체 + 56px hero 타이포 */
        .identity-name {
            font-family: var(--font-display) !important;
            font-size: 88px !important;
            font-weight: 700 !important;
            letter-spacing: -0.04em !important;
            line-height: 0.95 !important;
            color: var(--on-dark) !important;
            margin: 0 !important;
        }
        /* 시안 패스 8 — dot 와인색 강제 (2026-05-10 사용자 요청) */
        .identity-name .dot {
            color: #A50034 !important;
        }
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
                font-family: "LG EI Text", "LG EI Headline", sans-serif;
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
                <div class="status-card-hint">last sync 23:50</div>
            </div>
            <div class="status-divider-line"></div>

            <!-- preview-streamlit-clone.html sec-login (line 268-292) parity:
                 5 row — API Gateway / PG·MES / PG·ITAS / Streamlit Worker / 데이터 적재 -->
            <div class="status-row">
                <span class="status-dot status-dot--green"></span>
                <div class="status-label">API Gateway</div>
                <div class="status-detail">142 ms · OK</div>
            </div>

            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--green"></span>
                <div class="status-label">PostgreSQL · MES</div>
                <div class="status-detail">38 ms · OK</div>
            </div>

            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--green"></span>
                <div class="status-label">PostgreSQL · ITAS</div>
                <div class="status-detail">52 ms · OK</div>
            </div>

            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--yellow"></span>
                <div class="status-label">Streamlit Worker</div>
                <div class="status-detail">2/3 · degraded</div>
            </div>

            <div class="status-divider-line"></div>

            <div class="status-row">
                <span class="status-dot status-dot--green"></span>
                <div class="status-label">데이터 적재</div>
                <div class="status-detail">05-07 23:50 · OK</div>
            </div>
        </div>
    </body>
    </html>
    """
    # 5 row 로 늘어남 → 230px → 270px 로 component 높이 조정
    components.html(html, height=270, scrolling=False)

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
                font-family: "LG EI Text", "LG EI Headline", sans-serif;
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
        # 8_Board.py 는 8_Patch_Note.py 로 rename 됨 (커밋 a01... 부근).
        # st.switch_page 가 정확한 파일 경로를 요구하므로 새 이름 반영.
        st.switch_page("pages/8_Patch_Note.py")

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

def render_right_panels(patch_posts, all_patch_posts=None):
    """preview-streamlit-clone.html sec-login parity:
    우측 column 은 SYSTEM STATUS panel + PATCH NOTES panel 만 stack.
    이전엔 0.2 / 0.8 split 으로 좌측에 한국어 라벨 (시스템 상태 / 공지사항 /
    바로가기) 을 두었으나, preview HTML 의도에는 이 라벨이 없음 →
    가운데 spacer 가 진짜 비도록 라벨 column 제거.

    render_status_label_panel / render_board_link_panel 함수는 보존 (다른
    페이지 호출 가능성 + 백엔드 freeze 룰). 단지 여기서 호출 안 함."""
    # 1행: SYSTEM STATUS card
    render_system_status_panel()

    # 2행: PATCH NOTES card
    render_patch_notes_panel(patch_posts)

    # 3행: ops-row + foot-row (preview HTML sec-login 우하단 영역 parity)
    render_right_bottom_meta(all_patch_posts or patch_posts)
