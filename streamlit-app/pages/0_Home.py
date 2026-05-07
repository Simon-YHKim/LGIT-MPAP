import html
import urllib.parse

import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from auth_guard import require_login
from access_logger import log_page_access

# =========================================================
# Page Config
# =========================================================
st.set_page_config(
    page_title="설비생산성 분석 플랫폼",
    layout="wide",
    initial_sidebar_state="collapsed",
)
require_login(page_name="home", page_path="pages/0_Home.py")

# === Vitals theme (LG EI fonts + wine palette) ===
from ui.vitals import apply_vitals_theme
apply_vitals_theme()
log_page_access("Home")

# === Vitals analytics — client-side click/scroll/error tracker ===
from ui.analytics import inject_tracker
inject_tracker(page_name="Home", page_path="pages/0_Home.py")

# =========================================================
# DB Config
# =========================================================
# R4 — env var override 지원 (기본값 보존: 폐쇄망 운영 시 그대로 작동).
# 운영 환경에선 DB_HOST / DB_PASSWORD 등 환경변수로 주입 권장 (secrets 노출 회피).
import os as _os
DB_HOST = _os.getenv("CMP_DB_HOST", "localhost")
DB_PORT = int(_os.getenv("CMP_DB_PORT", "5432"))
DB_NAME = _os.getenv("CMP_DB_NAME", "CMP")
DB_USER = _os.getenv("CMP_DB_USER", "postgres")
DB_PASSWORD = _os.getenv("CMP_DB_PASSWORD")
if not DB_PASSWORD:
    raise RuntimeError(
        "CMP_DB_PASSWORD not configured. Set the env var (or add to "
        ".streamlit/secrets.toml and re-export). Hardcoded fallback removed."
    )
DB_SCHEMA = _os.getenv("CMP_DB_SCHEMA", "public")
DB_TABLE = "mart_cmp_dashboard_daily"
DASHBOARD_DB_LOOKBACK_MONTHS = 3
MAX_VALID_ACHIEVEMENT = 5.0

DB_WORK_DATE_COL = "work_date"
DB_PERIOD_COL = "period"
DB_AREA_COL = "area"
DB_MODEL_COL = "model"
DB_PROCESS_COL = "process_l1"
DB_EQUIPMENT_COL = "equipment"
DB_CMP_RATE_COL = "cmp_achievement_rate"

AREA_COL = "영역"
MODEL_COL = "모델"
PROCESS_COL = "공정"
DATE_COL = "날짜"
PERIOD_COL = "기간"
CMP_COL = "CMP 달성률"

PAGES = {
    "cmp": "pages/1_CMP_Dashboard.py",
    "uph": "pages/2_UPH_Dashboard.py",
    "mtba": "pages/3_MTBA_Dashboard.py",
    "mtba_detail": "pages/4_MTBA_Detail_View.py",
    "chat": "pages/5_MaxCapa_Chat.py",
}

CONTACT_MAIL_TO = [
    "rg.korea@lginnotek.com;",
    "pkh2889@lginnotek.com;",
    "jm.mun9205@lginnotek.com;",
]
CONTACT_MAIL_SUBJECT = "문의드립니다."
CONTACT_MAIL_BODY = """안녕하세요.

문의드립니다.

[문의 내용]
여기에 문의 내용을 입력하세요.
"""


