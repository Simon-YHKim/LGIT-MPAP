# -*- coding: utf-8 -*-
from __future__ import annotations

ALLOWED_MODELS = ["R53A", "R53B", "R50", "R63A", "R63B", "R70"]
MASTER_MV = "mtba.mv_detail_page_daily_master"
FALLBACK_MV = "mtba.mv_detail_page_daily"
DIM_EQUIPMENT = "mtba.dim_equipment"
COMMENT_TABLE = "mtba.alarm_comment_history"

PRIMARY = "#6D1028"
PRIMARY_2 = "#8B1E3F"
BG = "#FAF6F8"
CARD = "#FFFDFE"
ROSE = "#F7E7EC"
MIST = "#F6F1F4"
BORDER = "#E8D8DE"
TEXT = "#3D2430"
SUB = "#7A5A67"
PASTEL_RED = "#F6D9DF"
PASTEL_RED_STRONG = "#F2C9D1"
PASTEL_YELLOW = "#FFF0C7"
PASTEL_GREEN = "#E4F2E0"

PAGE_STYLE = f"""
<style>
:root {{
    --primary: {PRIMARY};
    --primary-2: {PRIMARY_2};
    --bg: {BG};
    --card: {CARD};
    --rose: {ROSE};
    --mist: {MIST};
    --border: {BORDER};
    --text: {TEXT};
    --sub: {SUB};
}}
.block-container {{ padding-top: 1.1rem; padding-bottom: 2.0rem; }}
.main {{ background: linear-gradient(180deg, #FFFDFE 0%, {BG} 100%); }}
.soft-card {{
    background: rgba(255,255,255,0.92);
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 14px 18px;
    box-shadow: 0 8px 24px rgba(109,16,40,0.06);
}}
.section-title {{
    color: {PRIMARY};
    font-size: 1.18rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}}
.panel-title {{
    color: {PRIMARY};
    font-size: 1.08rem;
    font-weight: 800;
    margin: 0.2rem 0 0.65rem 0;
}}
.helper-text {{ color: {SUB}; font-size: 0.92rem; }}
.legend-wrap {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:0.35rem; margin-bottom:0.35rem; }}
.legend-chip {{
    border-radius: 999px;
    padding: 6px 12px;
    border: 1px solid {BORDER};
    font-size: 0.82rem;
    background: white;
}}
.legend-chip.red {{ background: {PASTEL_RED}; }}
.legend-chip.yellow {{ background: {PASTEL_YELLOW}; }}
.legend-chip.green {{ background: {PASTEL_GREEN}; }}
.legend-chip.prod {{ background: {PASTEL_RED_STRONG}; }}
.popup-meta {{
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 10px 14px;
    background: #fffdfd;
    margin-bottom: 0.75rem;
}}
.popup-title {{ color:{PRIMARY}; font-weight:800; font-size:1.05rem; margin-bottom:0.25rem; }}
.popup-sub {{ color:{SUB}; font-size:0.9rem; line-height:1.5; }}
.small-note {{ color:{SUB}; font-size:0.82rem; }}
</style>
"""
