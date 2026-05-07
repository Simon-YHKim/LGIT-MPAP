-- ====================================================================
-- Performance indexes for MTBA Detail View / Comment History
-- ====================================================================
-- 적용 방법:
--   psql -h <host> -U <user> -d <database> -f SQL/perf_indexes.sql
--
-- 영향 범위:
--   - mtba.alarm_comment_history 의 댓글 조회 (load_alarm_comment_history)
--     → 현재 ORDER BY created_at DESC 가 인덱스 leading column 아니라서
--       full scan + sort. 아래 인덱스로 index-only seek 가능.
--   - 운영 중 적용 가능 (CONCURRENTLY 옵션 — 락 최소화).
-- ====================================================================

-- 1) Standard popup_scope 용 (equipment_id 기준)
-- WHERE popup_scope=:s AND equipment_id=:eid AND base_date=:d AND alarm_name=:a
-- ORDER BY created_at DESC, id DESC
--
-- NOTE: Partial index 의 predicate 는 query WHERE 절과 logically equivalent
-- 해야 PG planner 가 사용함. 쿼리는 `popup_scope = :popup_scope` 단일 매칭이므로
-- predicate 도 OR 형태로 풀어 써야 'standard' 와 'default' 양쪽이 인덱스 적중.
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_alarm_comment_hist_standard_lookup
    ON mtba.alarm_comment_history
        (popup_scope, equipment_id, base_date, alarm_name, created_at DESC, id DESC)
    WHERE popup_scope = 'standard' OR popup_scope = 'default';

-- 2) FOL popup_scope 용 (segment_name + process_name 기준)
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_alarm_comment_hist_fol_lookup
    ON mtba.alarm_comment_history
        (popup_scope, segment_name, process_name, base_date, alarm_name, created_at DESC, id DESC)
    WHERE popup_scope = 'fol';

-- 3) (옵션) alarm_code 가 있는 경우 빠른 필터링용 부분 인덱스
CREATE INDEX CONCURRENTLY IF NOT EXISTS
    idx_alarm_comment_hist_code
    ON mtba.alarm_comment_history (alarm_code, created_at DESC)
    WHERE alarm_code IS NOT NULL;

-- ====================================================================
-- Verification
-- ====================================================================
-- 적용 후 다음으로 검증 (예상: Index Scan / Index Only Scan):
--
--   EXPLAIN ANALYZE
--   SELECT id, created_at, created_by, alarm_code, alarm_name, comment_text
--   FROM mtba.alarm_comment_history
--   WHERE popup_scope = 'standard'
--     AND equipment_id = 1003
--     AND base_date = CURRENT_DATE
--     AND alarm_name = 'Cell Defect'
--   ORDER BY created_at DESC, id DESC
--   LIMIT 100;
--
-- ====================================================================
-- 통계 갱신 (선택)
-- ====================================================================
ANALYZE mtba.alarm_comment_history;

-- 끝.
