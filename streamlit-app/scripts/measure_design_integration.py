#!/usr/bin/env python3
"""Vitals 디자인 통합도 측정기 — 정적 분석.

각 페이지 (.py) 의 CSS/markdown 텍스트에서 6개 차원으로 점수화:
  1. Token usage      (30) — Vitals 팔레트 hex 비율
  2. Font compliance  (20) — Malgun/Arial !important 부재
  3. Theme injection  (10) — apply_vitals_theme() 호출
  4. Hero/Page head   (10) — vit-page-head / page-hero / 메인 타이틀 존재
  5. Component palette(15) — card-bg/border/soft 토큰 사용
  6. Status semantics (15) — good/warn/bad 색이 Vitals 시맨틱

사용법:
  python3 streamlit-app/scripts/measure_design_integration.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PAGES_DIR = REPO / "streamlit-app" / "pages"
LOGIN = REPO / "streamlit-app" / "login.py"

# Vitals 정식 팔레트 (대소문자 무시) — Light + Dark 양쪽 토큰
VITALS_HEX = {
    # ----- Light theme -----
    "A50034", "7E0027", "F8E5EC",         # primary / dark / tint
    "F7F8FA", "FFFFFF", "F1F3F5", "E5E7EB", "FAFAFA",  # surfaces
    "CBD0D6",                              # border-strong
    "1F2430", "6B7280", "9CA3AF",         # ink
    "1F8B4C", "B57F1B", "B23A48",         # status base
    "E6F4EA", "FAF1DD", "FDECEF",         # status tints
    "111111",                              # neutral terminal
    # ----- Dark theme overrides -----
    "0E1117", "0A0C10",                   # page-bg dark
    "161B22", "11161E",                   # card-bg dark
    "1A1F2A",                              # soft dark
    "2A2F3A", "3A4051",                   # border / border-strong dark
    "2EA85C", "D69E2E", "E5495A",         # status base dark
    "0F2418", "2A2210", "2E1318",         # status tints dark
    "2A1218",                              # primary-tint dark
}
VITALS_HEX = {h.upper() for h in VITALS_HEX}

HEX_RE = re.compile(r"#([0-9a-fA-F]{6})\b")
HEX_3_RE = re.compile(r"#([0-9a-fA-F]{3})\b")


def to6(h: str) -> str:
    return (h * 2 if len(h) == 3 else h).upper()


def score_tokens(src: str) -> tuple[float, dict]:
    hexes = [to6(m) for m in HEX_RE.findall(src) + HEX_3_RE.findall(src)]
    if not hexes:
        return 30.0, {"total": 0, "vitals": 0, "off": 0, "off_samples": []}
    total = len(hexes)
    vitals = sum(1 for h in hexes if h in VITALS_HEX)
    off = total - vitals
    rate = vitals / total
    off_samples = sorted(set(h for h in hexes if h not in VITALS_HEX))[:8]
    return round(rate * 30, 1), {"total": total, "vitals": vitals, "off": off, "off_samples": off_samples}


def score_font(src: str) -> tuple[float, dict]:
    bad_patterns = [
        r"font-family:\s*['\"]?Malgun.*!important",
        r"font-family:\s*['\"]?Inter['\"]?",
        r"font-family:\s*['\"]?Arial['\"]?\s*[,!]",
    ]
    hits = []
    for pat in bad_patterns:
        for m in re.finditer(pat, src, flags=re.IGNORECASE):
            hits.append(m.group(0)[:60])
    has_lg_ei = "LG EI" in src or "var(--font-" in src
    pts = 20.0
    pts -= min(len(hits) * 5, 20)
    if not has_lg_ei:
        pts -= 5
    return max(pts, 0), {"violations": hits[:5], "has_lg_ei_or_var": has_lg_ei}


def score_theme_injection(src: str) -> tuple[float, dict]:
    has_apply = bool(re.search(r"\bapply_vitals_theme\s*\(", src))
    has_local = bool(re.search(r"\binject_(?:vitals_theme|css)\s*\(", src))
    pts = 10.0 if has_apply else (5.0 if has_local else 0.0)
    return pts, {"apply_vitals_theme": has_apply, "local_inject": has_local}


def score_hero(src: str) -> tuple[float, dict]:
    patterns = [
        r"vit-page-head",
        r"page-hero",
        r"vit-hero",
        r"main-title",
        r"section-heading",
        r"page-banner",
        r'<h1\b',
    ]
    hits = [p for p in patterns if re.search(p, src)]
    pts = 10.0 if hits else 0.0
    return pts, {"matched": hits}


def score_component_palette(src: str) -> tuple[float, dict]:
    tokens = [
        r"--card-bg|var\(--card",
        r"--border\b|var\(--border",
        r"--soft\b|var\(--soft",
        r"--ink-body|var\(--ink",
        r"--page-bg|var\(--page",
    ]
    hits = sum(1 for p in tokens if re.search(p, src))
    pts = round((hits / len(tokens)) * 15, 1)
    return pts, {"tokens_used": hits, "of": len(tokens)}


def score_status_semantics(src: str) -> tuple[float, dict]:
    good_re = r"#1F8B4C|--status-good|status-good"
    warn_re = r"#B57F1B|--status-warn|status-warn"
    bad_re  = r"#B23A48|--status-bad|status-bad"
    has_good = bool(re.search(good_re, src, flags=re.IGNORECASE))
    has_warn = bool(re.search(warn_re, src, flags=re.IGNORECASE))
    has_bad  = bool(re.search(bad_re,  src, flags=re.IGNORECASE))
    legacy = bool(re.search(r"#16a34a|#dc2626|#ef4444|#10b981|#facc15|#22c55e", src, flags=re.IGNORECASE))
    n = sum([has_good, has_warn, has_bad])
    pts = round((n / 3) * 15, 1)
    if legacy:
        pts = max(pts - 5, 0)
    return pts, {"good": has_good, "warn": has_warn, "bad": has_bad, "legacy_status_color": legacy}


def measure_file(path: Path) -> dict:
    src = path.read_text(encoding="utf-8", errors="replace")
    # 페이지 본체 + 강결합 UI 모듈 (CSS/layout 가 분리된 경우)
    if path.name == "login.py":
        login_ui = REPO / "streamlit-app" / "ui" / "login_ui"
        if login_ui.is_dir():
            for f in sorted(login_ui.glob("*.py")):
                src += "\n" + f.read_text(encoding="utf-8", errors="replace")
    s1, d1 = score_tokens(src)
    s2, d2 = score_font(src)
    s3, d3 = score_theme_injection(src)
    s4, d4 = score_hero(src)
    s5, d5 = score_component_palette(src)
    s6, d6 = score_status_semantics(src)
    total = round(s1 + s2 + s3 + s4 + s5 + s6, 1)
    return {
        "file": str(path.relative_to(REPO)),
        "score": total,
        "max": 100,
        "breakdown": {
            "tokens(30)":  {"pts": s1, **d1},
            "font(20)":    {"pts": s2, **d2},
            "theme(10)":   {"pts": s3, **d3},
            "hero(10)":    {"pts": s4, **d4},
            "components(15)": {"pts": s5, **d5},
            "status(15)":  {"pts": s6, **d6},
        },
    }


def main():
    files = sorted(PAGES_DIR.glob("*.py"))
    if LOGIN.exists():
        files = [LOGIN] + files
    results = [measure_file(f) for f in files]
    results.sort(key=lambda r: r["score"])
    print(f"{'PAGE':<48} {'SCORE':>6}  TOKENS FONT THEME HERO COMP STATUS")
    print("-" * 90)
    for r in results:
        b = r["breakdown"]
        print(f"{r['file']:<48} {r['score']:>5.1f}/100  "
              f"{b['tokens(30)']['pts']:>4}/30 "
              f"{b['font(20)']['pts']:>4}/20 "
              f"{b['theme(10)']['pts']:>4}/10 "
              f"{b['hero(10)']['pts']:>4}/10 "
              f"{b['components(15)']['pts']:>4}/15 "
              f"{b['status(15)']['pts']:>4}/15")
    avg = sum(r["score"] for r in results) / len(results)
    print("-" * 90)
    print(f"{'AVERAGE':<48} {avg:>5.1f}/100")
    out = REPO / "streamlit-app" / "docs" / "design_integration_score.json"
    out.write_text(json.dumps({"average": round(avg, 1), "pages": results}, indent=2, ensure_ascii=False))
    print(f"\n→ {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
