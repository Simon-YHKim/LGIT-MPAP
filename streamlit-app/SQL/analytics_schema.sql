-- =========================================================
-- Vitals Analytics — self-hosted GA + Clarity-equivalent schema
-- =========================================================
--
-- This file is ADDITIVE. It does NOT touch the existing mtba schema or
-- the legacy public.user_sessions / public.page_view_logs tables.
--
-- All new tables live under the new `analytics` schema so they can be
-- granted/audited independently and dropped without affecting MTBA data.
--
-- Idempotent: every CREATE uses IF NOT EXISTS. Safe to re-run.
-- =========================================================

CREATE SCHEMA IF NOT EXISTS analytics;

SET search_path TO analytics, public;

-- =========================================================
-- 1. Pageview — one row per page navigation. Server creates the row on
--    page load (log_pageview_start), client updates duration on unload
--    (log_pageview_duration) so we can compute time-on-page.
--
--    NOTE: legacy public.page_view_logs is left untouched — that table
--    keeps the per-rerun "viewed_at" stream. analytics_pageview is the
--    deduplicated navigation-level table with duration.
-- =========================================================
CREATE TABLE IF NOT EXISTS analytics.analytics_pageview (
    pageview_id      BIGSERIAL PRIMARY KEY,
    session_id       BIGINT,
    user_id          TEXT,            -- email
    dept             TEXT,
    page_path        TEXT NOT NULL,
    page_name        TEXT,
    referrer         TEXT,
    user_agent       TEXT,
    viewport_w       INTEGER,
    viewport_h       INTEGER,
    started_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at         TIMESTAMP,
    duration_sec     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_pv_path_started
    ON analytics.analytics_pageview (page_path, started_at);
CREATE INDEX IF NOT EXISTS idx_pv_user_started
    ON analytics.analytics_pageview (user_id, started_at);
CREATE INDEX IF NOT EXISTS idx_pv_session
    ON analytics.analytics_pageview (session_id);

-- =========================================================
-- 2. Event — generic interaction stream (click, submit, scroll, custom,
--    rage_click, dead_click). Position is in CSS pixels relative to the
--    document; we also keep the viewport for normalization at render time.
-- =========================================================
CREATE TABLE IF NOT EXISTS analytics.analytics_event (
    event_id         BIGSERIAL PRIMARY KEY,
    pageview_id      BIGINT,          -- FK soft-link, NULL allowed for early events
    session_id       BIGINT,
    user_id          TEXT,
    page_path        TEXT NOT NULL,
    event_type       TEXT NOT NULL,   -- 'click' | 'submit' | 'scroll' | 'rage_click' | 'dead_click' | 'custom'
    element_id       TEXT,
    element_label    TEXT,
    position_x       INTEGER,
    position_y       INTEGER,
    viewport_w       INTEGER,
    viewport_h       INTEGER,
    scroll_depth_pct INTEGER,         -- 0-100, populated for 'scroll' events
    extra            JSONB,           -- forward-compat blob
    ts               TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ev_path_ts
    ON analytics.analytics_event (page_path, ts);
CREATE INDEX IF NOT EXISTS idx_ev_user_ts
    ON analytics.analytics_event (user_id, ts);
CREATE INDEX IF NOT EXISTS idx_ev_type_ts
    ON analytics.analytics_event (event_type, ts);

-- =========================================================
-- 3. Error — JS errors captured by window.onerror.
-- =========================================================
CREATE TABLE IF NOT EXISTS analytics.analytics_error (
    error_id         BIGSERIAL PRIMARY KEY,
    pageview_id      BIGINT,
    session_id       BIGINT,
    user_id          TEXT,
    page_path        TEXT NOT NULL,
    message          TEXT,
    stack            TEXT,
    source           TEXT,
    line_no          INTEGER,
    col_no           INTEGER,
    user_agent       TEXT,
    ts               TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_err_path_ts
    ON analytics.analytics_error (page_path, ts);
CREATE INDEX IF NOT EXISTS idx_err_user_ts
    ON analytics.analytics_error (user_id, ts);
CREATE INDEX IF NOT EXISTS idx_err_message
    ON analytics.analytics_error ((LEFT(COALESCE(message, ''), 200)));

-- =========================================================
-- 4. Heatmap aggregate — pre-binned 50x50 grid per page per day.
--    Populated by aggregate_heatmap_daily() so the dashboard can render
--    instantly without scanning analytics_event.
-- =========================================================
CREATE TABLE IF NOT EXISTS analytics.analytics_click_heatmap_agg (
    agg_id           BIGSERIAL PRIMARY KEY,
    page_path        TEXT NOT NULL,
    grid_x           INTEGER NOT NULL,    -- floor(position_x / 50)
    grid_y           INTEGER NOT NULL,    -- floor(position_y / 50)
    click_count      INTEGER NOT NULL DEFAULT 0,
    rage_click_count INTEGER NOT NULL DEFAULT 0,
    dead_click_count INTEGER NOT NULL DEFAULT 0,
    bucket_date      DATE NOT NULL,
    UNIQUE (page_path, bucket_date, grid_x, grid_y)
);

CREATE INDEX IF NOT EXISTS idx_heat_page_date
    ON analytics.analytics_click_heatmap_agg (page_path, bucket_date);
CREATE INDEX IF NOT EXISTS idx_heat_date
    ON analytics.analytics_click_heatmap_agg (bucket_date);

-- =========================================================
-- 5. Sanity ping
-- =========================================================
SELECT 'analytics schema created/verified' AS message;