def inject_css() -> None:
    # 폐쇄망: 외부 CDN @import 제거. Pretendard / IBM Plex Mono 는 시스템 폰트
    # 스택으로 fallback (font-stack 의 Apple SD Gothic Neo / Malgun Gothic /
    # SF Mono / Consolas 가 한·영 모두 커버).
    st.markdown("""<style>
        @font-face{font-family:'LG EI Text';font-weight:300;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-text-300.woff2') format('woff2')}
        @font-face{font-family:'LG EI Text';font-weight:400;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-text-400.woff2') format('woff2')}
        @font-face{font-family:'LG EI Text';font-weight:600;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-text-600.woff2') format('woff2')}
        @font-face{font-family:'LG EI Text';font-weight:700;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-text-700.woff2') format('woff2')}
        @font-face{font-family:'LG EI Headline';font-weight:300;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-headline-300.woff2') format('woff2')}
        @font-face{font-family:'LG EI Headline';font-weight:400;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-headline-400.woff2') format('woff2')}
        @font-face{font-family:'LG EI Headline';font-weight:600;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-headline-600.woff2') format('woff2')}
        @font-face{font-family:'LG EI Headline';font-weight:700;font-style:normal;font-display:swap;src:url('./fonts/lg-ei-headline-700.woff2') format('woff2')}

        :root{
            --primary:#A50034;
            --primary-dark:#7E0027;
            --primary-tint:#F8E5EC;
            --page-bg:#F7F8FA;
            --card-bg:#FFFFFF;
            --soft:#F1F3F5;
            --border:#E5E7EB;
            --border-strong:#CBD0D6;
            --ink-body:#1F2430;
            --ink-muted:#6B7280;
            --ink-subtle:#9CA3AF;
            --status-good:#1F8B4C;
            --status-warn:#B57F1B;
            --status-good-tint:#E6F4EA;
            --status-warn-tint:#FAF1DD;
            --status-subtle-tint:#EEF0F3;
            --font-body:'LG EI Text','LG Smart','Pretendard Variable',Pretendard,'Malgun Gothic',system-ui,sans-serif;
            --font-display:'LG EI Headline','LG EI Text','Pretendard Variable',Pretendard,sans-serif;
            --font-mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;
        }

        html, body, [class*="css"], [class*="st-"]{font-family:var(--font-body) !important;}
        .stApp{background:var(--page-bg);}

        /* 참고 이미지처럼 좌측 기준으로 넓게 사용 */
        .block-container{
            max-width:none;
            padding-top:2.0rem;
            padding-left:2.0rem;
            padding-right:2.0rem;
            padding-bottom:1.5rem;
        }

        .home-head{margin-bottom:26px;}
        .home-title{
            margin:0 0 8px 0;
            font-family:var(--font-display);
            font-size:34px;
            line-height:1.08;
            font-weight:800;
            letter-spacing:-0.03em;
            color:var(--ink-body);
        }
        .home-sub{margin:0;color:var(--ink-muted);font-size:14px;}

        /* Vitals 3-카테고리 헤딩 (생산 / 설비 성능 / 설비 효율) ----------- */
        .vit-cat-head{
            display:flex; align-items:center; flex-wrap:wrap; gap:10px;
            margin: 24px 0 14px;
            padding-left: 4px;
        }
        .vit-cat-bar{
            width:4px; height:22px;
            background: var(--primary);
            border-radius: 2px;
            flex: 0 0 auto;
        }
        .vit-cat-title{
            margin:0; font-family: var(--font-display);
            font-size:18px; font-weight:700; letter-spacing:-0.01em;
            color: var(--ink-body);
            display:flex; align-items:baseline; gap:10px;
        }
        .vit-cat-sub{
            font-family: var(--font-mono);
            font-size:11px; font-weight:600;
            color: var(--ink-subtle);
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .vit-cat-desc{
            margin: 0 0 0 4px;
            font-size: 12px; color: var(--ink-muted);
            flex: 1 1 auto; min-width: 0;
            text-align: right;
        }

        /* 모든 Home 카드 버튼의 실제 클릭 영역과 디자인 영역을 동일하게 처리 */
        .st-key-home_card_cmp,
        .st-key-home_card_uph,
        .st-key-home_card_mtba,
        .st-key-home_card_mtba_detail,
        .st-key-home_card_chat{
            margin-bottom:14px;
        }

        .st-key-home_card_cmp div[data-testid="stButton"],
        .st-key-home_card_uph div[data-testid="stButton"],
        .st-key-home_card_mtba div[data-testid="stButton"],
        .st-key-home_card_mtba_detail div[data-testid="stButton"],
        .st-key-home_card_chat div[data-testid="stButton"]{
            height:176px;
            margin:0 !important;
            padding:0 !important;
        }

        .st-key-home_card_cmp button,
        .st-key-home_card_uph button,
        .st-key-home_card_mtba button,
        .st-key-home_card_mtba_detail button,
        .st-key-home_card_chat button{
            width:100% !important;
            height:176px !important;
            min-height:176px !important;
            position:relative !important;
            display:block !important;
            padding:0 !important;
            margin:0 !important;
            background:var(--card-bg) !important;
            border:1px solid var(--border) !important;
            border-radius:10px !important;
            box-shadow:none !important;
            overflow:hidden !important;
            cursor:pointer !important;
            transition:border-color .15s, box-shadow .15s, transform .15s !important;
            color:transparent !important;
        }

        .st-key-home_card_cmp button:hover,
        .st-key-home_card_uph button:hover,
        .st-key-home_card_mtba button:hover,
        .st-key-home_card_mtba_detail button:hover{
            border-color:var(--border-strong) !important;
            box-shadow:inset 3px 0 0 var(--primary), 0 8px 22px -4px rgba(15,17,21,0.06) !important;
            transform:translateY(-1px);
            background:#FFFFFF !important;
        }
        .st-key-home_card_cmp button:focus,
        .st-key-home_card_uph button:focus,
        .st-key-home_card_mtba button:focus,
        .st-key-home_card_mtba_detail button:focus,
        .st-key-home_card_chat button:focus{
            border-color:var(--primary) !important;
            box-shadow:0 0 0 2px rgba(165,0,52,.12) !important;
            outline:none !important;
        }

        /* 버튼 label: 제목/설명 위치. 제목은 first-line으로 강조 */
        .st-key-home_card_cmp button p,
        .st-key-home_card_uph button p,
        .st-key-home_card_mtba button p,
        .st-key-home_card_mtba_detail button p,
        .st-key-home_card_chat button p{
            position:absolute !important;
            left:20px !important;
            right:20px !important;
            top:72px !important;
            margin:0 !important;
            white-space:pre-line !important;
            text-align:left !important;
            color:var(--ink-muted) !important;
            font-size:13px !important;
            font-weight:500 !important;
            line-height:1.5 !important;
            letter-spacing:-0.01em !important;
        }
        .st-key-home_card_cmp button p::first-line,
        .st-key-home_card_uph button p::first-line,
        .st-key-home_card_mtba button p::first-line,
        .st-key-home_card_mtba_detail button p::first-line,
        .st-key-home_card_chat button p::first-line{
            color:var(--ink-body) !important;
            font-size:15px !important;
            font-weight:800 !important;
            line-height:1.25 !important;
        }

        /* 아이콘 박스 */
        .st-key-home_card_cmp button::before,
        .st-key-home_card_uph button::before,
        .st-key-home_card_mtba button::before,
        .st-key-home_card_mtba_detail button::before,
        .st-key-home_card_chat button::before{
            position:absolute;
            left:20px;
            top:20px;
            width:36px;
            height:36px;
            border-radius:8px;
            background:var(--soft);
            color:var(--ink-body);
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:16px;
            line-height:36px;
            transition:background .15s, color .15s;
        }
        .st-key-home_card_cmp button:hover::before,
        .st-key-home_card_uph button:hover::before,
        .st-key-home_card_mtba button:hover::before,
        .st-key-home_card_mtba_detail button:hover::before{
            background:var(--primary-tint);
            color:var(--primary-dark);
        }
        .st-key-home_card_cmp button::before{content:"▦";}
        .st-key-home_card_uph button::before{content:"↗";}
        .st-key-home_card_mtba button::before{content:"⌁";}
        .st-key-home_card_mtba_detail button::before{content:"▧";}
        .st-key-home_card_chat button::before{content:"□";}

        /* 우상단 배지: 버튼 자체 pseudo라 위치가 밀리지 않음 */
        .st-key-home_card_cmp button::after,
        .st-key-home_card_uph button::after,
        .st-key-home_card_mtba button::after,
        .st-key-home_card_mtba_detail button::after,
        .st-key-home_card_chat button::after{
            position:absolute;
            right:20px;
            top:20px;
            display:inline-flex;
            align-items:center;
            gap:5px;
            padding:2px 8px;
            border-radius:4px;
            font-family:var(--font-mono);
            font-size:10px;
            font-weight:800;
            line-height:1.45;
            letter-spacing:.05em;
            white-space:nowrap;
        }
        .st-key-home_card_cmp button::after{content:"● 가오픈";background:var(--status-warn-tint);color:var(--status-warn);}
        .st-key-home_card_uph button::after{content:"● 가오픈";background:var(--status-warn-tint);color:var(--status-warn);}
        .st-key-home_card_mtba button::after{content:"● 가오픈";background:var(--status-warn-tint);color:var(--status-warn);}
        .st-key-home_card_mtba_detail button::after{content:"● 가오픈";background:var(--status-warn-tint);color:var(--status-warn);}
        .st-key-home_card_chat button::after{content:"● 오픈예정";background:var(--status-subtle-tint);color:var(--ink-muted);}

        /* 하단 meta */
        .st-key-home_card_cmp button p::after,
        .st-key-home_card_uph button p::after,
        .st-key-home_card_mtba button p::after,
        .st-key-home_card_mtba_detail button p::after,
        .st-key-home_card_chat button p::after{
            position:absolute;
            left:0;
            right:0;
            top:65px;
            padding-top:8px;
            border-top:1px dashed var(--border);
            font-family:var(--font-mono);
            font-size:11px;
            font-weight:500;
            color:var(--ink-subtle);
            letter-spacing:.04em;
            white-space:nowrap;
        }
        .st-key-home_card_cmp button p::after{content:"정식 5/22E · v4 · 2026-04-28";}
        .st-key-home_card_uph button p::after{content:"가오픈 4/29~ · 정식 5/22E";}
        .st-key-home_card_mtba button p::after{content:"가오픈 4/29~ · 정식 5/15E";}
        .st-key-home_card_mtba_detail button p::after{content:"가오픈 4/29~ · 정식 5/15E";}
        .st-key-home_card_chat button p::after{content:"오픈 예정                                    준비중";}

        /* disabled */
        .st-key-home_card_chat button:disabled{
            opacity:.68 !important;
            cursor:not-allowed !important;
            background:var(--card-bg) !important;
        }
        .st-key-home_card_chat button:disabled:hover{
            transform:none !important;
            box-shadow:none !important;
            border-color:var(--border) !important;
        }

        .home-footer{
            margin-top:18px;
            padding:18px 0 8px;
            border-top:1px solid var(--border);
            display:flex;
            justify-content:space-between;
            align-items:center;
            font-family:var(--font-mono);
            font-size:11px;
            color:var(--ink-subtle);
            letter-spacing:.04em;
            flex-wrap:wrap;
            gap:12px;
        }
        .home-footer a{color:var(--ink-muted);border-bottom:1px solid var(--border);text-decoration:none;}
        .home-footer a:hover{color:var(--primary-dark);border-color:var(--primary-dark);}


        /* =========================================================
           추가 요구사항: Streamlit 기본 상단/좌측 요소 제거
           - 기존 Home 디자인/카드/레이아웃은 변경하지 않음
           ========================================================= */
        header[data-testid="stHeader"]{
            display:none !important;
            height:0 !important;
            min-height:0 !important;
            background:transparent !important;
            box-shadow:none !important;
        }
        section[data-testid="stSidebar"],
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"]{
            display:none !important;
            width:0 !important;
            min-width:0 !important;
            visibility:hidden !important;
        }
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        #MainMenu,
        footer{
            display:none !important;
            visibility:hidden !important;
        }

        /* 추가 요구사항: 하단 문의 메일 보내기 버튼 */
        .contact-mail-button{
            display:inline-flex;
            align-items:center;
            justify-content:center;
            gap:7px;
            min-height:32px;
            padding:8px 14px;
            border-radius:999px;
            border:1px solid var(--primary);
            background:var(--primary);
            color:#fff !important;
            font-family:var(--font-body);
            font-size:12px;
            font-weight:700;
            letter-spacing:-.01em;
            text-decoration:none !important;
            box-shadow:0 6px 18px rgba(165,0,52,.13);
        }
        .contact-mail-button:hover{
            background:var(--primary-dark);
            border-color:var(--primary-dark);
            color:#fff !important;
            transform:translateY(-1px);
        }
        

        /* =========================================================
           CMP 요약 상황판 추가/보정 CSS
           ========================================================= */
        .cmp-summary-wrap{margin-bottom:26px;}
        .cmp-filter-caption{font-size:11px;font-weight:700;color:var(--ink-muted);margin:0 0 4px 0;}

        /* 요약 상황판 필터: y축 최소화 */
        .cmp-filter-compact div[data-testid="stForm"]{
            border:1px solid var(--border) !important;
            border-radius:8px !important;
            background:#fff !important;
            padding:8px 10px !important;
            margin-bottom:10px !important;
        }
        .cmp-filter-compact div[data-testid="stVerticalBlock"]{gap:.25rem !important;}
        .cmp-filter-compact label,
        .cmp-filter-compact p{
            font-size:11px !important;
            line-height:1.15 !important;
            margin-bottom:2px !important;
        }
        .cmp-filter-compact div[data-baseweb="select"] > div{
            min-height:34px !important;
            border-radius:7px !important;
            font-size:11px !important;
        }
        .cmp-filter-compact div[data-baseweb="tag"]{
            height:22px !important;
            margin-top:1px !important;
            margin-bottom:1px !important;
            background:var(--status-bad, #B23A48) !important;
            border-radius:5px !important;
        }
        .cmp-filter-compact div[data-baseweb="tag"] span{
            font-size:10px !important;
            line-height:18px !important;
        }
        .cmp-filter-compact div[role="radiogroup"]{
            min-height:34px !important;
            align-items:center !important;
            gap:10px !important;
        }
        .cmp-filter-compact div[role="radiogroup"] label{
            padding-top:0 !important;
            padding-bottom:0 !important;
            margin-bottom:0 !important;
        }
        .cmp-filter-compact button[kind="secondaryFormSubmit"]{
            min-height:34px !important;
            height:34px !important;
            padding:0 10px !important;
            border-radius:7px !important;
            border:1px solid var(--border) !important;
            background:#fff !important;
            color:var(--ink-body) !important;
            box-shadow:none !important;
            font-size:12px !important;
            font-weight:700 !important;
            text-align:center !important;
            justify-content:center !important;
        }
        .cmp-filter-compact button[kind="secondaryFormSubmit"]:hover{
            border-color:var(--primary) !important;
            color:var(--primary) !important;
            background:var(--primary-tint) !important;
        }

        .cmp-top-strip{height:7px;background:var(--primary);border-radius:8px 8px 0 0;margin:10px 0 14px 0;}
        .cmp-page-head{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:12px;}
        .cmp-eyebrow{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--ink-subtle);margin-bottom:7px;}
        .cmp-page-head h1{margin:0 0 6px 0;font-family:var(--font-display);font-size:26px;line-height:1.18;font-weight:800;letter-spacing:-.03em;color:var(--ink-body);}
        .cmp-page-head p{margin:0;color:var(--ink-muted);font-size:12px;line-height:1.35;}

        .cmp-kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:16px;}
        .cmp-kpi{
            position:relative;background:#fff;border:1px solid var(--border);border-radius:8px;
            padding:13px 16px 12px 19px;min-height:104px;height:auto;
            display:flex;flex-direction:column;justify-content:center;gap:6px;overflow:visible;
        }
        .cmp-kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--primary);border-radius:8px 0 0 8px;}
        .cmp-kpi__label{font-size:11px;font-weight:800;letter-spacing:.04em;color:var(--ink-subtle);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.25;}
        .cmp-kpi__value{font-family:var(--font-mono);font-size:30px;line-height:1.18;font-weight:700;color:var(--ink-body);letter-spacing:-.03em;overflow:visible;}
        .cmp-kpi__delta{font-family:var(--font-mono);font-size:12px;line-height:1.25;font-weight:700;overflow:visible;}
        .cmp-kpi__delta.good{color:var(--status-good);}.cmp-kpi__delta.bad{color:#B23A48;}.cmp-kpi__delta.neutral{color:var(--ink-subtle);}

        .cmp-sect-head{display:flex;align-items:center;gap:10px;margin:15px 0 10px;justify-content:space-between;}
        .cmp-sect-head__left{display:flex;align-items:center;gap:10px;}.cmp-sect-head__bar{width:4px;height:18px;background:var(--primary);border-radius:2px;}.cmp-sect-head__title{font-size:17px;font-weight:800;color:var(--ink-body);}.cmp-sect-head__meta{font-size:12px;color:var(--ink-muted);font-family:var(--font-mono);}
        .cmp-models{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px;margin-bottom:34px;}
        .cmp-model-col{background:#fff;border:1px solid var(--border);border-radius:8px;padding:13px;}
        .cmp-model-col__head{font-size:13px;font-weight:800;color:var(--ink-body);margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;}
        .cmp-count{font-family:var(--font-mono);font-size:11px;color:var(--ink-subtle);font-weight:400;}
        .cmp-proc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:6px;}
        .cmp-proc{height:56px;border-radius:6px;background:var(--soft);display:flex;flex-direction:column;justify-content:space-between;padding:6px 8px;border:1px solid transparent;}
        .cmp-proc__name{font-size:11px;color:var(--ink-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.25;}
        .cmp-proc__val{font-family:var(--font-mono);font-size:14px;font-weight:700;color:var(--ink-body);line-height:1.25;}
        .cmp-proc.good{background:#DFE8F6;border-color:#D6E1F2}.cmp-proc.good .cmp-proc__val{color:var(--status-good)}
        .cmp-proc.warn{background:#EFE5CC;border-color:#E5D5AE}.cmp-proc.warn .cmp-proc__val{color:var(--status-warn)}
        .cmp-proc.bad{background:#F2D7DF;border-color:#EBC6D0}.cmp-proc.bad .cmp-proc__val{color:#B23A48}

        /* 기존 Home 카드 디자인이 요약 필터 버튼에 오염되지 않도록 보정 */
        .cmp-filter-compact div[data-testid="stForm"] div[data-testid="stButton"] button{
            color:var(--ink-body) !important;
        }


        /* =========================================================
           2026-05-06 Compact Filter Override
           - 요약 상황판 필터 y축 최소화
           - 글자/버튼/선택박스 전체 축소
           - 기존 하단 메뉴 카드 디자인 유지
           ========================================================= */
        .cmp-filter-title{
            font-size:9px !important;
            line-height:1 !important;
            font-weight:700 !important;
            color:var(--ink-muted) !important;
            margin:0 0 2px 0 !important;
            padding:0 !important;
        }
        div[data-testid="stForm"]{
            border:1px solid var(--border) !important;
            border-radius:7px !important;
            background:#fff !important;
            padding:4px 7px !important;
            margin:0 0 8px 0 !important;
            min-height:0 !important;
        }
        div[data-testid="stForm"] div[data-testid="stVerticalBlock"],
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"]{
            gap:0.20rem !important;
        }
        div[data-testid="stForm"] div[data-testid="column"]{
            padding:0 2px !important;
        }
        div[data-testid="stForm"] div[data-testid="stElementContainer"]{
            margin:0 !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"]{
            min-height:25px !important;
            height:25px !important;
            align-items:center !important;
            gap:5px !important;
            padding:0 !important;
            margin:0 !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"] label{
            min-height:21px !important;
            height:21px !important;
            padding:0 !important;
            margin:0 !important;
            align-items:center !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"] label p,
        div[data-testid="stForm"] label p,
        div[data-testid="stForm"] p{
            font-size:9px !important;
            line-height:1.05 !important;
            margin:0 !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] input[type="radio"]{
            width:10px !important;
            height:10px !important;
            margin:0 2px 0 0 !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"]{
            min-height:25px !important;
            height:auto !important;
            font-size:9px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] > div{
            min-height:25px !important;
            padding-top:0 !important;
            padding-bottom:0 !important;
            border-radius:6px !important;
            font-size:9px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] input{
            font-size:9px !important;
            line-height:1 !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"]{
            height:17px !important;
            min-height:17px !important;
            margin:1px 2px 1px 0 !important;
            padding:0 4px !important;
            border-radius:4px !important;
            background:var(--status-bad, #B23A48) !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] span{
            font-size:8px !important;
            line-height:15px !important;
            max-width:86px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] svg,
        div[data-testid="stForm"] svg{
            width:10px !important;
            height:10px !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]{
            min-height:25px !important;
            height:25px !important;
            padding:0 5px !important;
            border-radius:6px !important;
            border:1px solid var(--border) !important;
            background:#fff !important;
            color:var(--ink-body) !important;
            box-shadow:none !important;
            font-size:9px !important;
            line-height:1 !important;
            font-weight:700 !important;
            text-align:center !important;
            justify-content:center !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] p{
            font-size:9px !important;
            line-height:1 !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover{
            border-color:var(--primary) !important;
            color:var(--primary) !important;
            background:var(--primary-tint) !important;
        }
        .cmp-top-strip{margin-top:6px !important;margin-bottom:10px !important;height:6px !important;}
        .cmp-page-head{margin-bottom:10px !important;}



        /* =========================================================
           2026-05-06 Compact Layout V2
           - 첨부 스크린샷 기준: 전체 요소를 mockup처럼 더 작고 조밀하게 조정
           - 필터 / KPI / 공정카드 / 섹션 간격 전체 축소
           ========================================================= */
        .block-container{
            padding-top:0.55rem !important;
            padding-left:1.35rem !important;
            padding-right:1.35rem !important;
            padding-bottom:1rem !important;
            max-width:1180px !important;
        }

        /* 필터 영역: 가장 큰 원인인 form/select/tag 높이 재축소 */
        .cmp-filter-title{
            font-size:8px !important;
            line-height:1 !important;
            margin:0 0 1px 0 !important;
            color:#7b8493 !important;
        }
        div[data-testid="stForm"]{
            padding:3px 5px !important;
            margin:0 0 7px 0 !important;
            border-radius:6px !important;
            min-height:30px !important;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"]{
            gap:0.14rem !important;
            align-items:center !important;
        }
        div[data-testid="stForm"] div[data-testid="column"]{
            padding:0 1px !important;
        }
        div[data-testid="stForm"] div[data-testid="stElementContainer"]{
            margin:0 !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] label,
        div[data-testid="stForm"] label p,
        div[data-testid="stForm"] p{
            font-size:8px !important;
            line-height:1 !important;
            margin:0 !important;
            padding:0 !important;
        }

        /* 기간 radio */
        div[data-testid="stForm"] div[role="radiogroup"]{
            min-height:22px !important;
            height:22px !important;
            gap:3px !important;
            padding:0 !important;
            margin:0 !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"] label{
            min-height:18px !important;
            height:18px !important;
            padding:0 !important;
            margin:0 !important;
        }
        div[data-testid="stForm"] input[type="radio"]{
            width:8px !important;
            height:8px !important;
            margin:0 2px 0 0 !important;
        }

        /* Multiselect control */
        div[data-testid="stForm"] div[data-baseweb="select"]{
            min-height:22px !important;
            font-size:8px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] > div{
            min-height:22px !important;
            padding:0 2px !important;
            border-radius:5px !important;
            font-size:8px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] input{
            font-size:8px !important;
            height:14px !important;
            line-height:14px !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"]{
            height:15px !important;
            min-height:15px !important;
            margin:1px 1px !important;
            padding:0 3px !important;
            border-radius:3px !important;
            max-width:82px !important;
            overflow:hidden !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] span{
            font-size:7.5px !important;
            line-height:13px !important;
            max-width:62px !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            white-space:nowrap !important;
        }
        div[data-testid="stForm"] svg{
            width:8px !important;
            height:8px !important;
        }

        /* Apply / Reset */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]{
            min-height:22px !important;
            height:22px !important;
            padding:0 4px !important;
            border-radius:5px !important;
            font-size:8px !important;
            line-height:1 !important;
            font-weight:700 !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] p{
            font-size:8px !important;
            line-height:1 !important;
        }

        /* 상단 타이틀/간격 축소 */
        .cmp-top-strip{
            height:5px !important;
            margin-top:5px !important;
            margin-bottom:8px !important;
            border-radius:5px !important;
        }
        .cmp-page-head{
            margin-bottom:8px !important;
        }
        .cmp-eyebrow{
            font-size:8px !important;
            margin-bottom:4px !important;
            letter-spacing:.07em !important;
        }
        .cmp-page-head h1{
            font-size:21px !important;
            line-height:1.15 !important;
            margin:0 0 5px 0 !important;
        }
        .cmp-page-head p{
            font-size:10px !important;
            line-height:1.25 !important;
        }

        /* KPI 카드 축소: 잘림 방지 유지하면서 높이만 줄임 */
        .cmp-kpi-row{
            gap:8px !important;
            margin-bottom:11px !important;
            grid-template-columns:repeat(auto-fit,minmax(170px,1fr)) !important;
        }
        .cmp-kpi{
            min-height:74px !important;
            height:74px !important;
            padding:8px 11px 8px 14px !important;
            border-radius:6px !important;
            gap:3px !important;
            justify-content:center !important;
        }
        .cmp-kpi::before{
            width:3px !important;
            border-radius:6px 0 0 6px !important;
        }
        .cmp-kpi__label{
            font-size:8px !important;
            line-height:1.1 !important;
            letter-spacing:.04em !important;
        }
        .cmp-kpi__value{
            font-size:24px !important;
            line-height:1.08 !important;
            letter-spacing:-.04em !important;
        }
        .cmp-kpi__delta{
            font-size:9px !important;
            line-height:1.1 !important;
        }

        /* 모델별 공정 섹션 축소 */
        .cmp-sect-head{
            margin:10px 0 7px !important;
        }
        .cmp-sect-head__bar{
            width:3px !important;
            height:14px !important;
        }
        .cmp-sect-head__title{
            font-size:14px !important;
        }
        .cmp-sect-head__meta{
            font-size:10px !important;
        }
        .cmp-models{
            gap:10px !important;
            margin-bottom:22px !important;
            grid-template-columns:repeat(auto-fit,minmax(330px,1fr)) !important;
        }
        .cmp-model-col{
            padding:9px !important;
            border-radius:6px !important;
        }
        .cmp-model-col__head{
            font-size:11px !important;
            margin-bottom:7px !important;
            padding-bottom:6px !important;
        }
        .cmp-count{
            font-size:9px !important;
        }
        .cmp-proc-grid{
            grid-template-columns:repeat(auto-fill,minmax(92px,1fr)) !important;
            gap:4px !important;
        }
        .cmp-proc{
            height:39px !important;
            min-height:39px !important;
            border-radius:4px !important;
            padding:4px 5px !important;
        }
        .cmp-proc__name{
            font-size:8px !important;
            line-height:1.05 !important;
        }
        .cmp-proc__val{
            font-size:11px !important;
            line-height:1.05 !important;
        }

        /* 상세 분석 메뉴도 상단 상황판과 균형 맞게 살짝 위로/작게 */
        .home-head[style]{
            margin-top:28px !important;
        }
        .home-title{
            font-size:24px !important;
            line-height:1.15 !important;
            margin-bottom:8px !important;
        }
        .home-sub{
            font-size:12px !important;
            margin-bottom:14px !important;
        }



        /* =========================================================
           2026-05-07 Compact Layout V3
           - V2가 다소 작게 느껴지는 부분을 전체적으로 약 8~12% 확대
           - 필터는 여전히 1줄/저높이 유지
           - KPI/공정카드/타이틀 가독성만 소폭 개선
           ========================================================= */
        .block-container{
            padding-top:0.70rem !important;
            padding-left:1.50rem !important;
            padding-right:1.50rem !important;
            padding-bottom:1.10rem !important;
            max-width:1240px !important;
        }

        /* 필터: 한 줄 유지 + 너무 작아진 글자/버튼만 소폭 확대 */
        .cmp-filter-title{
            font-size:9px !important;
            line-height:1.05 !important;
            margin:0 0 2px 0 !important;
        }
        div[data-testid="stForm"]{
            padding:4px 7px !important;
            margin:0 0 8px 0 !important;
            border-radius:7px !important;
            min-height:34px !important;
        }
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"]{
            gap:0.18rem !important;
            align-items:center !important;
        }
        div[data-testid="stForm"] div[data-testid="column"]{
            padding:0 2px !important;
        }
        div[data-testid="stForm"] label,
        div[data-testid="stForm"] label p,
        div[data-testid="stForm"] p{
            font-size:9px !important;
            line-height:1.05 !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"]{
            min-height:24px !important;
            height:24px !important;
            gap:5px !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"] label{
            min-height:20px !important;
            height:20px !important;
        }
        div[data-testid="stForm"] input[type="radio"]{
            width:9px !important;
            height:9px !important;
            margin:0 3px 0 0 !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"]{
            min-height:24px !important;
            font-size:9px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] > div{
            min-height:24px !important;
            padding:0 3px !important;
            border-radius:6px !important;
            font-size:9px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] input{
            font-size:9px !important;
            height:15px !important;
            line-height:15px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"]{
            height:17px !important;
            min-height:17px !important;
            margin:1px 2px !important;
            padding:0 4px !important;
            border-radius:4px !important;
            max-width:92px !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] span{
            font-size:8.5px !important;
            line-height:15px !important;
            max-width:72px !important;
        }
        div[data-testid="stForm"] svg{
            width:9px !important;
            height:9px !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]{
            min-height:24px !important;
            height:24px !important;
            padding:0 6px !important;
            border-radius:6px !important;
            font-size:9px !important;
            line-height:1 !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] p{
            font-size:9px !important;
            line-height:1 !important;
        }

        /* CMP 타이틀/상단 간격: V2보다 조금 크게 */
        .cmp-top-strip{
            height:6px !important;
            margin-top:6px !important;
            margin-bottom:10px !important;
            border-radius:6px !important;
        }
        .cmp-page-head{
            margin-bottom:10px !important;
        }
        .cmp-eyebrow{
            font-size:9px !important;
            margin-bottom:5px !important;
            letter-spacing:.075em !important;
        }
        .cmp-page-head h1{
            font-size:23px !important;
            line-height:1.16 !important;
            margin:0 0 6px 0 !important;
        }
        .cmp-page-head p{
            font-size:11px !important;
            line-height:1.28 !important;
        }

        /* KPI 카드: 가독성 회복 */
        .cmp-kpi-row{
            gap:10px !important;
            margin-bottom:13px !important;
            grid-template-columns:repeat(auto-fit,minmax(185px,1fr)) !important;
        }
        .cmp-kpi{
            min-height:82px !important;
            height:82px !important;
            padding:10px 13px 10px 16px !important;
            border-radius:7px !important;
            gap:4px !important;
        }
        .cmp-kpi::before{
            width:3px !important;
            border-radius:7px 0 0 7px !important;
        }
        .cmp-kpi__label{
            font-size:9px !important;
            line-height:1.15 !important;
            letter-spacing:.045em !important;
        }
        .cmp-kpi__value{
            font-size:27px !important;
            line-height:1.10 !important;
            letter-spacing:-.04em !important;
        }
        .cmp-kpi__delta{
            font-size:10px !important;
            line-height:1.15 !important;
        }

        /* 모델/공정 카드: V2 대비 소폭 확대 */
        .cmp-sect-head{
            margin:12px 0 8px !important;
        }
        .cmp-sect-head__bar{
            width:3px !important;
            height:16px !important;
        }
        .cmp-sect-head__title{
            font-size:15px !important;
        }
        .cmp-sect-head__meta{
            font-size:11px !important;
        }
        .cmp-models{
            gap:12px !important;
            margin-bottom:26px !important;
            grid-template-columns:repeat(auto-fit,minmax(360px,1fr)) !important;
        }
        .cmp-model-col{
            padding:11px !important;
            border-radius:7px !important;
        }
        .cmp-model-col__head{
            font-size:12px !important;
            margin-bottom:8px !important;
            padding-bottom:7px !important;
        }
        .cmp-count{
            font-size:10px !important;
        }
        .cmp-proc-grid{
            grid-template-columns:repeat(auto-fill,minmax(105px,1fr)) !important;
            gap:5px !important;
        }
        .cmp-proc{
            height:44px !important;
            min-height:44px !important;
            border-radius:5px !important;
            padding:5px 6px !important;
        }
        .cmp-proc__name{
            font-size:9px !important;
            line-height:1.08 !important;
        }
        .cmp-proc__val{
            font-size:12px !important;
            line-height:1.08 !important;
        }

        /* 상세 분석 메뉴도 약간 확대 */
        .home-head[style]{
            margin-top:32px !important;
        }
        .home-title{
            font-size:26px !important;
            line-height:1.16 !important;
            margin-bottom:9px !important;
        }
        .home-sub{
            font-size:13px !important;
            margin-bottom:15px !important;
        }



        /* =========================================================
           2026-05-07 Filter Compact Alignment Reset
           - 이전 HTML 링크 방식/st.pills 방식 사용 안 함
           - 현재 코드의 st.form + st.radio + st.multiselect + submit button 구조만 정리
           - 수정 포인트: 아래 --home-filter-* 값만 조절하면 크기 변경 가능
           ========================================================= */
        :root{
            --home-filter-form-padding-y: 6px;
            --home-filter-form-padding-x: 10px;
            --home-filter-form-radius: 9px;
            --home-filter-control-height: 30px;
            --home-filter-tag-height: 20px;
            --home-filter-font-size: 10.5px;
            --home-filter-button-font-size: 11px;
            --home-filter-gap: 0.28rem;
        }

        .cmp-filter-title{
            font-size:10px !important;
            line-height:1 !important;
            font-weight:700 !important;
            color:#6B7280 !important;
            margin:0 0 5px 2px !important;
            padding:0 !important;
        }

        /* 필터 form 박스 자체 */
        div[data-testid="stForm"]{
            background:#FFFFFF !important;
            border:1px solid #E1E5EA !important;
            border-radius:var(--home-filter-form-radius) !important;
            padding:var(--home-filter-form-padding-y) var(--home-filter-form-padding-x) !important;
            margin:0 0 12px 0 !important;
            min-height:0 !important;
            box-shadow:none !important;
            overflow:visible !important;
        }

        /* st.columns 한 줄 정렬 */
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"]{
            align-items:center !important;
            gap:var(--home-filter-gap) !important;
        }
        div[data-testid="stForm"] div[data-testid="column"]{
            display:flex !important;
            align-items:center !important;
            justify-content:flex-start !important;
            min-height:var(--home-filter-control-height) !important;
            padding-top:0 !important;
            padding-bottom:0 !important;
        }
        div[data-testid="stForm"] div[data-testid="stElementContainer"],
        div[data-testid="stForm"] div[data-testid="stVerticalBlock"],
        div[data-testid="stForm"] div[data-testid="stVerticalBlockBorderWrapper"]{
            margin-top:0 !important;
            margin-bottom:0 !important;
            padding-top:0 !important;
            padding-bottom:0 !important;
            gap:0 !important;
        }

        /* radio: 기간 */
        div[data-testid="stForm"] div[role="radiogroup"]{
            min-height:var(--home-filter-control-height) !important;
            height:var(--home-filter-control-height) !important;
            display:flex !important;
            align-items:center !important;
            gap:8px !important;
            padding:0 !important;
            margin:0 !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"] label{
            min-height:22px !important;
            height:22px !important;
            display:flex !important;
            align-items:center !important;
            padding:0 !important;
            margin:0 !important;
        }
        div[data-testid="stForm"] div[role="radiogroup"] label p,
        div[data-testid="stForm"] label p,
        div[data-testid="stForm"] p{
            font-size:var(--home-filter-font-size) !important;
            line-height:1.05 !important;
            margin:0 !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] input[type="radio"]{
            width:10px !important;
            height:10px !important;
            margin:0 3px 0 0 !important;
        }

        /* multiselect: 영역/모델 */
        div[data-testid="stForm"] div[data-baseweb="select"]{
            min-height:var(--home-filter-control-height) !important;
            height:auto !important;
            font-size:var(--home-filter-font-size) !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] > div{
            min-height:var(--home-filter-control-height) !important;
            border-radius:8px !important;
            border-color:#DDE3EA !important;
            background:#FFFFFF !important;
            padding-top:1px !important;
            padding-bottom:1px !important;
            box-shadow:none !important;
        }
        div[data-testid="stForm"] div[data-baseweb="select"] input{
            font-size:var(--home-filter-font-size) !important;
            height:16px !important;
            line-height:16px !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"]{
            height:var(--home-filter-tag-height) !important;
            min-height:var(--home-filter-tag-height) !important;
            display:inline-flex !important;
            align-items:center !important;
            margin:1px 2px 1px 0 !important;
            padding:0 6px !important;
            border-radius:999px !important;
            background:#F8E5EC !important;
            border:1px solid #A50034 !important;
            color:#7E0027 !important;
            max-width:150px !important;
            overflow:hidden !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] span{
            color:#7E0027 !important;
            font-size:10px !important;
            line-height:18px !important;
            font-weight:700 !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            white-space:nowrap !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] svg{
            width:10px !important;
            height:10px !important;
            color:#7E0027 !important;
            fill:#7E0027 !important;
        }

        /* Apply / Reset 버튼 */
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"],
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]{
            height:var(--home-filter-control-height) !important;
            min-height:var(--home-filter-control-height) !important;
            display:flex !important;
            align-items:center !important;
            justify-content:center !important;
            padding:0 10px !important;
            margin:0 !important;
            border-radius:8px !important;
            font-size:var(--home-filter-button-font-size) !important;
            line-height:1 !important;
            font-weight:800 !important;
            box-shadow:none !important;
            white-space:nowrap !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"] p,
        div[data-testid="stForm"] button[kind="primaryFormSubmit"] p{
            font-size:var(--home-filter-button-font-size) !important;
            line-height:1 !important;
            font-weight:800 !important;
            margin:0 !important;
            padding:0 !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]{
            background:#FFFFFF !important;
            color:#111827 !important;
            border:1px solid #DDE3EA !important;
        }
        div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover{
            background:#F8E5EC !important;
            color:#7E0027 !important;
            border-color:#A50034 !important;
        }

        /* 필터 아래 요소와의 간격만 살짝 정리 */
        .cmp-top-strip{
            margin-top:8px !important;
        }



        /* =========================================================
           2026-05-07 Title First Layout
           - 'PRODUCTIVITY · CMP' 제거
           - '전체 CMP 요약 상황판'을 최상단으로 이동
           - 요약 필터를 제목 바로 아래 배치
           ========================================================= */
        .cmp-page-title-top{
            margin:0 0 10px 0 !important;
            padding:0 !important;
        }
        .cmp-page-title-top h1{
            margin:0 !important;
            padding:0 !important;
            font-family:var(--font-display), 'Malgun Gothic', '맑은 고딕', sans-serif !important;
            font-size:26px !important;
            line-height:1.18 !important;
            font-weight:800 !important;
            letter-spacing:-.03em !important;
            color:var(--ink-body) !important;
        }
        .cmp-filter-title{
            margin:0 0 5px 2px !important;
        }
        div[data-testid="stForm"]{
            margin-bottom:10px !important;
        }
        .cmp-summary-wrap{
            margin-top:0 !important;
        }
        .cmp-summary-meta{
            margin:0 0 10px 2px !important;
            padding:0 !important;
            color:var(--ink-muted) !important;
            font-size:11px !important;
            line-height:1.25 !important;
            font-weight:500 !important;
        }
        .cmp-top-strip,
        .cmp-eyebrow{
            display:none !important;
        }



        /* =========================================================
           2026-05-07 Filter Dropdown Font & Selected Tag Neutral
           - 대상: 요약 필터의 st.multiselect 드롭다운 목록 글자/선택 tag
           - 조절 위치: 아래 :root의 --home-filter-dropdown-* 값 변경
           ========================================================= */
        :root{
            --home-filter-dropdown-option-font-size: 10px;    /* 드롭다운 목록 글자 크기 */
            --home-filter-dropdown-option-height: 26px;       /* 드롭다운 목록 한 줄 높이 */
            --home-filter-selected-tag-font-size: 9.5px;      /* 선택된 항목 tag 글자 크기 */
            --home-filter-selected-tag-height: 20px;          /* 선택된 항목 tag 높이 */
            --home-filter-selected-tag-padding-x: 7px;        /* 선택된 항목 tag 좌우 여백 */
        }

        /* =========================================================
           1) 선택된 항목 tag: 흰 배경 + 검정 글자 + 검정 테두리
           ========================================================= */
        div[data-testid="stForm"] div[data-baseweb="tag"]{
            height:var(--home-filter-selected-tag-height) !important;
            min-height:var(--home-filter-selected-tag-height) !important;
            display:inline-flex !important;
            align-items:center !important;
            margin:1px 2px 1px 0 !important;
            padding:0 var(--home-filter-selected-tag-padding-x) !important;
            border-radius:999px !important;
            background:#FFFFFF !important;
            border:1px solid #111111 !important;
            color:#111111 !important;
            box-shadow:none !important;
            max-width:150px !important;
            overflow:hidden !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] span,
        div[data-testid="stForm"] div[data-baseweb="tag"] *{
            color:#111111 !important;
            fill:#111111 !important;
            font-size:var(--home-filter-selected-tag-font-size) !important;
            line-height:calc(var(--home-filter-selected-tag-height) - 2px) !important;
            font-weight:600 !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] span{
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            white-space:nowrap !important;
        }
        div[data-testid="stForm"] div[data-baseweb="tag"] svg{
            width:10px !important;
            height:10px !important;
        }

        /* 선택박스 내부 입력 글자도 같이 축소 */
        div[data-testid="stForm"] div[data-baseweb="select"] input,
        div[data-testid="stForm"] div[data-baseweb="select"] span,
        div[data-testid="stForm"] div[data-baseweb="select"] div{
            font-size:var(--home-filter-selected-tag-font-size) !important;
        }

        /* =========================================================
           2) 드롭다운 목록 글자 크기 축소
           BaseWeb popover는 form 밖 body 하단에 생성될 수 있어 전역 selector 필요
           ========================================================= */
        div[data-baseweb="popover"] div[role="listbox"],
        div[data-baseweb="popover"] ul,
        div[data-baseweb="menu"]{
            font-size:var(--home-filter-dropdown-option-font-size) !important;
        }
        div[data-baseweb="popover"] div[role="option"],
        div[data-baseweb="popover"] li,
        div[data-baseweb="menu"] div[role="option"],
        div[data-baseweb="menu"] li{
            min-height:var(--home-filter-dropdown-option-height) !important;
            height:var(--home-filter-dropdown-option-height) !important;
            padding-top:4px !important;
            padding-bottom:4px !important;
            font-size:var(--home-filter-dropdown-option-font-size) !important;
            line-height:1.15 !important;
            color:#111111 !important;
        }
        div[data-baseweb="popover"] div[role="option"] *,
        div[data-baseweb="popover"] li *,
        div[data-baseweb="menu"] div[role="option"] *,
        div[data-baseweb="menu"] li *{
            font-size:var(--home-filter-dropdown-option-font-size) !important;
            line-height:1.15 !important;
            color:#111111 !important;
        }

        /* 드롭다운 선택/hover 상태도 과한 색상 없이 연한 회색 정도로만 */
        div[data-baseweb="popover"] div[role="option"][aria-selected="true"],
        div[data-baseweb="popover"] li[aria-selected="true"],
        div[data-baseweb="popover"] div[role="option"]:hover,
        div[data-baseweb="popover"] li:hover{
            background:#F3F4F6 !important;
            color:#111111 !important;
        }



        /* =========================================================
           2026-05-07 TRUE FINAL - BaseWeb Multiselect Tag Neutral
           문제 원인:
           - 기존 selector가 div[data-baseweb="tag"]만 잡고 있었음
           - 현재 Streamlit/BaseWeb tag root가 span/button 등으로 렌더링될 수 있어 미적용됨
           해결:
           - element 종류와 상관없이 [data-baseweb="tag"] 전체를 직접 타겟팅
           - 내부 label/close icon까지 전부 흰배경/검정글자/검정테두리 강제
           ========================================================= */
        :root{
            --neutral-tag-bg:#FFFFFF;
            --neutral-tag-text:#111111;
            --neutral-tag-border:#111111;
            --neutral-tag-height:20px;
            --neutral-tag-font-size:9.5px;
            --neutral-tag-padding-x:7px;
        }

        /* 선택된 항목 tag root: div/span/button 등 태그 종류와 무관하게 적용 */
        html body .stApp [data-testid="stForm"] [data-baseweb="select"] [data-baseweb="tag"],
        html body .stApp [data-testid="stForm"] [data-testid="stMultiSelect"] [data-baseweb="tag"],
        html body .stApp [data-baseweb="select"] [data-baseweb="tag"],
        html body .stApp [data-testid="stMultiSelect"] [data-baseweb="tag"],
        html body .stApp [data-baseweb="tag"]{
            background:#FFFFFF !important;
            background-color:#FFFFFF !important;
            background-image:none !important;
            border:1px solid #111111 !important;
            border-color:#111111 !important;
            color:#111111 !important;
            box-shadow:none !important;
            height:var(--neutral-tag-height) !important;
            min-height:var(--neutral-tag-height) !important;
            border-radius:999px !important;
            padding:0 var(--neutral-tag-padding-x) !important;
            margin:1px 2px 1px 0 !important;
            display:inline-flex !important;
            align-items:center !important;
            justify-content:center !important;
            overflow:hidden !important;
        }

        /* tag 내부 모든 요소: 빨강/흰색 잔여 스타일 제거 */
        html body .stApp [data-testid="stForm"] [data-baseweb="select"] [data-baseweb="tag"] *,
        html body .stApp [data-testid="stForm"] [data-testid="stMultiSelect"] [data-baseweb="tag"] *,
        html body .stApp [data-baseweb="select"] [data-baseweb="tag"] *,
        html body .stApp [data-testid="stMultiSelect"] [data-baseweb="tag"] *,
        html body .stApp [data-baseweb="tag"] *{
            background:transparent !important;
            background-color:transparent !important;
            background-image:none !important;
            color:#111111 !important;
            fill:#111111 !important;
            stroke:#111111 !important;
            border-color:#111111 !important;
            font-size:var(--neutral-tag-font-size) !important;
            line-height:calc(var(--neutral-tag-height) - 2px) !important;
            font-weight:600 !important;
            box-shadow:none !important;
        }

        /* tag label 계열 - BaseWeb 버전별 대응 */
        html body .stApp [data-baseweb="tag"] [data-baseweb="tag-label"],
        html body .stApp [data-baseweb="tag"] span,
        html body .stApp [data-baseweb="tag"] div{
            color:#111111 !important;
            font-size:var(--neutral-tag-font-size) !important;
            font-weight:600 !important;
            overflow:hidden !important;
            text-overflow:ellipsis !important;
            white-space:nowrap !important;
            max-width:145px !important;
        }

        /* X 버튼/아이콘 계열 */
        html body .stApp [data-baseweb="tag"] svg,
        html body .stApp [data-baseweb="tag"] button,
        html body .stApp [data-baseweb="tag"] [role="button"]{
            color:#111111 !important;
            fill:#111111 !important;
            stroke:#111111 !important;
            background:transparent !important;
            background-color:transparent !important;
            border:none !important;
            box-shadow:none !important;
        }
        html body .stApp [data-baseweb="tag"] svg{
            width:10px !important;
            height:10px !important;
        }

        /* hover/focus 시에도 색 유지 */
        html body .stApp [data-baseweb="tag"]:hover,
        html body .stApp [data-baseweb="tag"]:focus,
        html body .stApp [data-baseweb="tag"]:active{
            background:#FFFFFF !important;
            background-color:#FFFFFF !important;
            color:#111111 !important;
            border-color:#111111 !important;
            box-shadow:none !important;
        }
        html body .stApp [data-baseweb="tag"]:hover *,
        html body .stApp [data-baseweb="tag"]:focus *,
        html body .stApp [data-baseweb="tag"]:active *{
            color:#111111 !important;
            fill:#111111 !important;
            stroke:#111111 !important;
        }



        /* =========================================================
           2026-05-07 FINAL COLOR ONLY OVERRIDE
           - 기존 적용 방식/selector 구조는 유지
           - 선택된 multiselect tag 색상만 요청 색상으로 변경
           - radio 버튼 색상도 동일 조합으로 변경
           요청 색상:
             background: var(--primary-tint) = #F8E5EC
             border-color: var(--primary)    = #A50034
             color: var(--primary-dark)      = #7E0027
           ========================================================= */

        /* 선택된 영역/모델 tag root */
        html body .stApp [data-testid="stForm"] [data-baseweb="select"] [data-baseweb="tag"],
        html body .stApp [data-testid="stForm"] [data-testid="stMultiSelect"] [data-baseweb="tag"],
        html body .stApp [data-baseweb="select"] [data-baseweb="tag"],
        html body .stApp [data-testid="stMultiSelect"] [data-baseweb="tag"],
        html body .stApp [data-baseweb="tag"]{
            background:var(--primary-tint) !important;
            background-color:var(--primary-tint) !important;
            background-image:none !important;
            border:1px solid var(--primary) !important;
            border-color:var(--primary) !important;
            color:var(--primary-dark) !important;
            box-shadow:none !important;
        }

        /* 선택된 tag 내부 텍스트 / X 아이콘 */
        html body .stApp [data-testid="stForm"] [data-baseweb="select"] [data-baseweb="tag"] *,
        html body .stApp [data-testid="stForm"] [data-testid="stMultiSelect"] [data-baseweb="tag"] *,
        html body .stApp [data-baseweb="select"] [data-baseweb="tag"] *,
        html body .stApp [data-testid="stMultiSelect"] [data-baseweb="tag"] *,
        html body .stApp [data-baseweb="tag"] *{
            background:transparent !important;
            background-color:transparent !important;
            background-image:none !important;
            color:var(--primary-dark) !important;
            fill:var(--primary-dark) !important;
            stroke:var(--primary-dark) !important;
            border-color:var(--primary) !important;
        }

        html body .stApp [data-baseweb="tag"]:hover,
        html body .stApp [data-baseweb="tag"]:focus,
        html body .stApp [data-baseweb="tag"]:active{
            background:var(--primary-tint) !important;
            background-color:var(--primary-tint) !important;
            color:var(--primary-dark) !important;
            border-color:var(--primary) !important;
            box-shadow:none !important;
        }

        html body .stApp [data-baseweb="tag"]:hover *,
        html body .stApp [data-baseweb="tag"]:focus *,
        html body .stApp [data-baseweb="tag"]:active *{
            color:var(--primary-dark) !important;
            fill:var(--primary-dark) !important;
            stroke:var(--primary-dark) !important;
        }

        /* =========================================================
           일간/주간 radio 색상 변경
           ========================================================= */

        /* native radio 자체 색상 */
        html body .stApp [data-testid="stForm"] input[type="radio"]{
            accent-color:var(--primary) !important;
        }

        /* radio 외곽/내부 원이 div/span/svg로 그려지는 Streamlit/BaseWeb 버전 대응 */
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label,
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label *{
            color:var(--ink-body) !important;
        }

        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked),
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked) *{
            color:var(--primary-dark) !important;
            fill:var(--primary) !important;
            stroke:var(--primary) !important;
        }

        html body .stApp [data-testid="stForm"] div[role="radiogroup"] input[type="radio"]:checked{
            accent-color:var(--primary) !important;
            background-color:var(--primary-tint) !important;
            border-color:var(--primary) !important;
        }

        /* radio hover 시 연한 tint 적용 */
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:hover{
            color:var(--primary-dark) !important;
        }
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:hover *{
            color:var(--primary-dark) !important;
            fill:var(--primary) !important;
            stroke:var(--primary) !important;
        }



        /* =========================================================
           2026-05-07 TRUE FINAL Radio Color Override
           - 일간/주간 st.radio의 Streamlit/BaseWeb 기본 주황/빨강 색상 제거
           - 기존 multiselect tag 적용 방식은 유지
           - 요청 조합:
             background:var(--primary-tint);  #F8E5EC
             border-color:var(--primary);     #A50034
             color:var(--primary-dark);       #7E0027
           ========================================================= */

        /* native radio가 노출되는 브라우저/버전 대응 */
        html body .stApp [data-testid="stForm"] input[type="radio"]{
            accent-color:#A50034 !important;
        }

        /* BaseWeb radio label 전체 기본 정렬/글자 */
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label,
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]{
            display:inline-flex !important;
            align-items:center !important;
            color:#111827 !important;
        }
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label p,
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"] p{
            color:#111827 !important;
        }

        /* BaseWeb radio 원형 외곽: 기본/미선택 */
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"] > div:first-child,
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label > div:first-child{
            background:#FFFFFF !important;
            background-color:#FFFFFF !important;
            background-image:none !important;
            border-color:#D1D5DB !important;
            box-shadow:none !important;
        }

        /* 선택된 radio label 글자색 */
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:has(input[type="radio"]:checked),
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked),
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) *,
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked) *{
            color:#7E0027 !important;
            fill:#7E0027 !important;
            stroke:#A50034 !important;
        }

        /* 선택된 radio 외곽 원 */
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) > div:first-child,
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked) > div:first-child{
            background:#F8E5EC !important;
            background-color:#F8E5EC !important;
            background-image:none !important;
            border-color:#A50034 !important;
            box-shadow:none !important;
        }

        /* 선택된 radio 내부 점/dot. BaseWeb 버전별로 div/span/svg가 달라서 넓게 대응 */
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) > div:first-child > div,
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) > div:first-child span,
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked) > div:first-child > div,
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked) > div:first-child span{
            background:#7E0027 !important;
            background-color:#7E0027 !important;
            border-color:#7E0027 !important;
            box-shadow:none !important;
        }

        /* aria-checked 구조로 렌더링되는 경우 대응 */
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] [aria-checked="true"],
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"] [aria-checked="true"]{
            background:#F8E5EC !important;
            background-color:#F8E5EC !important;
            border-color:#A50034 !important;
            color:#7E0027 !important;
            box-shadow:none !important;
        }
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] [aria-checked="true"] *,
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"] [aria-checked="true"] *{
            color:#7E0027 !important;
            fill:#7E0027 !important;
            stroke:#A50034 !important;
        }

        /* inline style로 빨간 배경이 박힌 custom radio dot 대응: radio group 안에서만 제한 적용 */
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked) div[style*="background"],
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) div[style*="background"]{
            background:#F8E5EC !important;
            background-color:#F8E5EC !important;
            border-color:#A50034 !important;
            color:#7E0027 !important;
        }

        /* dot처럼 작은 내부 요소는 primary-dark로 다시 지정 */
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:has(input[type="radio"]:checked) div[style*="background"] div,
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:has(input[type="radio"]:checked) div[style*="background"] div{
            background:#7E0027 !important;
            background-color:#7E0027 !important;
        }

        /* hover도 동일 계열 */
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:hover,
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:hover{
            color:#7E0027 !important;
        }
        html body .stApp [data-testid="stForm"] div[role="radiogroup"] label:hover > div:first-child,
        html body .stApp [data-testid="stForm"] label[data-baseweb="radio"]:hover > div:first-child{
            background:#F8E5EC !important;
            background-color:#F8E5EC !important;
            border-color:#A50034 !important;
        }

</style>""", unsafe_allow_html=True)

