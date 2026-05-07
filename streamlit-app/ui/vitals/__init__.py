"""
ui.vitals — Vitals 디자인 시스템 (LG Innotek 광학솔루션 사업부)

이 모듈은 우리의 디자인을 Streamlit 페이지에 일관되게 적용하기 위한
글로벌 진입점입니다. 모든 페이지는 다음 한 줄로 디자인을 활성화합니다:

    from ui.vitals import apply_vitals_theme
    apply_vitals_theme()

전역 스타일 (와인레드 팔레트, LG EI 폰트, Streamlit 사이드바 hide,
가로 nav, 카드 톤 등) 이 즉시 적용됩니다. 페이지 본문은 본 모듈의
components 함수들 (render_topnav, render_page_header, render_chat_panel
등) 을 호출하거나 직접 markdown/HTML 을 작성합니다.

폰트·로고는 ui/vitals/fonts/ ui/vitals/assets/ 에 정적 파일로 보관하고
런타임에 base64 로 인코딩해 CSS data: URL 로 주입 → 외부 CDN 의존 0,
완전 폐쇄망 호환.
"""
from .theme import apply_vitals_theme, get_current_theme, render_theme_toggle
from .preferences import (
    get_user_theme_pref,
    save_user_theme_pref,
    get_user_locale_pref,
    save_user_locale_pref,
)
from .components import (
    render_topnav,
    render_page_header,
    render_card,
    render_chat_panel,
    render_lang_switcher,
    LOGO_WHITE_DATA_URI,
    LOGO_GRAY_DATA_URI,
)

__all__ = [
    "apply_vitals_theme",
    "get_current_theme",
    "render_theme_toggle",
    "get_user_theme_pref",
    "save_user_theme_pref",
    "get_user_locale_pref",
    "save_user_locale_pref",
    "render_topnav",
    "render_page_header",
    "render_card",
    "render_chat_panel",
    "render_lang_switcher",
    "LOGO_WHITE_DATA_URI",
    "LOGO_GRAY_DATA_URI",
]
