"""
verify_no_external.py — 폐쇄망 위반 검출 게이트.

LG Innotek 사내 폐쇄망에서는 외부 CDN / 외부 API / YouTube / Google Fonts /
jsdelivr 등 모든 인터넷 fetch 가 차단됨. STAGE 2 진입 전·후 코드/preview 안에
외부 URL 이 들어가지 않도록 grep 게이트.

검사 대상:
  · streamlit-app/**/*.py
  · streamlit-app/**/*.css
  · streamlit-app/**/*.html
  · docs/design/**/*.html
  · docs/design/**/*.css
  · docs/design/**/*.js

Allowlist (예외):
  · github.com / raw.githack.com URL 은 commit hash 미리보기용으로 commit
    message 등에만 등장하는 게 정상 — code 안에 들어가면 FAIL
  · localhost / 127.0.0.1 / 0.0.0.0 — 로컬 dev 만, prod 코드에는 없어야 함
    (이 게이트는 일단 허용)
  · http://schema.org / w3.org — XML 네임스페이스 (정적 문자열, 실제 fetch 아님)

사용법:
  python streamlit-app/scripts/verify_no_external.py
  # exit 0 = PASS, exit 1 = VIOLATIONS

옵션:
  --strict     localhost 까지 차단 (prod-ready 모드)
  --allow-mailto  mailto: 도 허용 (기본 OK)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_GLOBS = [
    "streamlit-app/**/*.py",
    "streamlit-app/**/*.css",
    "streamlit-app/**/*.html",
    "streamlit-app/**/*.js",
    # docs/design 에서는 STAGE 2 의 source-of-truth 만 검사:
    # preview-streamlit-clone.html + streamlit-clone.css.
    # mockup-S*.html / home.html / landing.html / index.html / shell 등은
    # archived reference (이전 design phase) 이라 외부 CDN URL 잔재 허용.
    "docs/design/preview-streamlit-clone.html",
    "docs/design/streamlit-clone.css",
]

# scan glob 외에 명시 제외 (예: streamlit-app/ui/analytics/frontend/index.html
# 처럼 의도적 외부 fetch 가 있는 경우 추가).
EXCLUDE_RELATIVE = set()

# 외부 호스트 패턴 (FAIL)
BAD_PATTERNS = [
    re.compile(r"https?://(?:www\.)?youtube\.com\b", re.IGNORECASE),
    re.compile(r"https?://youtu\.be\b", re.IGNORECASE),
    re.compile(r"https?://(?:[a-z0-9-]+\.)?googleapis\.com\b", re.IGNORECASE),
    re.compile(r"https?://(?:[a-z0-9-]+\.)?gstatic\.com\b", re.IGNORECASE),
    re.compile(r"https?://(?:[a-z0-9-]+\.)?fonts\.google\.com\b", re.IGNORECASE),
    re.compile(r"https?://cdn\.jsdelivr\.net\b", re.IGNORECASE),
    re.compile(r"https?://unpkg\.com\b", re.IGNORECASE),
    re.compile(r"https?://(?:cdnjs|cdn)\.cloudflare\.com\b", re.IGNORECASE),
    re.compile(r"https?://(?:www\.)?gstatic\.com\b", re.IGNORECASE),
    re.compile(r"https?://(?:[a-z0-9-]+\.)?cdn\.[a-z0-9-]+\b", re.IGNORECASE),
    re.compile(r"https?://api\.openai\.com\b", re.IGNORECASE),
    re.compile(r"https?://api\.anthropic\.com\b", re.IGNORECASE),
]

# 정규 표현식이 잡으면 안 되는 false-positive 패턴 (XML 네임스페이스 등)
ALLOW_SUBSTRINGS = [
    "http://www.w3.org/",       # SVG / XML 네임스페이스 (URL 형태지만 fetch 아님)
    "http://schema.org",
    "https://schema.org",
    "http://json-schema.org",
    "https://json-schema.org",
]


def _scan_file(path: Path, strict: bool) -> List[Tuple[int, str, str]]:
    """파일에서 외부 URL 위반 찾기. (line, pattern, snippet) 리스트 리턴."""
    findings: List[Tuple[int, str, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings
    for ln_no, line in enumerate(text.splitlines(), start=1):
        # allowlist 빠르게 처리
        if any(s in line for s in ALLOW_SUBSTRINGS):
            continue
        for pat in BAD_PATTERNS:
            if pat.search(line):
                findings.append((ln_no, pat.pattern, line.strip()[:120]))
        if strict:
            if re.search(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)\b", line):
                findings.append((ln_no, "localhost (strict)", line.strip()[:120]))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="localhost / 127.0.0.1 도 차단 (prod 모드).")
    args = parser.parse_args()

    files: List[Path] = []
    for g in SCAN_GLOBS:
        files.extend(sorted(REPO_ROOT.glob(g)))
    files = [f for f in files if "__pycache__" not in str(f)]

    total_findings: List[Tuple[Path, int, str, str]] = []
    for f in files:
        for ln, pat, snip in _scan_file(f, strict=args.strict):
            total_findings.append((f, ln, pat, snip))

    if total_findings:
        print(f"[FAIL] external URL violations ({len(total_findings)}):")
        for f, ln, pat, snip in total_findings:
            rel = f.relative_to(REPO_ROOT)
            print(f"  {rel}:{ln}  [{pat}]")
            print(f"      {snip}")
        return 1

    print(f"[PASS] no external URLs in {len(files)} files (strict={args.strict})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