def build_contact_mailto_url() -> str:
    recipients = ",".join([mail.strip() for mail in CONTACT_MAIL_TO if mail.strip()])
    query = urllib.parse.urlencode({"subject": CONTACT_MAIL_SUBJECT, "body": CONTACT_MAIL_BODY})
    return f"mailto:{recipients}?{query}"


def clean_text_series(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    return s.mask(s.isin({"nan", "NaN", "None", "NONE", "null", "NULL", "", "-"})).astype(object)


def fmt_pct(v) -> str:
    if pd.isna(v):
        return "-"
    return f"{float(v) * 100:.1f}%"


def fmt_delta(v):
    if pd.isna(v):
        return "-", "neutral"
    if v >= 0:
        return f"▲ +{float(v) * 100:.1f}%", "good"
    return f"▼ {float(v) * 100:.1f}%", "bad"


def achievement_class(v) -> str:
    if pd.isna(v):
        return "empty"
    if v >= 1.00:
        return "good"
    if v >= 0.95:
        return "warn"
    return "bad"


def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


@st.cache_resource(show_spinner=False)
def get_cmp_engine():
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(
        url,
        future=True,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"options": "-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000"},
    )


@st.cache_data(show_spinner=False, ttl=600)
def load_cmp_data() -> pd.DataFrame:
    query = text(f"""
        SELECT
            {quote_ident(DB_WORK_DATE_COL)} AS work_date,
            {quote_ident(DB_PERIOD_COL)} AS period,
            {quote_ident(DB_AREA_COL)} AS area,
            {quote_ident(DB_MODEL_COL)} AS model,
            {quote_ident(DB_PROCESS_COL)} AS process_l1,
            {quote_ident(DB_EQUIPMENT_COL)} AS equipment,
            {quote_ident(DB_CMP_RATE_COL)} AS cmp_achievement_rate
        FROM {quote_ident(DB_SCHEMA)}.{quote_ident(DB_TABLE)}
        WHERE {quote_ident(DB_WORK_DATE_COL)} IS NOT NULL
          AND {quote_ident(DB_AREA_COL)} IS NOT NULL
          AND {quote_ident(DB_MODEL_COL)} IS NOT NULL
          AND {quote_ident(DB_PROCESS_COL)} IS NOT NULL
          AND {quote_ident(DB_CMP_RATE_COL)} IS NOT NULL
          AND {quote_ident(DB_WORK_DATE_COL)} >= CURRENT_DATE - (:lookback_months || ' months')::interval
    """)
    with get_cmp_engine().connect() as conn:
        raw = pd.read_sql(query, conn, params={"lookback_months": DASHBOARD_DB_LOOKBACK_MONTHS})

    df = raw.rename(columns={
        "work_date": DATE_COL,
        "period": PERIOD_COL,
        "area": AREA_COL,
        "model": MODEL_COL,
        "process_l1": PROCESS_COL,
        "cmp_achievement_rate": CMP_COL,
    })
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce").dt.normalize()
    df[PERIOD_COL] = clean_text_series(df[PERIOD_COL])
    for col in [AREA_COL, MODEL_COL, PROCESS_COL]:
        df[col] = clean_text_series(df[col])
    df[CMP_COL] = pd.to_numeric(df[CMP_COL], errors="coerce")
    df.loc[(df[CMP_COL] < 0) | (df[CMP_COL] > MAX_VALID_ACHIEVEMENT), CMP_COL] = np.nan
    return df.dropna(subset=[DATE_COL, AREA_COL, MODEL_COL, PROCESS_COL, CMP_COL])


