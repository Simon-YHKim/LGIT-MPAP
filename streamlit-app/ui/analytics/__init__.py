"""
ui.analytics — Vitals self-hosted GA + Clarity-equivalent client tracker.

Drop one line at the top of every page (after apply_vitals_theme) to
turn on click / scroll / error / rage-click / dead-click capture and
register the pageview row used for time-on-page measurement:

    from ui.analytics import inject_tracker
    inject_tracker(page_name="Home", page_path="pages/0_Home.py")

Design notes (why this shape):
  * Closed-network friendly — the JS is bundled inline (no CDN).
  * Streamlit-only — uses streamlit.components.v1.declare_component
    pointing at a static `frontend/` dir that contains a single
    index.html with the tracker JS inlined. No npm / build step.
  * The component returns a JSON payload via Streamlit.setComponentValue;
    Python then bulk-inserts into Postgres on the next rerun.
  * Idempotent per-rerun — duplicate flushes are deduped via the JS
    `seq` counter cached in st.session_state.
  * Never throws — DB errors are swallowed so analytics failure can't
    break the dashboard.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from tracking import (
    log_pageview_start,
    log_event_batch,
    log_error_batch,
    log_pageview_duration,
)

_LOG = logging.getLogger("vitals.analytics")

_THIS_DIR = Path(__file__).resolve().parent
_FRONTEND_DIR = _THIS_DIR / "frontend"
_TRACKER_JS = (_THIS_DIR / "tracker.js").read_text(encoding="utf-8")
_INDEX_TEMPLATE = (_FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

# Bake the tracker source into a generated index.html. We keep the
# template separate (frontend/index.html) so the JS bridge stays
# readable and we only re-write the generated copy when tracker.js
# changes — the .build artifact is deterministic.
_BUILD_DIR = _FRONTEND_DIR / "_build"
_BUILD_DIR.mkdir(exist_ok=True)
_BUILD_INDEX = _BUILD_DIR / "index.html"


def _build_frontend_bundle() -> Path:
    """Materialize a single-file frontend bundle that declare_component
    can serve as a static dir. Re-built on import only if stale."""
    expected = _INDEX_TEMPLATE.replace("/* __TRACKER_JS_INLINE__ */", _TRACKER_JS)
    needs_write = True
    if _BUILD_INDEX.exists():
        try:
            if _BUILD_INDEX.read_text(encoding="utf-8") == expected:
                needs_write = False
        except Exception:
            needs_write = True
    if needs_write:
        _BUILD_INDEX.write_text(expected, encoding="utf-8")
    return _BUILD_DIR


_BUNDLE_DIR = _build_frontend_bundle()

# declare_component must be called at module top-level so Streamlit's
# component registry caches it. The "name" is internal — pick something
# that won't collide with other components in the app.
_vitals_analytics_component = components.declare_component(
    "vitals_analytics_tracker",
    path=str(_BUNDLE_DIR),
)


def _safe_call(fn, *args, **kwargs):
    """Run an analytics DB call but never raise into the page."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        _LOG.warning("analytics call failed: %s: %s", fn.__name__, e)
        return None


def _ensure_pageview(page_name: str, page_path: str) -> Optional[int]:
    """Open a new analytics_pageview row for this (session, page) pair.

    Keyed by page_path inside session_state so navigating between
    pages produces a fresh row, but Streamlit reruns of the SAME page
    reuse the existing row (no duplication).
    """
    user_id = st.session_state.get("user_email")
    if not user_id:
        return None

    key = f"_analytics_pageview_id::{page_path}"
    pv_id = st.session_state.get(key)
    if pv_id:
        return pv_id

    # Close the previous page's pageview from Python (best-effort).
    # Streamlit's SPA-style navigation often suppresses JS unload, so
    # we close the prior row whenever the user lands on a new page.
    prev_key = st.session_state.get("_analytics_last_pageview_key")
    if prev_key and prev_key != key:
        prev_pv = st.session_state.get(prev_key)
        prev_started = st.session_state.get(prev_key + "::started_at")
        if prev_pv and prev_started:
            dur = max(0, int(time.time() - prev_started))
            _safe_call(log_pageview_duration, prev_pv, dur)

    pv_id = _safe_call(
        log_pageview_start,
        user_id=user_id,
        dept=st.session_state.get("department"),
        page_path=page_path,
        page_name=page_name,
        session_id=st.session_state.get("session_id"),
    )
    if pv_id:
        st.session_state[key] = pv_id
        st.session_state[key + "::started_at"] = time.time()
        st.session_state["_analytics_last_pageview_key"] = key
    return pv_id


def _flush_payload(payload, page_path: str) -> None:
    """Persist the JS-side batch into Postgres."""
    if not isinstance(payload, dict):
        return

    seq = payload.get("seq")
    seq_state_key = f"_analytics_last_seq::{page_path}"
    last_seq = st.session_state.get(seq_state_key, 0)
    if seq is None or int(seq) <= int(last_seq):
        return
    st.session_state[seq_state_key] = int(seq)

    user_id = st.session_state.get("user_email")
    session_id = st.session_state.get("session_id")
    pageview_id = payload.get("pageview_id") or st.session_state.get(
        f"_analytics_pageview_id::{page_path}"
    )

    # Stamp authoritative fields server-side. We trust the JS for
    # element/position metadata, but identity comes from session_state.
    events = payload.get("events") or []
    for e in events:
        e["user_id"] = user_id
        e["session_id"] = session_id
        e["pageview_id"] = pageview_id
        e["page_path"] = page_path

    errors = payload.get("errors") or []
    for e in errors:
        e["user_id"] = user_id
        e["session_id"] = session_id
        e["pageview_id"] = pageview_id
        e["page_path"] = page_path

    if events:
        _safe_call(log_event_batch, events)
    if errors:
        _safe_call(log_error_batch, errors)


def inject_tracker(page_name: str, page_path: str) -> None:
    """Public entry point. Call once at the top of each page after
    require_login() and apply_vitals_theme()."""
    if not st.session_state.get("login"):
        return

    pv_id = _ensure_pageview(page_name, page_path)

    args = {
        "user_id":     st.session_state.get("user_email"),
        "dept":        st.session_state.get("department"),
        "session_id":  st.session_state.get("session_id"),
        "pageview_id": pv_id,
        "page_path":   page_path,
        "flush_ms":    4000,
        "flush_max":   25,
    }

    # `key` keeps the component instance stable across reruns of the
    # SAME page — without it, every rerun would re-mount the iframe and
    # re-attach event listeners (causing 2x, 3x event counts).
    payload = _vitals_analytics_component(
        key=f"vitals_analytics::{page_path}",
        default=None,
        **args,
    )

    if payload:
        _flush_payload(payload, page_path)


__all__ = ["inject_tracker"]
