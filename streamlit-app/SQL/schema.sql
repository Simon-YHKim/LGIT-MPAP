-- =========================================================
-- MTBA Streamlit Project - schema.sql (개발용 초기화 버전)
-- =========================================================

-- [중요]
-- 개발/초기 적재 단계에서는 스키마 전체를 재생성하는 편이 안전합니다.
-- 운영 데이터가 이미 있다면 이 방식 대신 비파괴 버전으로 바꿔야 합니다.

DROP SCHEMA IF EXISTS mtba CASCADE;
CREATE SCHEMA mtba;

SET search_path TO mtba, public;

-- =========================================================
-- 1. DIM TABLES
-- =========================================================

CREATE TABLE mtba.dim_plant (
    plant_id         BIGSERIAL PRIMARY KEY,
    plant_code       TEXT,
    plant_name       TEXT NOT NULL UNIQUE,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE mtba.dim_process (
    process_id       BIGSERIAL PRIMARY KEY,
    plant_id         BIGINT NOT NULL REFERENCES mtba.dim_plant(plant_id),
    process_code     TEXT,
    process_name     TEXT NOT NULL,
    process_short    TEXT,
    created_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE (plant_id, process_name)
);

CREATE TABLE mtba.dim_model (
    model_id         BIGSERIAL PRIMARY KEY,
    model_name       TEXT NOT NULL UNIQUE,
    model_group      TEXT,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE mtba.dim_equipment (
    equipment_id       BIGSERIAL PRIMARY KEY,
    plant_id           BIGINT NOT NULL REFERENCES mtba.dim_plant(plant_id),
    process_id         BIGINT REFERENCES mtba.dim_process(process_id),
    equipment_code     TEXT,
    equipment_name     TEXT NOT NULL,
    equipment_no       TEXT,
    segment_id         TEXT,
    segment_name       TEXT,
    created_at         TIMESTAMP DEFAULT NOW(),
    UNIQUE (plant_id, equipment_name)
);

CREATE TABLE mtba.dim_alarm (
    alarm_id             BIGSERIAL PRIMARY KEY,
    plant_code           TEXT,
    process_code         TEXT,
    process_name         TEXT,
    alarm_code           TEXT NOT NULL,
    alarm_name           TEXT NOT NULL,
    model_name           TEXT,
    importance_grade     TEXT,
    created_at           TIMESTAMP DEFAULT NOW()
);

-- 자연키 인덱스 (표현식은 UNIQUE CONSTRAINT가 아니라 UNIQUE INDEX로 생성)
CREATE UNIQUE INDEX ux_dim_alarm_nk
    ON mtba.dim_alarm (process_name, alarm_code, alarm_name, COALESCE(model_name, ''));

-- =========================================================
-- 2. MODEL FAMILY TABLES
-- 연계 모델 과거이력 확장용 (예: MEM -> Varo 등)
-- =========================================================

CREATE TABLE mtba.model_family (
    family_id         BIGSERIAL PRIMARY KEY,
    family_name       TEXT NOT NULL UNIQUE,
    description       TEXT,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE mtba.model_family_map (
    family_map_id     BIGSERIAL PRIMARY KEY,
    family_id         BIGINT NOT NULL REFERENCES mtba.model_family(family_id) ON DELETE CASCADE,
    model_id          BIGINT NOT NULL REFERENCES mtba.dim_model(model_id) ON DELETE CASCADE,
    valid_from        DATE,
    valid_to          DATE,
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX ux_model_family_map
    ON mtba.model_family_map (family_id, model_id, COALESCE(valid_from, DATE '1900-01-01'));

-- =========================================================
-- 3. FACT TABLES
-- =========================================================

-- 3-1. 설비/일자별 Runtime
CREATE TABLE mtba.fact_runtime_daily (
    runtime_daily_id       BIGSERIAL PRIMARY KEY,
    base_date              DATE NOT NULL,
    plant_id               BIGINT NOT NULL REFERENCES mtba.dim_plant(plant_id),
    process_id             BIGINT NOT NULL REFERENCES mtba.dim_process(process_id),
    equipment_id           BIGINT NOT NULL REFERENCES mtba.dim_equipment(equipment_id),
    runtime_minutes        NUMERIC(18,2) NOT NULL DEFAULT 0,
    source_file            TEXT,
    created_at             TIMESTAMP DEFAULT NOW()
);

-- 3-2. 설비/일자별 알람 총건수
CREATE TABLE mtba.fact_alarm_daily (
    alarm_daily_id         BIGSERIAL PRIMARY KEY,
    base_date              DATE NOT NULL,
    plant_id               BIGINT NOT NULL REFERENCES mtba.dim_plant(plant_id),
    process_id             BIGINT NOT NULL REFERENCES mtba.dim_process(process_id),
    equipment_id           BIGINT NOT NULL REFERENCES mtba.dim_equipment(equipment_id),
    alarm_count_total      INTEGER NOT NULL DEFAULT 0,
    source_file            TEXT,
    created_at             TIMESTAMP DEFAULT NOW()
);

-- 3-3. 설비/일자/알람/모델별 상세 알람
CREATE TABLE mtba.fact_alarm_detail_daily (
    alarm_detail_daily_id  BIGSERIAL PRIMARY KEY,
    base_date              DATE NOT NULL,
    plant_id               BIGINT NOT NULL REFERENCES mtba.dim_plant(plant_id),
    process_id             BIGINT NOT NULL REFERENCES mtba.dim_process(process_id),
    equipment_id           BIGINT NOT NULL REFERENCES mtba.dim_equipment(equipment_id),
    model_id               BIGINT REFERENCES mtba.dim_model(model_id),
    alarm_id               BIGINT REFERENCES mtba.dim_alarm(alarm_id),
    alarm_count            INTEGER NOT NULL DEFAULT 0,
    source_file            TEXT,
    created_at             TIMESTAMP DEFAULT NOW()
);

-- 3-4. 생산이력 (모델/설비/일자 기준)
CREATE TABLE mtba.fact_production_daily (
    production_daily_id    BIGSERIAL PRIMARY KEY,
    base_date              DATE NOT NULL,
    plant_id               BIGINT NOT NULL REFERENCES mtba.dim_plant(plant_id),
    process_id             BIGINT NOT NULL REFERENCES mtba.dim_process(process_id),
    equipment_id           BIGINT REFERENCES mtba.dim_equipment(equipment_id),
    model_id               BIGINT REFERENCES mtba.dim_model(model_id),
    input_qty              NUMERIC(18,2) DEFAULT 0,
    output_qty             NUMERIC(18,2) DEFAULT 0,
    defect_qty             NUMERIC(18,2) DEFAULT 0,
    source_file            TEXT,
    created_at             TIMESTAMP DEFAULT NOW()
);

-- =========================================================
-- 4. UI / 사용자 메모 / 이미지
-- =========================================================

CREATE TABLE mtba.report_note (
    note_id                BIGSERIAL PRIMARY KEY,
    panel_key              TEXT NOT NULL,
    model_id               BIGINT REFERENCES mtba.dim_model(model_id),
    process_id             BIGINT REFERENCES mtba.dim_process(process_id),
    selected_period_key    TEXT,
    note_text              TEXT,
    created_by             TEXT,
    updated_by             TEXT,
    created_at             TIMESTAMP DEFAULT NOW(),
    updated_at             TIMESTAMP DEFAULT NOW()
);

CREATE TABLE mtba.report_image (
    image_id               BIGSERIAL PRIMARY KEY,
    note_id                BIGINT REFERENCES mtba.report_note(note_id) ON DELETE CASCADE,
    file_name              TEXT NOT NULL,
    file_path              TEXT NOT NULL,
    mime_type              TEXT,
    file_size              BIGINT,
    width_px               INTEGER,
    height_px              INTEGER,
    created_at             TIMESTAMP DEFAULT NOW()
);

-- =========================================================
-- 5. INDEXES
-- =========================================================

CREATE INDEX idx_dim_process_plant_name
    ON mtba.dim_process (plant_id, process_name);

CREATE INDEX idx_dim_equipment_plant_name
    ON mtba.dim_equipment (plant_id, equipment_name);

CREATE INDEX idx_runtime_daily_date_eq
    ON mtba.fact_runtime_daily (base_date, equipment_id);

CREATE INDEX idx_runtime_daily_process
    ON mtba.fact_runtime_daily (process_id, base_date);

CREATE INDEX idx_alarm_daily_date_eq
    ON mtba.fact_alarm_daily (base_date, equipment_id);

CREATE INDEX idx_alarm_daily_process
    ON mtba.fact_alarm_daily (process_id, base_date);

CREATE INDEX idx_alarm_detail_date_eq_model
    ON mtba.fact_alarm_detail_daily (base_date, equipment_id, model_id);

CREATE INDEX idx_alarm_detail_alarm
    ON mtba.fact_alarm_detail_daily (alarm_id, base_date);

CREATE INDEX idx_alarm_detail_model
    ON mtba.fact_alarm_detail_daily (model_id, base_date);

CREATE INDEX idx_production_daily_date_proc_model
    ON mtba.fact_production_daily (base_date, process_id, model_id);

CREATE INDEX idx_production_daily_eq
    ON mtba.fact_production_daily (equipment_id, base_date);

CREATE INDEX idx_report_note_panel
    ON mtba.report_note (panel_key, created_at);

CREATE INDEX idx_report_image_note
    ON mtba.report_image (note_id);

-- =========================================================
-- 6. MATERIALIZED VIEW / VIEW
-- =========================================================

-- 6-1. 설비/일자 기준 대표 모델 매핑
-- 생산(output_qty) 최대 모델을 그 설비의 대표 모델로 선택
CREATE MATERIALIZED VIEW mtba.mv_equipment_model_daily AS
SELECT
    base_date,
    equipment_id,
    model_id
FROM (
    SELECT
        base_date,
        equipment_id,
        model_id,
        COALESCE(output_qty, 0) AS output_qty,
        ROW_NUMBER() OVER (
            PARTITION BY base_date, equipment_id
            ORDER BY COALESCE(output_qty, 0) DESC, model_id
        ) AS rn
    FROM mtba.fact_production_daily
    WHERE equipment_id IS NOT NULL
      AND model_id IS NOT NULL
) t
WHERE rn = 1;

CREATE INDEX idx_mv_equipment_model_daily
    ON mtba.mv_equipment_model_daily (base_date, equipment_id, model_id);

-- 6-2. 일자별 설비 MTBA View
CREATE VIEW mtba.v_mtba_daily_equipment AS
SELECT
    r.base_date,
    r.plant_id,
    r.process_id,
    r.equipment_id,
    em.model_id,
    r.runtime_minutes,
    COALESCE(a.alarm_count_total, 0) AS alarm_count_total,
    CASE
        WHEN COALESCE(a.alarm_count_total, 0) = 0 THEN NULL
        ELSE ROUND(r.runtime_minutes / a.alarm_count_total, 2)
    END AS mtba
FROM mtba.fact_runtime_daily r
LEFT JOIN mtba.fact_alarm_daily a
    ON r.base_date = a.base_date
   AND r.equipment_id = a.equipment_id
LEFT JOIN mtba.mv_equipment_model_daily em
    ON r.base_date = em.base_date
   AND r.equipment_id = em.equipment_id;

-- 6-3. 주차별 설비 MTBA
CREATE MATERIALIZED VIEW mtba.mv_mtba_weekly_equipment AS
SELECT
    DATE_TRUNC('week', base_date)::date AS week_start,
    plant_id,
    process_id,
    equipment_id,
    model_id,
    SUM(runtime_minutes) AS runtime_minutes,
    SUM(alarm_count_total) AS alarm_count_total,
    CASE
        WHEN SUM(alarm_count_total) = 0 THEN NULL
        ELSE ROUND(SUM(runtime_minutes) / SUM(alarm_count_total), 2)
    END AS mtba
FROM mtba.v_mtba_daily_equipment
GROUP BY 1,2,3,4,5;

CREATE INDEX idx_mv_mtba_weekly_equipment
    ON mtba.mv_mtba_weekly_equipment (week_start, model_id, process_id, equipment_id);

-- 6-4. 주차별 공정 통계 (Best / Worst / Avg / Stdev)
CREATE MATERIALIZED VIEW mtba.mv_mtba_weekly_process_stats AS
SELECT
    week_start,
    model_id,
    process_id,
    MAX(mtba) AS mtba_best,
    MIN(mtba) AS mtba_worst,
    ROUND(AVG(mtba)::numeric, 2) AS mtba_avg,
    ROUND(STDDEV_SAMP(mtba)::numeric, 2) AS mtba_stdev
FROM mtba.mv_mtba_weekly_equipment
WHERE mtba IS NOT NULL
GROUP BY 1,2,3;

CREATE INDEX idx_mv_mtba_weekly_process_stats
    ON mtba.mv_mtba_weekly_process_stats (week_start, model_id, process_id);

-- 6-5. 주차별 설비-알람 상세
CREATE MATERIALIZED VIEW mtba.mv_alarm_weekly_equipment_detail AS
SELECT
    DATE_TRUNC('week', fad.base_date)::date AS week_start,
    fad.equipment_id,
    fad.process_id,
    fad.model_id,
    fad.alarm_id,
    SUM(fad.alarm_count) AS alarm_count
FROM mtba.fact_alarm_detail_daily fad
GROUP BY 1,2,3,4,5;

CREATE INDEX idx_mv_alarm_weekly_equipment_detail
    ON mtba.mv_alarm_weekly_equipment_detail (week_start, equipment_id, model_id, alarm_id);

-- =========================================================
-- 7. 초기 샘플 공정 축약명 (선택)
-- =========================================================

-- 실제 데이터에 해당 공정명이 있을 때만 나중에 UPDATE로 세팅됩니다.
-- schema 단계에서는 생략해도 무방하므로 기본 구조만 제공합니다.

-- =========================================================
-- 8. 완료 메시지용 테스트 쿼리 (선택)
-- =========================================================
 SELECT 'schema created successfully' AS message;

 CREATE TABLE IF NOT EXISTS mtba.alarm_annotation (
    alarm_annotation_id  BIGSERIAL PRIMARY KEY,
    alarm_code           TEXT NOT NULL,
    alarm_name           TEXT NOT NULL,
    note_text            TEXT,
    image_path           TEXT,
    image_name           TEXT,
    mime_type            TEXT,
    file_size            BIGINT,
    created_at           TIMESTAMP DEFAULT NOW(),
    updated_at           TIMESTAMP DEFAULT NOW(),
    UNIQUE (alarm_code, alarm_name)
);

CREATE INDEX IF NOT EXISTS idx_alarm_annotation_key
    ON mtba.alarm_annotation (alarm_code, alarm_name);