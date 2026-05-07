#!/usr/bin/env python3
"""Verify dark-mode tokens are present in the injected Vitals CSS.

Standalone — runs without a real Streamlit/SQLAlchemy install by stubbing
the imports the modules need at load time. Useful as a CI smoke gate.

Usage:
    python3 streamlit-app/scripts/verify_dark_mode_tokens.py
"""
from __future__ import annotations
import inspect
import sys
import types
from pathlib import Path


def _install_stubs() -> None:
    fake_sa = types.ModuleType("sqlalchemy")
    fake_sa.text = lambda x: x  # type: ignore
    sys.modules.setdefault("sqlalchemy", fake_sa)

    fake_st = types.ModuleType("streamlit")
    fake_st.session_state = {}  # type: ignore
    fake_st.markdown = lambda *a, **k: None  # type: ignore
    fake_st.button = lambda *a, **k: False  # type: ignore
    fake_st.sidebar = fake_st  # type: ignore
    fake_st.rerun = lambda: None  # type: ignore

    class _Ctx:
        page_script_hash = "x"

    fake_runtime = types.ModuleType("streamlit.runtime")
    fake_sr = types.ModuleType("streamlit.runtime.scriptrunner")
    fake_sr.get_script_run_ctx = lambda: _Ctx()  # type: ignore
    sys.modules.setdefault("streamlit", fake_st)
    sys.modules.setdefault("streamlit.runtime", fake_runtime)
    sys.modules.setdefault("streamlit.runtime.scriptrunner", fake_sr)

    fake_db = types.ModuleType("db")
    fake_db.get_engine = lambda: None  # type: ignore
    sys.modules.setdefault("db", fake_db)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    _install_stubs()

    from ui.vitals.theme import (  # noqa: E402
        _build_css,
        apply_vitals_theme,
        get_current_theme,
        render_theme_toggle,
    )

    css = _build_css()

    dark_tokens = {
        "--page-bg":          "#0E1117",
        "--card-bg":          "#161B22",
        "--soft":             "#1A1F2A",
        "--border":           "#2A2F3A",
        "--border-strong":    "#3A4051",
        "--ink-body":         "#E5E7EB",
        "--ink-muted":        "#9CA3AF",
        "--ink-subtle":       "#6B7280",
        "--status-good":      "#2EA85C",
        "--status-warn":      "#D69E2E",
        "--status-bad":       "#E5495A",
        "--status-good-tint": "#0F2418",
        "--status-warn-tint": "#2A2210",
        "--status-bad-tint":  "#2E1318",
        "--primary-tint":     "#2A1218",
    }

    failures: list[str] = []

    if '[data-theme="dark"]' not in css:
        failures.append('Missing [data-theme="dark"] selector')
    if ".vitals-dark" not in css:
        failures.append("Missing .vitals-dark fallback selector")
    if ":root" not in css:
        failures.append("Missing :root for light defaults")

    for tok, val in dark_tokens.items():
        if val.upper() not in css.upper():
            failures.append(f"Missing dark token {tok} -> {val}")

    for v in ["#A50034", "#F7F8FA", "#FFFFFF", "#1F2430", "#1F8B4C", "#B57F1B", "#B23A48"]:
        if v not in css:
            failures.append(f"Missing light token {v}")

    sig = inspect.signature(apply_vitals_theme)
    for p in sig.parameters.values():
        if p.default is inspect.Parameter.empty:
            failures.append(f"apply_vitals_theme param {p.name} has no default — backward compat break")

    # Backward-compat smoke: callable with no args
    apply_vitals_theme()
    if get_current_theme() != "light":
        failures.append("Default theme should be 'light'")
    apply_vitals_theme("dark")
    if get_current_theme() != "dark":
        failures.append("Setting 'dark' did not stick")
    apply_vitals_theme("light")
    if get_current_theme() != "light":
        failures.append("Setting 'light' did not stick")

    # render_theme_toggle is callable
    try:
        render_theme_toggle()
    except Exception as e:  # noqa: BLE001
        failures.append(f"render_theme_toggle raised: {e}")

    if failures:
        print("FAIL")
        for f in failures:
            print("  -", f)
        return 1

    print("PASS — dark tokens present, light intact, API callable with no args")
    print(f"CSS length: {len(css)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