def get_latest_windows(df: pd.DataFrame, view_mode: str):
    latest_date = df[DATE_COL].max()
    if pd.isna(latest_date):
        return None
    if view_mode == "주간":
        cur_start, cur_end = latest_date - pd.Timedelta(days=6), latest_date
        prev_start, prev_end = cur_start - pd.Timedelta(days=7), cur_start - pd.Timedelta(days=1)
    else:
        cur_start = cur_end = latest_date
        prev_dates = df.loc[df[DATE_COL] < latest_date, DATE_COL].dropna()
        prev_start = prev_end = None if prev_dates.empty else prev_dates.max()
    return cur_start, cur_end, prev_start, prev_end, latest_date


def window_filter(df: pd.DataFrame, start, end) -> pd.DataFrame:
    if start is None or end is None:
        return df.iloc[0:0].copy()
    return df[(df[DATE_COL] >= start) & (df[DATE_COL] <= end)].copy()


def build_summary(df: pd.DataFrame, areas: list[str], models: list[str], view_mode: str):
    base = df.copy()
    if areas:
        base = base[base[AREA_COL].isin(areas)]
    if models:
        base = base[base[MODEL_COL].isin(models)]
    if base.empty:
        return None

    win = get_latest_windows(base, view_mode)
    if win is None:
        return None
    cur_start, cur_end, prev_start, prev_end, latest_date = win
    cur = window_filter(base, cur_start, cur_end)
    prev = window_filter(base, prev_start, prev_end)

    overall = cur[CMP_COL].mean()
    prev_overall = prev[CMP_COL].mean()
    overall_delta = overall - prev_overall if not pd.isna(prev_overall) else np.nan

    model_cur = cur.groupby(MODEL_COL, dropna=False)[CMP_COL].mean().reset_index(name="cmp")
    model_prev = prev.groupby(MODEL_COL, dropna=False)[CMP_COL].mean().reset_index(name="prev_cmp")
    model_summary = model_cur.merge(model_prev, on=MODEL_COL, how="left")
    model_summary["delta"] = model_summary["cmp"] - model_summary["prev_cmp"]
    model_summary = model_summary.sort_values(MODEL_COL)

    proc_summary = (
        cur.groupby([MODEL_COL, PROCESS_COL], dropna=False)[CMP_COL]
        .mean()
        .reset_index(name="cmp")
        .sort_values([MODEL_COL, PROCESS_COL])
    )
    return {
        "cur": cur,
        "cur_start": cur_start,
        "cur_end": cur_end,
        "latest_date": latest_date,
        "view_mode": view_mode,
        "overall": overall,
        "overall_delta": overall_delta,
        "model_summary": model_summary,
        "proc_summary": proc_summary,
    }


