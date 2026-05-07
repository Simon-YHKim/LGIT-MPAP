"""
ui.vitals.fonts — LG EI 폰트 base64 로더

폐쇄망에서도 외부 CDN 없이 LG EI 코퍼레이트 폰트가 모든 페이지에 일관되게
적용되도록, ui/vitals/fonts/*.woff2 정적 파일을 런타임에 base64 로
인코딩해 @font-face data: URL 로 주입한다.

- LG EI Text (300/400/600/700) — 본문/UI/라벨용
- LG EI Headline (700) — 디스플레이/H1 hero 용
- 누락 시 Pretendard / Malgun Gothic / system-ui 로 graceful fallback
"""
from __future__ import annotations
import base64
from functools import lru_cache
from pathlib import Path

_FONT_DIR = Path(__file__).parent / "fonts"

# (filename, family, weight)
_FONT_FILES = [
    ("lg-ei-text-300.woff2",     "LG EI Text",     300),
    ("lg-ei-text-400.woff2",     "LG EI Text",     400),
    ("lg-ei-text-600.woff2",     "LG EI Text",     600),
    ("lg-ei-text-700.woff2",     "LG EI Text",     700),
    ("lg-ei-headline-700.woff2", "LG EI Headline", 700),
]


@lru_cache(maxsize=1)
def font_face_block() -> str:
    """모든 LG EI 폰트의 @font-face 블록을 반환. 한 번 인코딩 후 캐시."""
    rules = []
    for filename, family, weight in _FONT_FILES:
        path = _FONT_DIR / filename
        if not path.exists():
            # 파일 없으면 건너뜀 (graceful — fallback 폰트가 적용됨)
            continue
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            f"@font-face{{"
            f"font-family:'{family}';"
            f"font-weight:{weight};"
            f"font-style:normal;"
            f"font-display:swap;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')"
            f"}}"
        )
    return "\n".join(rules)


# 본문/UI 폰트 스택 (CSS --font-body 변수로 사용)
FONT_BODY_STACK = (
    "'LG EI Text','LG Smart','Pretendard Variable',Pretendard,"
    "'Malgun Gothic',system-ui,sans-serif"
)

# 디스플레이/Hero 폰트 스택 (--font-display)
FONT_DISPLAY_STACK = (
    "'LG EI Headline','LG EI Text','Pretendard Variable',Pretendard,sans-serif"
)

# 모노 폰트 (KPI 숫자/표 셀)
FONT_MONO_STACK = "'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace"
