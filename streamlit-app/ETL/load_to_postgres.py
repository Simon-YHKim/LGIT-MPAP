
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, Optional
from uuid import uuid4

import pandas as pd
from sqlalchemy import create_engine, text

# ---------------------------------------------------------
# toml loader
# ---------------------------------------------------------
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore


# =========================================================
# 0. CONFIG
# =========================================================
BASE_DIR = Path(__file__).resolve().parents[1]
SECRETS_PATH = BASE_DIR / ".streamlit" / "secrets.toml"
ARCHIVE_ROOT = BASE_DIR / "Data_ori"

DEFAULT_LOOKBACK_DAYS = 1


def load_config() -> Dict[str, str]:
    secrets = {}
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)

    def get_value(key: str, default: str) -> str:
        return os.getenv(key, str(secrets.get(key, default)))

    db_url = os.getenv("DB_URL") or secrets.get("DB_URL")
    if not db_url:
        raise RuntimeError(
            "DB_URL not configured. Set DB_URL env or add it to "
            ".streamlit/secrets.toml. Hardcoded fallback removed."
        )

    return {
        "DB_URL": db_url,
        "RUNTIME_XLSX": get_value("RUNTIME_XLSX", str(BASE_DIR / "Data" / "Runtime_summary_by_date.xlsx")),
        "ALARM_DAILY_XLSX": get_value("ALARM_DAILY_XLSX", str(BASE_DIR / "Data" / "alarm_count_filter_sum.xlsx")),
        "ALARM_DETAIL_XLSX": get_value("ALARM_DETAIL_XLSX", str(BASE_DIR / "Data" / "alarm_count_filter.xlsx")),
        "ALARM_MASTER_XLSX": get_value("ALARM_MASTER_XLSX", str(BASE_DIR / "Data" / "Master_Result.xlsx")),
        "PRODUCTION_CSV": get_value("PRODUCTION_CSV", str(BASE_DIR / "Data" / "MTBA_Production.csv")),
        "LOOKBACK_DAYS": get_value("LOOKBACK_DAYS", str(DEFAULT_LOOKBACK_DAYS)),
    }


CFG = load_config()
DB_URL = CFG["DB_URL"]
RUNTIME_XLSX = CFG["RUNTIME_XLSX"]
ALARM_DAILY_XLSX = CFG["ALARM_DAILY_XLSX"]
ALARM_DETAIL_XLSX = CFG["ALARM_DETAIL_XLSX"]
ALARM_MASTER_XLSX = CFG["ALARM_MASTER_XLSX"]
PRODUCTION_CSV = CFG["PRODUCTION_CSV"]
LOOKBACK_DAYS = int(CFG["LOOKBACK_DAYS"])

engine = create_engine(DB_URL, pool_pre_ping=True, future=True)


# =========================================================
# 1. COMMON UTILS
# =========================================================
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().replace("\n", "").replace("\r", "") for c in df.columns]
    return df


def parse_date_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    return pd.to_datetime(s, errors="coerce", format="mixed").dt.date


def clean_numeric(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA, "N/A": pd.NA, "NA": pd.NA, "null": pd.NA, "NULL": pd.NA, "-": pd.NA})
    s = s.str.replace(",", "", regex=False)
    s = s.str.replace(r"^\((.+)\)$", r"-\1", regex=True)
    s = s.str.replace(r"[^0-9\.\-]", "", regex=True)
    s = s.replace({"": pd.NA, "-": pd.NA, ".": pd.NA, "-.": pd.NA})
    return pd.to_numeric(s, errors="coerce")


def normalize_text_key(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    return s


def normalize_alarm_code(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    return s


def to_join_key(s: pd.Series, null_token: str = "__NULL__") -> pd.Series:
    s = s.astype("string").str.strip()
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    return s.fillna(null_token)


def extract_equipment_no(equipment_name: Optional[str]) -> Optional[str]:
    if equipment_name is None or pd.isna(equipment_name):
        return None
    m = re.search(r"#\s*([0-9]+)", str(equipment_name))
    return m.group(1) if m else None


def print_connection_info() -> None:
    with engine.connect() as conn:
        db_name = conn.execute(text("SELECT current_database()")).scalar()
        user_name = conn.execute(text("SELECT current_user")).scalar()
        print(f"[INFO] connected DB = {db_name}, user = {user_name}")


def validate_file_exists(path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"파일이 존재하지 않습니다: {path}")


def validate_required_columns(df: pd.DataFrame, required_cols: Iterable[str], context: str = "") -> None:
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"[{context}] 필수 컬럼 누락: {missing}\n현재 컬럼: {list(df.columns)}")


# =========================================================
# 2. ARCHIVE HELPERS
# =========================================================
def build_archive_target_path(src_path: Path, executed_at: datetime) -> Path:
    year_str = executed_at.strftime("%Y")
    month_str = executed_at.strftime("%m")
    day_str = executed_at.strftime("%d")
    stamp = executed_at.strftime("%Y%m%d_%H")

    target_dir = ARCHIVE_ROOT / year_str / month_str / day_str
    target_dir.mkdir(parents=True, exist_ok=True)

    stem = src_path.stem
    suffix = src_path.suffix
    candidate = target_dir / f"{stem}_{stamp}{suffix}"
    if not candidate.exists():
        return candidate

    seq = 1
    while True:
        candidate = target_dir / f"{stem}_{stamp}_{seq:02d}{suffix}"
        if not candidate.exists():
            return candidate
        seq += 1


def move_processed_files(folder_paths: list[str], executed_at: datetime) -> list[str]:
    messages: list[str] = []
    allowed_exts = {".csv", ".xlsx", ".xls"}
    for folder in folder_paths:
        folder_path = Path(folder)
        if not folder_path.exists():
            msg = f"[WARN] 아카이브 이동 생략 (폴더 없음): {folder_path}"
            print(msg)
            messages.append(msg)
            continue
        if not folder_path.is_dir():
            msg = f"[WARN] 아카이브 이동 생략 (폴더 아님): {folder_path}"
            print(msg)
            messages.append(msg)
            continue
        files = sorted([p for p in folder_path.iterdir() if p.is_file()])
        if not files:
            msg = f"[INFO] 이동할 파일 없음: {folder_path}"
            print(msg)
            messages.append(msg)
            continue
        for src in files:
            if src.name.startswith("~$"):
                continue
            if src.suffix.lower() not in allowed_exts:
                continue
            target = build_archive_target_path(src, executed_at)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))
            msg = f"[INFO] 파일 이동 완료: {src} -> {target}"
            print(msg)
            messages.append(msg)
    return messages