def render_kpi(label, value, delta):
    d, cls = fmt_delta(delta)
    return (
        f"<div class='cmp-kpi'>"
        f"<div class='cmp-kpi__label'>{html.escape(str(label))}</div>"
        f"<div class='cmp-kpi__value'>{fmt_pct(value)}</div>"
        f"<div class='cmp-kpi__delta {cls}'>{html.escape(d)}</div>"
        f"</div>"
    )


def render_summary_html(summary):
    cur_start, cur_end = summary["cur_start"], summary["cur_end"]
    period_label = f"{cur_start:%Y-%m-%d}" if cur_start == cur_end else f"{cur_start:%Y-%m-%d} ~ {cur_end:%Y-%m-%d}"

    kpis = [render_kpi("전체 달성률", summary["overall"], summary["overall_delta"])]
    for _, r in summary["model_summary"].iterrows():
        kpis.append(render_kpi(f"{r[MODEL_COL]} 달성률", r["cmp"], r["delta"]))

    blocks = []
    for model in summary["model_summary"][MODEL_COL].tolist():
        mdf = summary["proc_summary"][summary["proc_summary"][MODEL_COL] == model]
        cards = []
        for _, r in mdf.iterrows():
            cls = achievement_class(r["cmp"])
            proc = html.escape(str(r[PROCESS_COL]))
            cards.append(
                f"<div class='cmp-proc {cls}' title='{proc}'>"
                f"<div class='cmp-proc__name'>{proc}</div>"
                f"<div class='cmp-proc__val'>{fmt_pct(r['cmp'])}</div>"
                f"</div>"
            )
        blocks.append(
            f"<div class='cmp-model-col'>"
            f"<div class='cmp-model-col__head'><span>{html.escape(str(model))}</span><span class='cmp-count'>{len(mdf)} 공정</span></div>"
            f"<div class='cmp-proc-grid'>{''.join(cards)}</div>"
            f"</div>"
        )

    st.markdown(
        f"""
        <div class="cmp-summary-wrap">
            <div class="cmp-summary-meta">{html.escape(summary['view_mode'])} 기준 · {html.escape(period_label)} · 영역/모델 필터 적용 결과</div>
            <div class="cmp-kpi-row">{''.join(kpis)}</div>
            <div class="cmp-sect-head">
                <div class="cmp-sect-head__left"><div class="cmp-sect-head__bar"></div><div class="cmp-sect-head__title">모델별 공정 달성률</div></div>
                <div class="cmp-sect-head__meta">마지막 갱신 {summary['latest_date']:%Y-%m-%d}</div>
            </div>
            <div class="cmp-models">{''.join(blocks)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init_filter_state(df):
    all_areas = sorted(df[AREA_COL].dropna().astype(str).unique().tolist())
    all_models = sorted(df[MODEL_COL].dropna().astype(str).unique().tolist())
    st.session_state.setdefault("home_cmp_view_mode", "일간")
    st.session_state.setdefault("home_cmp_selected_areas", all_areas)
    st.session_state.setdefault("home_cmp_selected_models", all_models)
    st.session_state["home_cmp_selected_areas"] = [x for x in st.session_state["home_cmp_selected_areas"] if x in all_areas] or all_areas
    st.session_state["home_cmp_selected_models"] = [x for x in st.session_state["home_cmp_selected_models"] if x in all_models] or all_models


def render_cmp_filter(df):
    all_areas = sorted(df[AREA_COL].dropna().astype(str).unique().tolist())
    all_models = sorted(df[MODEL_COL].dropna().astype(str).unique().tolist())

    # 필터 영역은 Home 상단 공간을 많이 차지하지 않도록 라벨을 접고 한 줄로 압축합니다.
    st.markdown("<div class='cmp-filter-title'>요약 필터</div>", unsafe_allow_html=True)
    with st.form("home_cmp_filter_form", border=False):
        c1, c2, c3, c4, c5 = st.columns([0.85, 4.45, 2.45, 0.72, 0.72], gap="small")
        with c1:
            view_mode = st.radio(
                "기간",
                ["일간", "주간"],
                index=0 if st.session_state["home_cmp_view_mode"] == "일간" else 1,
                horizontal=True,
                label_visibility="collapsed",
            )
        with c2:
            areas = st.multiselect(
                "영역",
                all_areas,
                default=st.session_state["home_cmp_selected_areas"],
                label_visibility="collapsed",
                placeholder="영역",
            )
        with c3:
            models = st.multiselect(
                "모델",
                all_models,
                default=st.session_state["home_cmp_selected_models"],
                label_visibility="collapsed",
                placeholder="모델",
            )
        with c4:
            apply_clicked = st.form_submit_button("Apply", use_container_width=True)
        with c5:
            reset_clicked = st.form_submit_button("Reset", use_container_width=True)

    if reset_clicked:
        st.session_state["home_cmp_view_mode"] = "일간"
        st.session_state["home_cmp_selected_areas"] = all_areas
        st.session_state["home_cmp_selected_models"] = all_models
        st.rerun()
    if apply_clicked:
        st.session_state["home_cmp_view_mode"] = view_mode
        st.session_state["home_cmp_selected_areas"] = areas or all_areas
        st.session_state["home_cmp_selected_models"] = models or all_models
        st.rerun()
    return st.session_state["home_cmp_view_mode"], st.session_state["home_cmp_selected_areas"], st.session_state["home_cmp_selected_models"]

def render_cmp_summary_section():
    try:
        df = load_cmp_data()
    except Exception as e:
        st.error(f"CMP 요약 데이터 로딩 실패: {e}")
        st.caption("DB 컬럼 기준: mart_cmp_dashboard_daily.work_date, area, model, process_l1, equipment, cmp_achievement_rate")
        return
    if df.empty:
        st.warning("CMP 요약 상황판에 표시할 데이터가 없습니다.")
        return
    init_filter_state(df)

    # preview sec-home-1 와 정렬 — vit-top-strip 6px wine + flat title.
    from ui.vitals.components import render_top_strip
    render_top_strip()
    st.markdown(
        """
        <div class="cmp-page-title-top">
            <h1>전체 CMP 요약 상황판</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    view_mode, areas, models = render_cmp_filter(df)
    summary = build_summary(df, areas, models, view_mode)
    if summary is None or summary["cur"].empty:
        st.warning("선택한 조건에 해당하는 CMP 데이터가 없습니다.")
        return
    render_summary_html(summary)


def render_card_button(key: str, page: str, title: str, desc: str, disabled: bool = False) -> None:
    label = f"{title}\n{desc}"
    clicked = st.button(label, key=f"home_card_{key}", use_container_width=True, disabled=disabled)
    if clicked and not disabled:
        st.switch_page(page)


def _render_category_heading(ko: str, en: str, desc: str = "") -> None:
    """우리 home.html mockup 의 3-카테고리 헤딩 (좌 와인 vertical bar + Ko + En sub).
    백엔드 호출 0 — 순수 HTML 렌더."""
    st.markdown(
        f"""
        <div class="vit-cat-head">
            <span class="vit-cat-bar"></span>
            <h3 class="vit-cat-title">{ko}<span class="vit-cat-sub">{en}</span></h3>
            {f'<p class="vit-cat-desc">{desc}</p>' if desc else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_menu_section():
    """상세 분석 메뉴 — 우리 home.html mockup 처럼 3 대분류로 그룹.
       - 생산 (Production): CMP Dashboard
       - 설비 성능 (Equipment Performance): UPH Dashboard
       - 설비 효율 (Equipment Efficiency): MTBA Dashboard, MTBA Detail View, MaxCapa Chat
       각 카드의 click → switch_page 백엔드 호출 동일 (render_card_button 그대로 사용)."""
    st.markdown(
        """
        <div class="home-head" style="margin-top:44px;">
            <h2 class="home-title">분석 도구</h2>
            <p class="home-sub">상단 요약에서 이상 공정/모델을 확인한 후, 아래 카테고리 별 도구에서 상세 분석 화면으로 이동하세요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 카테고리 1: 생산 (CMP) ─────────────────────────────────
    _render_category_heading("생산", "Production", "공정별 달성률 · 라인 KPI")
    cat1 = st.columns(3, gap="medium")
    with cat1[0]:
        render_card_button("cmp", PAGES["cmp"], "CMP Dashboard", "공정별 CMP 달성률 추이 · 영역×모델×기간 필터로 조회")
    with cat1[1]:
        st.empty()
    with cat1[2]:
        st.empty()

    # ── 카테고리 2: 설비 성능 (UPH) ────────────────────────────
    _render_category_heading("설비 성능", "Equipment Performance", "UPH · 동작시간 · 편차 분석")
    cat2 = st.columns(3, gap="medium")
    with cat2[0]:
        render_card_button("uph", PAGES["uph"], "UPH Dashboard", "UPH · 동작시간 분석 · I-TAS 분기 + 6 섹션 추적")
    with cat2[1]:
        st.empty()
    with cat2[2]:
        st.empty()

    # ── 카테고리 3: 설비 효율 (MTBA + MaxCapa Chat) ────────────
    _render_category_heading("설비 효율", "Equipment Efficiency", "MTBA · 알람 · 자연어 분석")
    cat3 = st.columns(3, gap="medium")
    with cat3[0]:
        render_card_button("mtba", PAGES["mtba"], "MTBA Dashboard", "공정별 MTBA 통계 · 다중 패널 · 메모/이미지 업로드")
    with cat3[1]:
        render_card_button("mtba_detail", PAGES["mtba_detail"], "MTBA Detail View", "패널 기반 드릴다운 · 공정×설비 매트릭스 · 알람 상세 팝업")
    with cat3[2]:
        render_card_button("chat", PAGES["chat"], "MaxCapa Chat", "대화형 생산지표 조회 · MES UPH / ITAS UPH 자연어 질의", disabled=True)


def render_contact_box():
    contact_mailto_url = build_contact_mailto_url()
    st.markdown(
        f"""
        <div class="home-footer">
            <span>제작 · 광학 Max Capa TDR</span>
            <span class="footer-sep">|</span>
            <a class="contact-mail-button" href="{contact_mailto_url}">📧 문의 메일 보내기</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_home_mode_selector() -> str:
    """Home 페이지 상단 3-모드 선택기.
    - current  : 우리 home.html 디자인 (3 카테고리 메뉴) — 기본
    - case1    : 심플 필터 + Best 3 / Worst 3 CMP 카드
    - case2    : 원본 zip 의 CMP 요약 상황판 (디자인은 Vitals 톤)
    Returns: 현재 선택된 모드 키.
    """
    st.markdown(
        """
        <style>
        .vit-mode-bar {
            display:flex; align-items:center; gap:6px; flex-wrap:wrap;
            padding: 6px;
            background: var(--soft);
            border: 1px solid var(--border);
            border-radius: 10px;
            margin-bottom: 22px;
            width: max-content;
        }
        .vit-mode-bar .vit-mode-eyebrow{
            font-family: var(--font-mono);
            font-size: 10px; font-weight: 700; letter-spacing: .1em;
            color: var(--ink-subtle); text-transform: uppercase;
            padding: 0 10px;
        }
        /* 모드 버튼 — st-key 로 스코프 */
        div[class*="st-key-vit_mode_btn_"] button {
            background: transparent !important;
            border: 1px solid transparent !important;
            color: var(--ink-muted) !important;
            font-weight: 600 !important;
            min-height: 32px !important;
            padding: 0 14px !important;
            border-radius: 8px !important;
            box-shadow: none !important;
        }
        div[class*="st-key-vit_mode_btn_"] button:hover {
            background: rgba(255,255,255,0.7) !important;
            color: var(--ink-body) !important;
        }
        div[class*="st-key-vit_mode_btn_"] button:disabled,
        div[class*="st-key-vit_mode_btn_"] button[disabled] {
            background: var(--card-bg) !important;
            border-color: var(--border) !important;
            color: var(--ink-body) !important;
            font-weight: 700 !important;
            box-shadow: 0 1px 2px rgba(15,17,21,0.04) !important;
            opacity: 1 !important;
            cursor: default !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 기본값: 'current'
    mode = st.session_state.get("home_mode", "current")

    # 모드 바 — 3 버튼 + 안내 eyebrow
    st.markdown('<div class="vit-mode-bar">', unsafe_allow_html=True)
    cols = st.columns([1.4, 1.6, 2.0, 2.6, 1.0])
    with cols[0]:
        st.markdown('<span class="vit-mode-eyebrow">View</span>', unsafe_allow_html=True)
    with cols[1]:
        if st.button("기본", key="vit_mode_btn_current", disabled=(mode == "current")):
            st.session_state["home_mode"] = "current"
            st.rerun()
    with cols[2]:
        if st.button("Best · Worst 카드", key="vit_mode_btn_case1", disabled=(mode == "case1")):
            st.session_state["home_mode"] = "case1"
            st.rerun()
    with cols[3]:
        if st.button("CMP 요약 상황판", key="vit_mode_btn_case2", disabled=(mode == "case2")):
            st.session_state["home_mode"] = "case2"
            st.rerun()
    with cols[4]:
        st.empty()
    st.markdown('</div>', unsafe_allow_html=True)

    return mode


def _render_simple_cmp_filter(df):
    """Case 1 전용 — 심플 필터: 일/주 토글 + 영역(전체 또는 선택). 모델 필터는 생략 (직관적).
    Returns: (view_mode, areas, models) — build_summary 호환.
    """
    init_filter_state(df)
    st.markdown('<div class="cmp-filter-title">요약 필터</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([0.85, 4.0, 1.5], gap="small")
    with c1:
        view_mode = st.radio(
            "기간",
            options=["일별", "주간"],
            index=0 if st.session_state.get("home_view_mode_simple", "일별") == "일별" else 1,
            horizontal=True,
            key="home_view_mode_simple",
            label_visibility="collapsed",
        )
    with c2:
        all_areas = sorted(df[AREA_COL].dropna().unique().tolist())
        areas = st.multiselect(
            "영역",
            options=all_areas,
            default=st.session_state.get("home_areas_simple", all_areas),
            key="home_areas_simple",
            label_visibility="collapsed",
            placeholder="영역(전체) — 비우면 모든 영역",
        )
    with c3:
        st.markdown(
            f'<div style="font-family:var(--font-mono);font-size:11px;color:var(--ink-subtle);'
            f'letter-spacing:.06em;text-transform:uppercase;text-align:right;padding-top:6px;">'
            f"latest · {df[DATE_COL].max().strftime('%Y-%m-%d') if not df.empty else '-'}</div>",
            unsafe_allow_html=True,
        )
    # 모델 미선택 = 전체
    return view_mode, areas, []


def _compute_best_worst_processes(summary, n: int = 3):
    """summary["cur"] 에서 공정별 평균 CMP 달성률 계산 → Best n / Worst n 반환.
    Returns: (best_df, worst_df) — 각 DataFrame 컬럼: process_l1, area, model, cmp_rate."""
    cur = summary.get("cur") if summary else None
    if cur is None or cur.empty:
        empty = pd.DataFrame(columns=[PROCESS_COL, AREA_COL, MODEL_COL, CMP_COL])
        return empty, empty

    # 공정 단위 평균 (영역·모델 cross — 가장 큰 단위로 집계)
    proc = (
        cur.groupby(PROCESS_COL, as_index=False)
           .agg({CMP_COL: "mean", AREA_COL: "first", MODEL_COL: "first"})
    )
    proc = proc.dropna(subset=[CMP_COL])
    proc_sorted = proc.sort_values(CMP_COL, ascending=False)
    best = proc_sorted.head(n).reset_index(drop=True)
    worst = proc_sorted.tail(n).iloc[::-1].reset_index(drop=True)  # 최악 1위 먼저
    return best, worst


def _render_proc_card(rank: int, row, kind: str = "best"):
    """단일 공정 카드 — 우리 home.html 의 카드 톤 + 신호등 색.
    kind: 'best' / 'worst' / 'mid'."""
    proc_name = str(row.get(PROCESS_COL, "-"))
    rate = row.get(CMP_COL)
    klass = achievement_class(rate)  # 'good' / 'warn' / 'bad' / 'empty'
    rate_str = fmt_pct(rate)
    area_lbl = row.get(AREA_COL, "")
    model_lbl = row.get(MODEL_COL, "")

    st.markdown(
        f"""
        <div class="vit-proc-card vit-proc-card--{kind} vit-proc-card--{klass}">
            <div class="vit-proc-card__rank">#{rank}</div>
            <div class="vit-proc-card__title">{html.escape(proc_name)}</div>
            <div class="vit-proc-card__rate vit-rate--{klass}">{rate_str}</div>
            <div class="vit-proc-card__meta">
                <span>{html.escape(str(area_lbl))}</span>
                <span class="vit-proc-card__sep">·</span>
                <span>{html.escape(str(model_lbl))}</span>
            </div>
            <div class="vit-proc-card__sec">
                <span class="vit-proc-card__sec-label">UPH</span>
                <span class="vit-proc-card__sec-val">—</span>
                <span class="vit-proc-card__sec-sep">·</span>
                <span class="vit-proc-card__sec-label">MTBA</span>
                <span class="vit-proc-card__sec-val">—</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_case1_best_worst_cards():
    """Case 1 — 심플 필터 + Best 3 / Worst 3 CMP 카드 (신호등 색).
    UPH/MTBA 는 백엔드 호출 구조상 페이지 단일 컨텍스트에서 process×model 단위로
    한번에 가져올 수 없어 카드 안에는 '—' 로 placeholder, 안내문 표시.
    """
    try:
        df = load_cmp_data()
    except Exception as e:
        st.error(f"CMP 데이터 로딩 실패: {e}")
        return
    if df.empty:
        st.warning("CMP 데이터가 없습니다.")
        return

    # preview sec-home-2 와 정렬 — vit-top-strip 6px wine + flat title.
    from ui.vitals.components import render_top_strip
    render_top_strip()
    st.markdown(
        """
        <div class="cmp-page-title-top">
            <h1>전체 CMP 요약 · Best 3 / Worst 3</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
    view_mode, areas, models = _render_simple_cmp_filter(df)
    summary = build_summary(df, areas, models, view_mode)
    if summary is None or summary.get("cur") is None or summary["cur"].empty:
        st.info("선택한 조건에 데이터가 없습니다.")
        return

    best_df, worst_df = _compute_best_worst_processes(summary, n=3)
    if best_df.empty and worst_df.empty:
        # 모든 공정이 NaN/0 인 edge case — 빈 카드 그리드 대신 안내문 표시.
        st.info("선택 조건의 공정별 CMP 달성률 데이터가 모두 비어 있습니다.")
        return

    # CSS once
    st.markdown(
        """
        <style>
        .vit-best-worst-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom: 14px; }
        @media (max-width:1280px){ .vit-best-worst-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width:980px){  .vit-best-worst-grid { grid-template-columns: 1fr; } }
        .vit-proc-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-left: 4px solid var(--border-strong);
            border-radius: 12px;
            padding: 14px 16px;
            display:flex; flex-direction:column; gap:6px;
            position: relative;
        }
        .vit-proc-card--good  { border-left-color: var(--status-good); background: linear-gradient(180deg, var(--status-good-tint) 0%, var(--card-bg) 60%); }
        .vit-proc-card--warn  { border-left-color: var(--status-warn); background: linear-gradient(180deg, var(--status-warn-tint, #FAF1DD) 0%, var(--card-bg) 60%); }
        .vit-proc-card--bad   { border-left-color: var(--status-bad);  background: linear-gradient(180deg, #FDECEF 0%, var(--card-bg) 60%); }
        .vit-proc-card--empty { border-left-color: var(--border-strong); }
        .vit-proc-card__rank {
            font-family: var(--font-mono);
            font-size: 10px; font-weight:700; letter-spacing: .1em;
            color: var(--ink-subtle); text-transform: uppercase;
        }
        .vit-proc-card__title {
            font-family: var(--font-display);
            font-size: 16px; font-weight:700; letter-spacing:-0.01em;
            color: var(--ink-body);
        }
        .vit-proc-card__rate {
            font-family: var(--font-mono);
            font-size: 28px; font-weight:700; letter-spacing:-0.02em;
            line-height: 1.05;
        }
        .vit-rate--good  { color: var(--status-good); }
        .vit-rate--warn  { color: var(--status-warn); }
        .vit-rate--bad   { color: var(--status-bad); }
        .vit-rate--empty { color: var(--ink-subtle); }
        .vit-proc-card__meta {
            font-family: var(--font-mono); font-size:11px; color: var(--ink-muted);
            display:flex; gap:6px; flex-wrap:wrap;
        }
        .vit-proc-card__sep,
        .vit-proc-card__sec-sep { color: var(--ink-subtle); }
        .vit-proc-card__sec {
            margin-top:4px; padding-top:8px;
            border-top: 1px dashed var(--border);
            display:flex; gap:6px; flex-wrap:wrap;
            font-family: var(--font-mono); font-size:11px; color: var(--ink-muted);
        }
        .vit-proc-card__sec-label { font-weight:700; color: var(--ink-subtle); letter-spacing: .04em; text-transform: uppercase; }
        .vit-proc-card__sec-val   { color: var(--ink-body); font-weight:600; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Worst 3 (먼저 — 주의 환기)
    st.markdown('<div class="vit-cat-head"><span class="vit-cat-bar"></span><h3 class="vit-cat-title">Worst 3<span class="vit-cat-sub">개선 우선순위</span></h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="vit-best-worst-grid">', unsafe_allow_html=True)
    cols_w = st.columns(3, gap="small")
    for i, (idx, row) in enumerate(worst_df.iterrows()):
        with cols_w[i % 3]:
            _render_proc_card(i + 1, row, kind="worst")
    st.markdown('</div>', unsafe_allow_html=True)

    # Best 3
    st.markdown('<div class="vit-cat-head" style="margin-top:18px;"><span class="vit-cat-bar"></span><h3 class="vit-cat-title">Best 3<span class="vit-cat-sub">달성률 상위</span></h3></div>', unsafe_allow_html=True)
    st.markdown('<div class="vit-best-worst-grid">', unsafe_allow_html=True)
    cols_b = st.columns(3, gap="small")
    for i, (idx, row) in enumerate(best_df.iterrows()):
        with cols_b[i % 3]:
            _render_proc_card(i + 1, row, kind="best")
    st.markdown('</div>', unsafe_allow_html=True)

    # 데이터 가용성 안내 (UPH/MTBA placeholder)
    st.markdown(
        '<div class="cmp-page-title-top" style="margin-top:18px;"><p class="home-sub" '
        'style="font-size:12px;color:var(--ink-subtle);">'
        'UPH · MTBA 는 모델·기간 컨텍스트가 필요해 카드 내에서는 표시 생략. '
        '각 공정의 상세는 우측 상단 카테고리 메뉴(UPH / MTBA Dashboard)에서 확인하세요.'
        '</p></div>',
        unsafe_allow_html=True,
    )


def main():
    inject_css()
    mode = render_home_mode_selector()

    if mode == "case1":
        # Case 1 — 심플 필터 + Best/Worst 카드
        render_case1_best_worst_cards()
        render_menu_section()
        render_contact_box()
    elif mode == "case2":
        # Case 2 — 원본 zip 의 CMP 요약 상황판 구조 (디자인은 Vitals 톤)
        render_cmp_summary_section()
        render_menu_section()
        render_contact_box()
    else:
        # Current (default) — 우리 home.html 디자인 (3 카테고리 메뉴 only)
        render_menu_section()
        render_contact_box()


if __name__ == "__main__":
    main()