# =========================================================
# 3. DB CHECK / AUX / INDEX
# =========================================================
def schema_exists(conn, schema_name: str) -> bool:
    sql = text("""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.schemata
            WHERE schema_name = :schema_name
        )
    """)
    return bool(conn.execute(sql, {"schema_name": schema_name}).scalar())


def table_exists(conn, full_table_name: str) -> bool:
    return conn.execute(text("SELECT to_regclass(:table_name)"), {"table_name": full_table_name}).scalar() is not None


def ensure_aux_tables(conn) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mtba.report_note (
            note_id BIGSERIAL PRIMARY KEY,
            panel_key TEXT NOT NULL,
            model_id BIGINT,
            process_id BIGINT,
            selected_period_key TEXT,
            note_text TEXT,
            created_by TEXT,
            updated_by TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mtba.report_image (
            image_id BIGSERIAL PRIMARY KEY,
            note_id BIGINT REFERENCES mtba.report_note(note_id) ON DELETE CASCADE,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            mime_type TEXT,
            file_size BIGINT,
            width_px INTEGER,
            height_px INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mtba.alarm_annotation (
            alarm_annotation_id BIGSERIAL PRIMARY KEY,
            alarm_code TEXT NOT NULL,
            alarm_name TEXT NOT NULL,
            note_text TEXT,
            image_path TEXT,
            image_name TEXT,
            mime_type TEXT,
            file_size BIGINT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (alarm_code, alarm_name)
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mtba.etl_job_run_log (
            run_id BIGSERIAL PRIMARY KEY,
            job_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TIMESTAMP NOT NULL DEFAULT NOW(),
            finished_at TIMESTAMP,
            message TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mtba.etl_source_watermark (
            source_name TEXT PRIMARY KEY,
            max_base_date DATE,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))


def ensure_indexes_and_constraints(conn) -> None:
    ddl_list = [
        "CREATE INDEX IF NOT EXISTS idx_fact_runtime_daily_date ON mtba.fact_runtime_daily (base_date)",
        "CREATE INDEX IF NOT EXISTS idx_fact_alarm_daily_date ON mtba.fact_alarm_daily (base_date)",
        "CREATE INDEX IF NOT EXISTS idx_fact_alarm_detail_daily_date ON mtba.fact_alarm_detail_daily (base_date)",
        "CREATE INDEX IF NOT EXISTS idx_fact_production_daily_date ON mtba.fact_production_daily (base_date)",
        "CREATE INDEX IF NOT EXISTS idx_fact_alarm_detail_daily_eq_date ON mtba.fact_alarm_detail_daily (equipment_id, base_date)",
        "CREATE INDEX IF NOT EXISTS idx_fact_production_daily_eq_date ON mtba.fact_production_daily (equipment_id, base_date)",
        "CREATE INDEX IF NOT EXISTS idx_dim_equipment_name ON mtba.dim_equipment (equipment_name)",
        "CREATE INDEX IF NOT EXISTS idx_dim_process_name ON mtba.dim_process (process_name)",
        "CREATE INDEX IF NOT EXISTS idx_dim_model_name ON mtba.dim_model (model_name)",
        "CREATE INDEX IF NOT EXISTS idx_dim_equipment_segment_name ON mtba.dim_equipment (segment_name)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_runtime_daily_bk ON mtba.fact_runtime_daily (base_date, plant_id, process_id, equipment_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_alarm_daily_bk ON mtba.fact_alarm_daily (base_date, plant_id, process_id, equipment_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_alarm_detail_daily_bk ON mtba.fact_alarm_detail_daily (base_date, plant_id, process_id, equipment_id, COALESCE(model_id, -1), COALESCE(alarm_id, -1))",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_fact_production_daily_bk ON mtba.fact_production_daily (base_date, plant_id, process_id, COALESCE(equipment_id, -1), COALESCE(model_id, -1))",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_dim_alarm_bk ON mtba.dim_alarm (process_name, alarm_code, alarm_name, COALESCE(model_name, '__NULL__'))",
    ]
    for ddl in ddl_list:
        conn.execute(text(ddl))


def refresh_mv_if_exists(conn, mv_name: str) -> None:
    if table_exists(conn, mv_name):
        print(f"[INFO] REFRESH MATERIALIZED VIEW: {mv_name}")
        conn.execute(text(f"REFRESH MATERIALIZED VIEW {mv_name}"))
    else:
        print(f"[WARN] MV 없음 - REFRESH 건너뜀: {mv_name}")


def analyze_tables(conn, table_names: list[str]) -> None:
    done = set()
    for t in table_names:
        if t in done:
            continue
        done.add(t)
        print(f"[INFO] ANALYZE: {t}")
        conn.execute(text(f"ANALYZE {t}"))


# =========================================================
# 4. LOCK / WATERMARK / FAST INSERT HELPERS
# =========================================================
def try_acquire_etl_lock(conn, lock_key: int = 987654321) -> bool:
    return bool(conn.execute(text("SELECT pg_try_advisory_lock(:lock_key)"), {"lock_key": lock_key}).scalar())


def release_etl_lock(conn, lock_key: int = 987654321) -> None:
    conn.execute(text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": lock_key})


def get_source_watermark(conn, source_name: str):
    result = conn.execute(text("SELECT max_base_date FROM mtba.etl_source_watermark WHERE source_name = :source_name"), {"source_name": source_name}).scalar()
    return pd.to_datetime(result).date() if result is not None else None


def upsert_source_watermark(conn, source_name: str, max_base_date):
    conn.execute(text("""
        INSERT INTO mtba.etl_source_watermark (source_name, max_base_date, updated_at)
        VALUES (:source_name, :max_base_date, NOW())
        ON CONFLICT (source_name)
        DO UPDATE SET
            max_base_date = EXCLUDED.max_base_date,
            updated_at = NOW()
    """), {"source_name": source_name, "max_base_date": max_base_date})


def filter_incremental_by_date(df: pd.DataFrame, base_date_col: str, max_loaded_date, lookback_days: int) -> pd.DataFrame:
    if df.empty or max_loaded_date is None:
        return df
    cutoff = max_loaded_date - timedelta(days=lookback_days)
    filtered = df[df[base_date_col] >= cutoff].copy()
    print(f"[INFO] watermark filter: max_loaded_date={max_loaded_date}, lookback_days={lookback_days}, before={len(df)}, after={len(filtered)}")
    return filtered


def insert_via_stage_on_conflict(conn, df: pd.DataFrame, schema: str, table: str) -> int:
    if df.empty:
        print(f"[INFO] {schema}.{table} 신규 후보 rows 없음")
        return 0
    df = df.drop_duplicates().copy()
    temp_table = f"_stg_{table}_{uuid4().hex[:8]}"
    full_temp_name = f"{schema}.{temp_table}"
    full_target_name = f"{schema}.{table}"
    print(f"[INFO] staging 적재: {full_temp_name} ({len(df)} rows)")
    df.to_sql(temp_table, conn, schema=schema, if_exists="replace", index=False, method="multi", chunksize=2000)
    cols = list(df.columns)
    insert_sql = f"""
        WITH ins AS (
            INSERT INTO {full_target_name} ({", ".join(cols)})
            SELECT {", ".join(cols)}
            FROM {full_temp_name}
            ON CONFLICT DO NOTHING
            RETURNING 1
        )
        SELECT COUNT(*) FROM ins
    """
    inserted_count = conn.execute(text(insert_sql)).scalar() or 0
    conn.execute(text(f"DROP TABLE IF EXISTS {full_temp_name}"))
    print(f"[INFO] {full_target_name} 신규 insert rows = {inserted_count}")
    return int(inserted_count)


# =========================================================
# 5. FILE READERS
# =========================================================
def read_excel_safely(path: str) -> pd.DataFrame:
    validate_file_exists(path)
    print(f"[INFO] Excel 읽기: {path}")
    return normalize_columns(pd.read_excel(path, engine="openpyxl"))


def read_production_csv(path: str) -> pd.DataFrame:
    validate_file_exists(path)
    encodings = ["utf-16", "utf-8", "utf-8-sig", "cp949", "euc-kr", "utf-16le", "utf-16be"]
    skip_options = [2, 0]
    expected_cols = {"공장명", "공정명", "모델명", "설비명", "재공일자"}
    last_error = None

    with open(path, "rb") as f:
        head = f.read(10)
        print(f"[DEBUG] Production CSV first 10 bytes = {head}")

    for enc in encodings:
        for skip in skip_options:
            try:
                print(f"[INFO] Production CSV 읽기 시도: encoding={enc}, skiprows={skip}")
                df = pd.read_csv(path, encoding=enc, skiprows=skip)
                df = normalize_columns(df)
                print(f"[DEBUG] columns({enc}, skip={skip}) = {list(df.columns)}")
                if len(expected_cols.intersection(set(df.columns))) >= 3:
                    print(f"[INFO] Production CSV 읽기 성공: encoding={enc}, skiprows={skip}")
                    return df
            except Exception as e:
                last_error = e
                print(f"[WARN] 실패: encoding={enc}, skiprows={skip}, error={e}")
    raise RuntimeError(f"MTBA_Production.csv 읽기 실패. 마지막 오류: {last_error}")


# =========================================================
# 6. DIM HELPERS
# =========================================================
def insert_dim_plant(conn, plant_names: Iterable[str]) -> None:
    for plant_name in sorted(set([x for x in plant_names if pd.notna(x)])):
        conn.execute(text("INSERT INTO mtba.dim_plant (plant_name) VALUES (:plant_name) ON CONFLICT (plant_name) DO NOTHING"), {"plant_name": plant_name})


def insert_dim_model(conn, model_names: Iterable[str]) -> None:
    for model_name in sorted(set([x for x in model_names if pd.notna(x)])):
        conn.execute(text("INSERT INTO mtba.dim_model (model_name) VALUES (:model_name) ON CONFLICT (model_name) DO NOTHING"), {"model_name": model_name})


def insert_dim_process(conn, df: pd.DataFrame) -> None:
    validate_required_columns(df, ["plant_name", "process_name"], "insert_dim_process")
    plant_df = pd.read_sql("SELECT plant_id, plant_name FROM mtba.dim_plant", conn)
    temp = df[["plant_name", "process_name"]].dropna().drop_duplicates().merge(plant_df, on="plant_name", how="left")
    for _, row in temp.iterrows():
        if pd.isna(row["plant_id"]):
            continue
        conn.execute(text("INSERT INTO mtba.dim_process (plant_id, process_name) VALUES (:plant_id, :process_name) ON CONFLICT (plant_id, process_name) DO NOTHING"), {"plant_id": int(row["plant_id"]), "process_name": row["process_name"]})


def insert_dim_equipment(conn, df: pd.DataFrame) -> None:
    validate_required_columns(df, ["plant_name", "process_name", "equipment_name"], "insert_dim_equipment")
    plant_df = pd.read_sql("SELECT plant_id, plant_name FROM mtba.dim_plant", conn)
    process_df = pd.read_sql("SELECT dp.process_id, dp.process_name, pl.plant_name FROM mtba.dim_process dp JOIN mtba.dim_plant pl ON dp.plant_id = pl.plant_id", conn)
    use_segment = "segment_name" in df.columns
    base_cols = ["plant_name", "process_name", "equipment_name"] + (["segment_name"] if use_segment else [])
    temp = df[base_cols].drop_duplicates().copy()
    temp["plant_name"] = normalize_text_key(temp["plant_name"])
    temp["process_name"] = normalize_text_key(temp["process_name"])
    temp["equipment_name"] = normalize_text_key(temp["equipment_name"])
    temp["segment_name"] = normalize_text_key(temp["segment_name"]) if use_segment else pd.NA
    temp = temp.dropna(subset=["plant_name", "process_name", "equipment_name"])
    temp = temp.merge(plant_df, on="plant_name", how="left")
    temp = temp.merge(process_df[["process_id", "process_name", "plant_name"]], on=["plant_name", "process_name"], how="left")
    temp["equipment_no"] = temp["equipment_name"].apply(extract_equipment_no)

    for _, row in temp.iterrows():
        if pd.isna(row["plant_id"]) or pd.isna(row["process_id"]):
            continue
        conn.execute(text("""
            INSERT INTO mtba.dim_equipment (
                plant_id,
                process_id,
                equipment_name,
                equipment_no,
                segment_name
            )
            VALUES (
                :plant_id,
                :process_id,
                :equipment_name,
                :equipment_no,
                :segment_name
            )
            ON CONFLICT (plant_id, equipment_name)
            DO UPDATE SET
                process_id = EXCLUDED.process_id,
                equipment_no = COALESCE(EXCLUDED.equipment_no, mtba.dim_equipment.equipment_no),
                segment_name = COALESCE(EXCLUDED.segment_name, mtba.dim_equipment.segment_name)
        """), {
            "plant_id": int(row["plant_id"]),
            "process_id": int(row["process_id"]),
            "equipment_name": row["equipment_name"],
            "equipment_no": row["equipment_no"],
            "segment_name": None if pd.isna(row["segment_name"]) else row["segment_name"],
        })


def build_common_mappings(conn):
    plant_df = pd.read_sql("SELECT plant_id, plant_name FROM mtba.dim_plant", conn)
    process_df = pd.read_sql("SELECT dp.process_id, dp.process_name, pl.plant_name FROM mtba.dim_process dp JOIN mtba.dim_plant pl ON dp.plant_id = pl.plant_id", conn)
    equipment_df = pd.read_sql("SELECT de.equipment_id, de.equipment_name, de.equipment_no, de.segment_name, pl.plant_name FROM mtba.dim_equipment de JOIN mtba.dim_plant pl ON de.plant_id = pl.plant_id", conn)
    model_df = pd.read_sql("SELECT model_id, model_name FROM mtba.dim_model", conn)
    return plant_df, process_df, equipment_df, model_df


# =========================================================
# 7. LOADERS
# =========================================================
def load_alarm_master(conn) -> int:
    df = read_excel_safely(ALARM_MASTER_XLSX)
    df = df.rename(columns={"공장ID": "plant_code", "공정ID": "process_code", "공정": "process_name", "알람코드": "alarm_code", "알람명": "alarm_name", "Model": "model_name", "중요등급": "importance_grade"})
    validate_required_columns(df, ["process_name", "alarm_code", "alarm_name"], "load_alarm_master")
    for c in ["plant_code", "process_code", "process_name", "alarm_code", "alarm_name", "model_name", "importance_grade"]:
        if c not in df.columns:
            df[c] = None
    for c in ["plant_code", "process_code", "process_name", "alarm_name", "model_name", "importance_grade"]:
        df[c] = normalize_text_key(df[c])
    df["alarm_code"] = normalize_alarm_code(df["alarm_code"])
    valid_rows = df.loc[~(df["process_name"].isna() | df["alarm_name"].isna() | df["alarm_code"].isna()), ["plant_code", "process_code", "process_name", "alarm_code", "alarm_name", "model_name", "importance_grade"]].drop_duplicates().copy()
    return insert_via_stage_on_conflict(conn, valid_rows, "mtba", "dim_alarm")


def load_runtime(conn) -> int:
    source_name = "fact_runtime_daily"
    df = read_excel_safely(RUNTIME_XLSX)
    df = df.rename(columns={"공장": "plant_name", "공정": "process_name", "설비": "equipment_name", "날짜": "base_date", "설비상태변경소요시간(분)": "runtime_minutes"})
    validate_required_columns(df, ["plant_name", "process_name", "equipment_name", "base_date", "runtime_minutes"], "load_runtime")
    df["plant_name"] = normalize_text_key(df["plant_name"])
    df["process_name"] = normalize_text_key(df["process_name"])
    df["equipment_name"] = normalize_text_key(df["equipment_name"])
    df["base_date"] = parse_date_series(df["base_date"])
    df["runtime_minutes"] = pd.to_numeric(df["runtime_minutes"], errors="coerce").fillna(0)
    df = filter_incremental_by_date(df, "base_date", get_source_watermark(conn, source_name), LOOKBACK_DAYS)
    plant_df, process_df, equipment_df, _ = build_common_mappings(conn)
    merged = df.merge(plant_df, on="plant_name", how="left")
    merged = merged.merge(process_df[["process_id", "process_name", "plant_name"]], on=["plant_name", "process_name"], how="left")
    merged = merged.merge(equipment_df[["equipment_id", "equipment_name", "plant_name"]], on=["plant_name", "equipment_name"], how="left")
    rows = merged[["base_date", "plant_id", "process_id", "equipment_id", "runtime_minutes"]].dropna(subset=["base_date", "plant_id", "process_id", "equipment_id"]).copy()
    rows["source_file"] = Path(RUNTIME_XLSX).name
    inserted = insert_via_stage_on_conflict(conn, rows, "mtba", "fact_runtime_daily")
    if not rows.empty:
        upsert_source_watermark(conn, source_name, rows["base_date"].max())
    return inserted


def load_alarm_daily(conn) -> int:
    source_name = "fact_alarm_daily"
    df = read_excel_safely(ALARM_DAILY_XLSX)
    df = df.rename(columns={"공장": "plant_name", "공정": "process_name", "설비": "equipment_name", "날짜": "base_date", "알람발생건수": "alarm_count_total"})
    validate_required_columns(df, ["plant_name", "process_name", "equipment_name", "base_date", "alarm_count_total"], "load_alarm_daily")
    df["plant_name"] = normalize_text_key(df["plant_name"])
    df["process_name"] = normalize_text_key(df["process_name"])
    df["equipment_name"] = normalize_text_key(df["equipment_name"])
    df["base_date"] = parse_date_series(df["base_date"])
    df["alarm_count_total"] = pd.to_numeric(df["alarm_count_total"], errors="coerce").fillna(0).astype(int)
    df = filter_incremental_by_date(df, "base_date", get_source_watermark(conn, source_name), LOOKBACK_DAYS)
    plant_df, process_df, equipment_df, _ = build_common_mappings(conn)
    merged = df.merge(plant_df, on="plant_name", how="left")
    merged = merged.merge(process_df[["process_id", "process_name", "plant_name"]], on=["plant_name", "process_name"], how="left")
    merged = merged.merge(equipment_df[["equipment_id", "equipment_name", "plant_name"]], on=["plant_name", "equipment_name"], how="left")
    rows = merged[["base_date", "plant_id", "process_id", "equipment_id", "alarm_count_total"]].dropna(subset=["base_date", "plant_id", "process_id", "equipment_id"]).copy()
    rows["source_file"] = Path(ALARM_DAILY_XLSX).name
    inserted = insert_via_stage_on_conflict(conn, rows, "mtba", "fact_alarm_daily")
    if not rows.empty:
        upsert_source_watermark(conn, source_name, rows["base_date"].max())
    return inserted


def load_alarm_detail(conn) -> int:
    source_name = "fact_alarm_detail_daily"
    df = read_excel_safely(ALARM_DETAIL_XLSX)
    df = df.rename(columns={"공장": "plant_name", "공정": "process_name", "설비": "equipment_name", "날짜": "base_date", "알람코드": "alarm_code", "알람내용(무시기준적용후2)": "alarm_name", "알람발생건수": "alarm_count", "Model": "model_name", "중요등급": "importance_grade"})
    validate_required_columns(df, ["plant_name", "process_name", "equipment_name", "base_date", "alarm_code", "alarm_name", "alarm_count"], "load_alarm_detail")
    df["plant_name"] = normalize_text_key(df["plant_name"])
    df["process_name"] = normalize_text_key(df["process_name"])
    df["equipment_name"] = normalize_text_key(df["equipment_name"])
    df["alarm_name"] = normalize_text_key(df["alarm_name"])
    df["alarm_code"] = normalize_alarm_code(df["alarm_code"])
    df["model_name"] = normalize_text_key(df["model_name"]) if "model_name" in df.columns else pd.NA
    df["base_date"] = parse_date_series(df["base_date"])
    df["alarm_count"] = pd.to_numeric(df["alarm_count"], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["plant_name", "process_name", "equipment_name", "base_date", "alarm_code", "alarm_name"])
    df = filter_incremental_by_date(df, "base_date", get_source_watermark(conn, source_name), LOOKBACK_DAYS)
    if df.empty:
        print("[INFO] fact_alarm_detail_daily 처리 대상 없음")
        return 0
    plant_df, process_df, equipment_df, model_df = build_common_mappings(conn)
    alarm_seed = df[["process_name", "alarm_code", "alarm_name", "model_name"]].copy()
    alarm_seed["process_name"] = normalize_text_key(alarm_seed["process_name"])
    alarm_seed["alarm_code"] = normalize_alarm_code(alarm_seed["alarm_code"])
    alarm_seed["alarm_name"] = normalize_text_key(alarm_seed["alarm_name"])
    alarm_seed["model_name"] = normalize_text_key(alarm_seed["model_name"])
    alarm_seed = alarm_seed.dropna(subset=["process_name", "alarm_code", "alarm_name"]).drop_duplicates()
    insert_via_stage_on_conflict(conn, alarm_seed, "mtba", "dim_alarm")
    alarm_df = pd.read_sql("SELECT alarm_id, process_name, alarm_code, alarm_name, model_name FROM mtba.dim_alarm", conn)
    merged = df.merge(plant_df, on="plant_name", how="left")
    merged = merged.merge(process_df[["process_id", "process_name", "plant_name"]], on=["plant_name", "process_name"], how="left")
    merged = merged.merge(equipment_df[["equipment_id", "equipment_name", "plant_name"]], on=["plant_name", "equipment_name"], how="left")
    merged = merged.merge(model_df, on="model_name", how="left")
    for col in ["process_name", "alarm_name", "model_name"]:
        if col in merged.columns:
            merged[col] = normalize_text_key(merged[col])
        if col in alarm_df.columns:
            alarm_df[col] = normalize_text_key(alarm_df[col])
    merged["alarm_code"] = normalize_alarm_code(merged["alarm_code"])
    alarm_df["alarm_code"] = normalize_alarm_code(alarm_df["alarm_code"])
    merged["process_name_key"] = to_join_key(merged["process_name"])
    merged["alarm_code_key"] = to_join_key(merged["alarm_code"])
    merged["alarm_name_key"] = to_join_key(merged["alarm_name"])
    merged["model_name_key"] = to_join_key(merged["model_name"])
    alarm_df["process_name_key"] = to_join_key(alarm_df["process_name"])
    alarm_df["alarm_code_key"] = to_join_key(alarm_df["alarm_code"])
    alarm_df["alarm_name_key"] = to_join_key(alarm_df["alarm_name"])
    alarm_df["model_name_key"] = to_join_key(alarm_df["model_name"])
    merged = merged.merge(alarm_df[["alarm_id", "process_name_key", "alarm_code_key", "alarm_name_key", "model_name_key"]], on=["process_name_key", "alarm_code_key", "alarm_name_key", "model_name_key"], how="left")
    rows = merged[["base_date", "plant_id", "process_id", "equipment_id", "model_id", "alarm_id", "alarm_count"]].dropna(subset=["base_date", "plant_id", "process_id", "equipment_id"]).copy()
    rows["source_file"] = Path(ALARM_DETAIL_XLSX).name
    inserted = insert_via_stage_on_conflict(conn, rows, "mtba", "fact_alarm_detail_daily")
    if not rows.empty:
        upsert_source_watermark(conn, source_name, rows["base_date"].max())
    return inserted


def load_production(conn) -> int:
    source_name = "fact_production_daily"
    df = read_production_csv(PRODUCTION_CSV)
    df = df.rename(columns={"공장명": "plant_name", "공정명": "process_name", "모델명": "model_name", "설비명": "equipment_name", "재공일자": "base_date", "투입수": "input_qty", "완공수": "output_qty", "불량수": "defect_qty", "설비세그먼트명": "segment_name"})
    validate_required_columns(df, ["plant_name", "process_name", "model_name", "equipment_name", "base_date"], "load_production")
    df["plant_name"] = normalize_text_key(df["plant_name"])
    df["process_name"] = normalize_text_key(df["process_name"])
    df["model_name"] = normalize_text_key(df["model_name"])
    df["equipment_name"] = normalize_text_key(df["equipment_name"])
    df["segment_name"] = normalize_text_key(df["segment_name"]) if "segment_name" in df.columns else pd.NA
    df["base_date"] = parse_date_series(df["base_date"])
    for c in ["input_qty", "output_qty", "defect_qty"]:
        df[c] = clean_numeric(df[c]).fillna(0) if c in df.columns else 0
    df = filter_incremental_by_date(df, "base_date", get_source_watermark(conn, source_name), LOOKBACK_DAYS)
    plant_df, process_df, equipment_df, model_df = build_common_mappings(conn)
    merged = df.merge(plant_df, on="plant_name", how="left")
    merged = merged.merge(process_df[["process_id", "process_name", "plant_name"]], on=["plant_name", "process_name"], how="left")
    merged = merged.merge(equipment_df[["equipment_id", "equipment_name", "plant_name"]], on=["plant_name", "equipment_name"], how="left")
    merged = merged.merge(model_df, on="model_name", how="left")
    rows = merged[["base_date", "plant_id", "process_id", "equipment_id", "model_id", "input_qty", "output_qty", "defect_qty"]].dropna(subset=["base_date", "plant_id", "process_id", "model_id"]).copy()
    rows["source_file"] = Path(PRODUCTION_CSV).name
    inserted = insert_via_stage_on_conflict(conn, rows, "mtba", "fact_production_daily")
    if not rows.empty:
        upsert_source_watermark(conn, source_name, rows["base_date"].max())
    return inserted


# =========================================================
# 8. POST PROCESSING
# =========================================================
def insert_sample_process_aliases(conn) -> None:
    alias_map = {
        "Shield can attach": "SCA",
        "Shield can reinforcement": "SCR",
        "Terminal Connection": "TC",
        "Durango Filling": "DIF",
        "Glue Locking": "GL",
        "Baffle Sidefill": "BS",
        "Module sealing": "MS",
        "Laser marking": "LM",
    }
    for process_name, short_name in alias_map.items():
        conn.execute(text("UPDATE mtba.dim_process SET process_short = :short_name WHERE process_name = :process_name"), {"process_name": process_name, "short_name": short_name})


def refresh_views(conn) -> None:
    refresh_mv_if_exists(conn, "mtba.mv_equipment_model_daily")
    refresh_mv_if_exists(conn, "mtba.mv_mtba_weekly_equipment")
    refresh_mv_if_exists(conn, "mtba.mv_mtba_weekly_process_stats")
    refresh_mv_if_exists(conn, "mtba.mv_alarm_weekly_equipment_detail")
    refresh_detail_page_mv_if_exists(conn)


# =========================================================
# 9. DETAIL PAGE MV
# =========================================================
def ensure_detail_page_mv(conn) -> None:
    """
    [수정사항] 기존 MV 자동 재생성 방식
    - 기존 mv_detail_page_daily 가 있으면 DROP 후 다시 CREATE
    - 새 정의에 de.segment_name 포함
    """
    if table_exists(conn, "mtba.mv_detail_page_daily"):
        print("[INFO] DROP MATERIALIZED VIEW: mtba.mv_detail_page_daily")
        conn.execute(text("DROP MATERIALIZED VIEW mtba.mv_detail_page_daily"))

    print("[INFO] CREATE MATERIALIZED VIEW: mtba.mv_detail_page_daily")
    conn.execute(text("""
        CREATE MATERIALIZED VIEW mtba.mv_detail_page_daily AS
        WITH prod_rank AS (
            SELECT
                fp.base_date,
                fp.equipment_id,
                fp.model_id,
                SUM(COALESCE(fp.output_qty, 0)) AS sum_output_qty,
                SUM(COALESCE(fp.input_qty, 0)) AS sum_input_qty,
                ROW_NUMBER() OVER (
                    PARTITION BY fp.base_date, fp.equipment_id
                    ORDER BY
                        SUM(COALESCE(fp.output_qty, 0)) DESC,
                        SUM(COALESCE(fp.input_qty, 0)) DESC,
                        fp.model_id
                ) AS rn
            FROM mtba.fact_production_daily fp
            GROUP BY fp.base_date, fp.equipment_id, fp.model_id
        ),
        prod_map AS (
            SELECT base_date, equipment_id, model_id
            FROM prod_rank
            WHERE rn = 1
        ),
        prod_day AS (
            SELECT
                fp.base_date,
                fp.equipment_id,
                fp.model_id,
                SUM(COALESCE(fp.output_qty, 0)) AS output_qty
            FROM mtba.fact_production_daily fp
            GROUP BY fp.base_date, fp.equipment_id, fp.model_id
        ),
        alarm_detail_day AS (
            SELECT
                fad.base_date,
                fad.equipment_id,
                fad.alarm_id,
                SUM(COALESCE(fad.alarm_count, 0)) AS alarm_count
            FROM mtba.fact_alarm_detail_daily fad
            GROUP BY fad.base_date, fad.equipment_id, fad.alarm_id
        ),
        alarm_daily_total AS (
            SELECT
                fad.base_date,
                fad.equipment_id,
                SUM(COALESCE(fad.alarm_count, 0)) AS total_alarm_count
            FROM mtba.fact_alarm_detail_daily fad
            GROUP BY fad.base_date, fad.equipment_id
        )
        SELECT
            rt.base_date,
            pm.model_id,
            dm.model_name,
            de.process_id,
            dp.process_name,
            rt.equipment_id,
            de.equipment_name,
            COALESCE(NULLIF(TRIM(COALESCE(de.equipment_no, '')), ''), de.equipment_name) AS equipment_no,
            de.segment_name,
            da.alarm_id,
            da.alarm_name,
            COALESCE(addy.alarm_count, 0) AS alarm_count,
            COALESCE(pd.output_qty, 0) AS output_qty,
            COALESCE(rt.runtime_minutes, 0) AS runtime_minutes,
            COALESCE(adt.total_alarm_count, 0) AS daily_total_alarm_count,
            CASE
                WHEN COALESCE(adt.total_alarm_count, 0) > 0
                THEN ROUND(rt.runtime_minutes::numeric / adt.total_alarm_count::numeric, 2)
                ELSE rt.runtime_minutes::numeric
            END AS daily_mtba
        FROM mtba.fact_runtime_daily rt
        JOIN mtba.dim_equipment de ON rt.equipment_id = de.equipment_id
        JOIN mtba.dim_process dp ON de.process_id = dp.process_id
        LEFT JOIN prod_map pm ON rt.base_date = pm.base_date AND rt.equipment_id = pm.equipment_id
        LEFT JOIN mtba.dim_model dm ON pm.model_id = dm.model_id
        LEFT JOIN prod_day pd ON rt.base_date = pd.base_date AND rt.equipment_id = pd.equipment_id AND pm.model_id IS NOT DISTINCT FROM pd.model_id
        LEFT JOIN alarm_detail_day addy ON rt.base_date = addy.base_date AND rt.equipment_id = addy.equipment_id
        LEFT JOIN mtba.dim_alarm da ON addy.alarm_id = da.alarm_id
        LEFT JOIN alarm_daily_total adt ON rt.base_date = adt.base_date AND rt.equipment_id = adt.equipment_id
        WITH NO DATA
    """))


def ensure_detail_page_mv_indexes(conn) -> None:
    idx_sqls = [
        "CREATE INDEX IF NOT EXISTS idx_mv_detail_page_daily_model_proc_date ON mtba.mv_detail_page_daily (model_name, process_name, base_date)",
        "CREATE INDEX IF NOT EXISTS idx_mv_detail_page_daily_eq_date ON mtba.mv_detail_page_daily (equipment_id, base_date)",
        "CREATE INDEX IF NOT EXISTS idx_mv_detail_page_daily_proc_date ON mtba.mv_detail_page_daily (process_name, base_date)",
        "CREATE INDEX IF NOT EXISTS idx_mv_detail_page_daily_alarm ON mtba.mv_detail_page_daily (alarm_name)",
        "CREATE INDEX IF NOT EXISTS idx_mv_detail_page_daily_segment_name ON mtba.mv_detail_page_daily (segment_name)",
    ]
    for sql in idx_sqls:
        conn.execute(text(sql))


def refresh_detail_page_mv_if_exists(conn) -> None:
    if table_exists(conn, "mtba.mv_detail_page_daily"):
        print("[INFO] REFRESH MATERIALIZED VIEW: mtba.mv_detail_page_daily")
        conn.execute(text("REFRESH MATERIALIZED VIEW mtba.mv_detail_page_daily"))


# =========================================================
# 10. MAIN
# =========================================================
def main() -> None:
    print("=" * 80)
    print("[INFO] load_to_postgres.py 시작 (Fast Incremental Append + Archive Move)")
    print("=" * 80)
    print(f"[INFO] LOOKBACK_DAYS = {LOOKBACK_DAYS}")

    # 디버그
    with engine.connect() as conn:
        print("[DEBUG] current_database/current_user 확인")
        print(conn.execute(text("SELECT current_database(), current_user, inet_server_addr(), inet_server_port()")).fetchall())
        print("[DEBUG] dim_equipment 컬럼 확인")
        cols = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'mtba' AND table_name = 'dim_equipment' ORDER BY ordinal_position")).fetchall()
        print(cols)

    print_connection_info()

    source_files = [RUNTIME_XLSX, ALARM_DAILY_XLSX, ALARM_DETAIL_XLSX, ALARM_MASTER_XLSX, PRODUCTION_CSV]
    source_dirs = sorted({str(Path(RUNTIME_XLSX).resolve().parent), str(Path(ALARM_DAILY_XLSX).resolve().parent), str(Path(ALARM_DETAIL_XLSX).resolve().parent), str(Path(ALARM_MASTER_XLSX).resolve().parent), str(Path(PRODUCTION_CSV).resolve().parent)})

    for p in source_files:
        validate_file_exists(p)
        print(f"[INFO] file ok: {p}")

    runtime_df = read_excel_safely(RUNTIME_XLSX).rename(columns={"공장": "plant_name", "공정": "process_name", "설비": "equipment_name"})
    validate_required_columns(runtime_df, ["plant_name", "process_name", "equipment_name"], "runtime_df")
    runtime_df["plant_name"] = normalize_text_key(runtime_df["plant_name"])
    runtime_df["process_name"] = normalize_text_key(runtime_df["process_name"])
    runtime_df["equipment_name"] = normalize_text_key(runtime_df["equipment_name"])

    alarm_daily_df = read_excel_safely(ALARM_DAILY_XLSX).rename(columns={"공장": "plant_name", "공정": "process_name", "설비": "equipment_name"})
    validate_required_columns(alarm_daily_df, ["plant_name", "process_name", "equipment_name"], "alarm_daily_df")
    alarm_daily_df["plant_name"] = normalize_text_key(alarm_daily_df["plant_name"])
    alarm_daily_df["process_name"] = normalize_text_key(alarm_daily_df["process_name"])
    alarm_daily_df["equipment_name"] = normalize_text_key(alarm_daily_df["equipment_name"])

    alarm_detail_df = read_excel_safely(ALARM_DETAIL_XLSX).rename(columns={"공장": "plant_name", "공정": "process_name", "설비": "equipment_name", "Model": "model_name"})
    validate_required_columns(alarm_detail_df, ["plant_name", "process_name", "equipment_name"], "alarm_detail_df")
    alarm_detail_df["plant_name"] = normalize_text_key(alarm_detail_df["plant_name"])
    alarm_detail_df["process_name"] = normalize_text_key(alarm_detail_df["process_name"])
    alarm_detail_df["equipment_name"] = normalize_text_key(alarm_detail_df["equipment_name"])
    alarm_detail_df["model_name"] = normalize_text_key(alarm_detail_df["model_name"]) if "model_name" in alarm_detail_df.columns else pd.NA

    production_df = read_production_csv(PRODUCTION_CSV).rename(columns={"공장명": "plant_name", "공정명": "process_name", "설비명": "equipment_name", "모델명": "model_name", "설비세그먼트명": "segment_name"})
    validate_required_columns(production_df, ["plant_name", "process_name", "equipment_name", "model_name"], "production_df(main)")
    production_df["plant_name"] = normalize_text_key(production_df["plant_name"])
    production_df["process_name"] = normalize_text_key(production_df["process_name"])
    production_df["equipment_name"] = normalize_text_key(production_df["equipment_name"])
    production_df["model_name"] = normalize_text_key(production_df["model_name"])
    production_df["segment_name"] = normalize_text_key(production_df["segment_name"]) if "segment_name" in production_df.columns else pd.NA

    plant_names = pd.concat([runtime_df["plant_name"], alarm_daily_df["plant_name"], alarm_detail_df["plant_name"], production_df["plant_name"]], ignore_index=True)
    model_names = pd.concat([alarm_detail_df["model_name"], production_df["model_name"]], ignore_index=True)

    runtime_eq_df = runtime_df[["plant_name", "process_name", "equipment_name"]].copy(); runtime_eq_df["segment_name"] = pd.NA
    alarm_daily_eq_df = alarm_daily_df[["plant_name", "process_name", "equipment_name"]].copy(); alarm_daily_eq_df["segment_name"] = pd.NA
    alarm_detail_eq_df = alarm_detail_df[["plant_name", "process_name", "equipment_name"]].copy(); alarm_detail_eq_df["segment_name"] = pd.NA
    prod_eq_df = production_df[["plant_name", "process_name", "equipment_name", "segment_name"]].copy()

    # FutureWarning 방지: all-NA segment_name 만 있는 DF는 concat 대상에서 제외
    dfs = [runtime_eq_df, alarm_daily_eq_df, alarm_detail_eq_df, prod_eq_df]
    dfs = [d for d in dfs if not ("segment_name" in d.columns and d["segment_name"].isna().all())]
    process_eq_df = pd.concat(dfs, ignore_index=True).drop_duplicates() if dfs else pd.DataFrame(columns=["plant_name", "process_name", "equipment_name", "segment_name"])

    job_name = "mtba_incremental_append_fast"
    run_id = None
    executed_at = datetime.now()
    changed_tables: list[str] = []
    fact_changed = False

    with engine.connect() as conn:
        ensure_aux_tables(conn)
        ensure_indexes_and_constraints(conn)
        ensure_detail_page_mv(conn)
        ensure_detail_page_mv_indexes(conn)
        conn.commit()

        locked = try_acquire_etl_lock(conn)
        conn.commit()
        if not locked:
            print("[WARN] 이미 ETL이 실행 중입니다. 이번 실행은 건너뜁니다.")
            conn.execute(text("INSERT INTO mtba.etl_job_run_log (job_name, status, message) VALUES (:job_name, 'SKIPPED', 'Another ETL run is already in progress.')"), {"job_name": job_name})
            conn.commit()
            return

        try:
            run_id = conn.execute(text("INSERT INTO mtba.etl_job_run_log (job_name, status, message) VALUES (:job_name, 'RUNNING', 'Fast incremental ETL started.') RETURNING run_id"), {"job_name": job_name}).scalar()
            conn.commit()

            if not schema_exists(conn, "mtba"):
                raise RuntimeError("mtba 스키마가 없습니다. 먼저 schema.sql을 실행해서 스키마/테이블/View를 생성하세요.")

            print("[INFO] Incremental mode - truncate 없음")
            insert_dim_plant(conn, plant_names.tolist())
            insert_dim_model(conn, model_names.tolist())
            insert_dim_process(conn, process_eq_df[["plant_name", "process_name"]].drop_duplicates())
            insert_dim_equipment(conn, process_eq_df)

            ins_alarm_master = load_alarm_master(conn)
            if ins_alarm_master > 0:
                changed_tables.append("mtba.dim_alarm")
            ins_runtime = load_runtime(conn)
            if ins_runtime > 0:
                changed_tables.append("mtba.fact_runtime_daily"); fact_changed = True
            ins_alarm_daily = load_alarm_daily(conn)
            if ins_alarm_daily > 0:
                changed_tables.append("mtba.fact_alarm_daily"); fact_changed = True
            ins_alarm_detail = load_alarm_detail(conn)
            if ins_alarm_detail > 0:
                changed_tables.append("mtba.fact_alarm_detail_daily"); fact_changed = True
            ins_production = load_production(conn)
            if ins_production > 0:
                changed_tables.append("mtba.fact_production_daily"); fact_changed = True

            insert_sample_process_aliases(conn)
            total_inserted = ins_alarm_master + ins_runtime + ins_alarm_daily + ins_alarm_detail + ins_production
            print(f"[INFO] total inserted rows = {total_inserted}")

            if fact_changed:
                refresh_views(conn)
            if changed_tables:
                analyze_tables(conn, changed_tables)
            else:
                print("[INFO] 신규 적재 rows가 없어 MV refresh / ANALYZE 생략")
            conn.commit()

            archive_messages = move_processed_files(source_dirs, executed_at)
            archive_message_text = "\n".join(archive_messages)
            conn.execute(text("UPDATE mtba.etl_job_run_log SET status = 'SUCCESS', finished_at = NOW(), message = :message WHERE run_id = :run_id"), {"run_id": run_id, "message": f"Fast incremental ETL completed successfully. inserted={total_inserted}\n{archive_message_text}"[:4000]})
            conn.commit()

        except Exception as e:
            conn.rollback()
            if run_id is not None:
                conn.execute(text("UPDATE mtba.etl_job_run_log SET status = 'FAILED', finished_at = NOW(), message = :message WHERE run_id = :run_id"), {"run_id": run_id, "message": str(e)[:4000]})
                conn.commit()
            raise

        finally:
            release_etl_lock(conn)
            conn.commit()

    print("=" * 80)
    print("[INFO] Fast Incremental ETL 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
