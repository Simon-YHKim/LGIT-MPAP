from __future__ import annotations

import os
import configparser
from dataclasses import dataclass
from typing import Optional

import pandas as pd
import psycopg2
import re


# R4 — env var override 지원 (기본값 보존: 폐쇄망 그대로 작동).
DEFAULT_DB_HOST     = os.getenv('ITAS_DB_HOST',     'localhost')
DEFAULT_DB_PORT     = int(os.getenv('ITAS_DB_PORT', '5432'))
DEFAULT_DB_NAME     = os.getenv('ITAS_DB_NAME',     'I-TAS_Data')
DEFAULT_DB_USER     = os.getenv('ITAS_DB_USER',     'postgres')
DEFAULT_DB_PASSWORD = os.getenv('ITAS_DB_PASSWORD', '!Q2w3e4r5t')
DEFAULT_DB_SCHEMA   = os.getenv('ITAS_DB_SCHEMA',   'public')
DEFAULT_MES_DB_NAME = os.getenv('MES_DB_NAME',      'MES_UPH')

ITAS_UPH_TABLE = 'itas_uph_result'
MES_UPH_TABLE = 'uph_input_runtime_daily_model'


@dataclass(frozen=True)
class DbConfig:
    host: str
    port: int
    dbname: str
    user: str
    password: str
    schema: str

def fetch_mes_process_name_candidates(db: DbConfig) -> list[str]:
    """
    MES DB에서 실제 process_name 후보 목록 조회
    """
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    SELECT DISTINCT process_name
    FROM {schema_q}.{table_q}
    WHERE process_name IS NOT NULL
      AND TRIM(process_name) <> ''
    ORDER BY process_name;
    """

    df = read_sql_df(query, db)
    if df.empty:
        return []

    return (
        df["process_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .drop_duplicates()
        .tolist()
    )

def fetch_mes_overall_avg_uph_for_day(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    customer_model: str | None = None,
) -> float | None:
    process_name = normalize_process_name(process_name)
    model_sql, model_params = _mes_customer_model_condition(customer_model)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    WITH machine_uph AS (
        SELECT
            equipment_name AS machine_no,
            SUM(uph) AS uph
        FROM {schema_q}.{table_q}
        WHERE process_name = %(process_name)s
          {model_sql}
          AND work_date = %(work_date)s
          AND uph IS NOT NULL
        GROUP BY equipment_name
    )
    SELECT AVG(uph) AS overall_avg_uph
    FROM machine_uph;
    """

    params = {
        "process_name": process_name,
        "work_date": selected_date.date(),
    }
    params.update(model_params)

    df = read_sql_df(query, db, params=params)
    if df.empty or pd.isna(df.iloc[0]["overall_avg_uph"]):
        return None

    return float(df.iloc[0]["overall_avg_uph"])


def fetch_itas_overall_avg_uph_for_day(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
) -> float | None:
    process_name = normalize_process_name(process_name)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)

    query = f"""
    WITH machine_uph AS (
        SELECT
            machine_no,
            uph
        FROM {schema_q}.{table_q}
        WHERE process_name = %(process_name)s
          AND work_date = %(work_date)s
          AND uph IS NOT NULL
    )
    SELECT AVG(uph) AS overall_avg_uph
    FROM machine_uph;
    """

    params = {
        "process_name": process_name,
        "work_date": selected_date.date(),
    }

    df = read_sql_df(query, db, params=params)
    if df.empty or pd.isna(df.iloc[0]["overall_avg_uph"]):
        return None

    return float(df.iloc[0]["overall_avg_uph"])

def fetch_mes_ranked_machines(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    rank_direction: str,
    top_n: int,
    customer_model: str | None = None,
) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)
    model_sql, model_params = _mes_customer_model_condition(customer_model)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    order_sql = "DESC" if rank_direction == "best" else "ASC"

    query = f"""
    SELECT
        equipment_name AS 호기,
        SUM(uph) AS uph
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      {model_sql}
      AND work_date = %(work_date)s
      AND uph IS NOT NULL
    GROUP BY equipment_name
    ORDER BY uph {order_sql} NULLS LAST, equipment_name
    LIMIT %(top_n)s;
    """

    params = {
        "process_name": process_name,
        "work_date": selected_date.date(),
        "top_n": int(top_n),
    }
    params.update(model_params)

    df = read_sql_df(query, db, params=params)

    if not df.empty:
        df["uph"] = pd.to_numeric(df["uph"], errors="coerce")

    return df

def fetch_mes_best_worst_ranked_machines(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    top_n: int,
    customer_model: str | None = None,
) -> pd.DataFrame:
    best_df = fetch_mes_ranked_machines(
        db=db,
        process_name=process_name,
        selected_date=selected_date,
        rank_direction="best",
        top_n=top_n,
        customer_model=customer_model,
    ).copy()

    worst_df = fetch_mes_ranked_machines(
        db=db,
        process_name=process_name,
        selected_date=selected_date,
        rank_direction="worst",
        top_n=top_n,
        customer_model=customer_model,
    ).copy()

    if not best_df.empty:
        best_df["구분"] = "Best"
        best_df["순위"] = range(1, len(best_df) + 1)

    if not worst_df.empty:
        worst_df["구분"] = "Worst"
        worst_df["순위"] = range(1, len(worst_df) + 1)

    cols = ["구분", "순위", "호기", "uph"]
    result = pd.concat([best_df, worst_df], ignore_index=True)

    if result.empty:
        return pd.DataFrame(columns=cols)

    return result[cols]

def fetch_itas_best_worst_ranked_machines(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    top_n: int,
) -> pd.DataFrame:
    best_df = fetch_itas_ranked_machines(
        db=db,
        process_name=process_name,
        selected_date=selected_date,
        rank_direction="best",
        top_n=top_n,
    ).copy()

    worst_df = fetch_itas_ranked_machines(
        db=db,
        process_name=process_name,
        selected_date=selected_date,
        rank_direction="worst",
        top_n=top_n,
    ).copy()

    if not best_df.empty:
        best_df["구분"] = "Best"
        best_df["순위"] = range(1, len(best_df) + 1)

    if not worst_df.empty:
        worst_df["구분"] = "Worst"
        worst_df["순위"] = range(1, len(worst_df) + 1)

    cols = ["구분", "순위", "호기", "uph"]
    result = pd.concat([best_df, worst_df], ignore_index=True)

    if result.empty:
        return pd.DataFrame(columns=cols)

    return result[cols]

def fetch_itas_ranked_machines(
    db: DbConfig,
    process_name: str,
    selected_date: pd.Timestamp,
    rank_direction: str,
    top_n: int,
) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)

    order_sql = "DESC" if rank_direction == "best" else "ASC"

    query = f"""
    SELECT
        machine_no AS 호기,
        uph AS uph
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      AND work_date = %(work_date)s
      AND uph IS NOT NULL
    ORDER BY uph {order_sql} NULLS LAST, machine_no
    LIMIT %(top_n)s;
    """

    params = {
        "process_name": process_name,
        "work_date": selected_date.date(),
        "top_n": int(top_n),
    }

    df = read_sql_df(query, db, params=params)

    if not df.empty:
        df["uph"] = pd.to_numeric(df["uph"], errors="coerce")

    return df

def fetch_itas_process_name_candidates(db: DbConfig) -> list[str]:
    """
    ITAS DB에서 실제 process_name 후보 목록 조회
    """
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)

    query = f"""
    SELECT DISTINCT process_name
    FROM {schema_q}.{table_q}
    WHERE process_name IS NOT NULL
      AND TRIM(process_name) <> ''
    ORDER BY process_name;
    """

    df = read_sql_df(query, db)
    if df.empty:
        return []

    return (
        df["process_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .drop_duplicates()
        .tolist()
    )


def fetch_mes_customer_model_candidates(db: DbConfig) -> list[str]:
    """
    MES DB에서 전체 customer_model 후보 목록 조회
    """
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    SELECT DISTINCT customer_model
    FROM {schema_q}.{table_q}
    WHERE customer_model IS NOT NULL
      AND TRIM(customer_model) <> ''
    ORDER BY customer_model;
    """

    df = read_sql_df(query, db)
    if df.empty:
        return []

    return (
        df["customer_model"]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .drop_duplicates()
        .tolist()
    )


def normalize_for_candidate_match(text: str | None) -> str:
    """
    후보 매칭용 정규화
    목적:
    - 따옴표 제거
    - 공정/모델 제거
    - 소문자화
    - 다중 공백 제거
    - 테스트 -> test 같은 토큰 alias 치환
    """
    if not text:
        return ""

    text = str(text).strip()

    # 따옴표류 제거
    text = text.replace('"', ' ')
    text = text.replace("'", " ")
    text = text.replace("“", " ")
    text = text.replace("”", " ")
    text = text.replace("‘", " ")
    text = text.replace("’", " ")

    # 접미어 제거
    text = text.replace("공정", " ")
    text = text.replace("모델", " ")

    # 소문자화
    text = text.lower()

    # 범용 토큰 alias
    token_alias = {
        "테스트": "test",
    }
    for src, dst in token_alias.items():
        text = text.replace(src, dst)

    # 특수문자 일부 공백화
    text = re.sub(r"[_/\\\-]+", " ", text)

    # 공백 정리
    text = " ".join(text.split())

    return text.strip()


def match_best_candidate(raw_value: str | None, candidates: list[str]) -> str | None:
    """
    raw_value를 candidates 중 실제 DB 값으로 매핑
    규칙:
    1. 완전일치
    2. 대소문자 무시 일치
    3. 정규화 exact match
    일치 없으면 원래값 반환
    """
    if not raw_value:
        return raw_value

    raw_value = str(raw_value).strip()
    if not candidates:
        return raw_value

    # 1) 완전일치
    for candidate in candidates:
        if raw_value == candidate:
            return candidate

    # 2) 대소문자 무시 일치
    raw_lower = raw_value.lower()
    for candidate in candidates:
        if raw_lower == str(candidate).lower():
            return candidate

    # 3) 정규화 exact match
    raw_norm = normalize_for_candidate_match(raw_value)
    normalized_map = {}

    for candidate in candidates:
        norm = normalize_for_candidate_match(candidate)
        if norm and norm not in normalized_map:
            normalized_map[norm] = candidate

    if raw_norm in normalized_map:
        return normalized_map[raw_norm]

    return raw_value

def tokenize_for_candidate_match(text: str | None) -> list[str]:
    """
    후보 매칭용 토큰 분리
    """
    normalized = normalize_for_candidate_match(text)
    if not normalized:
        return []
    return [tok for tok in normalized.split() if tok]


def compute_candidate_match_score(raw_value: str | None, candidate: str) -> float:
    """
    입력값과 후보 간 토큰 기반 점수 계산
    score = 0.7 * recall + 0.3 * precision

    recall    = 겹치는 토큰 수 / 입력 토큰 수
    precision = 겹치는 토큰 수 / 후보 토큰 수
    """
    raw_tokens = tokenize_for_candidate_match(raw_value)
    cand_tokens = tokenize_for_candidate_match(candidate)

    if not raw_tokens or not cand_tokens:
        return 0.0

    raw_set = set(raw_tokens)
    cand_set = set(cand_tokens)

    overlap = raw_set.intersection(cand_set)
    overlap_count = len(overlap)

    if overlap_count == 0:
        return 0.0

    recall = overlap_count / len(raw_set)
    precision = overlap_count / len(cand_set)

    score = 0.7 * recall + 0.3 * precision
    return round(score, 6)


def rank_candidate_matches(raw_value: str | None, candidates: list[str], top_k: int = 5) -> list[dict]:
    """
    후보별 점수 계산 후 상위 top_k 반환
    반환 예:
    [
        {"candidate": "APS Test", "score": 1.0},
        {"candidate": "APS Final Test", "score": 0.766667},
    ]
    """
    if not raw_value or not candidates:
        return []

    scored = []
    for candidate in candidates:
        score = compute_candidate_match_score(raw_value, candidate)
        if score > 0:
            scored.append({
                "candidate": candidate,
                "score": score,
            })

    scored.sort(key=lambda x: (-x["score"], x["candidate"]))
    return scored[:top_k]


def resolve_process_candidate(raw_value: str | None, candidates: list[str]) -> dict:
    """
    공정명 후보를 실제 DB 후보와 매칭

    반환 예시:
    {
        "status": "resolved",
        "matched_value": "APS Test",
        "candidates": [...]
    }

    또는

    {
        "status": "need_clarification",
        "matched_value": None,
        "candidates": [...]
    }
    """
    if not raw_value:
        return {
            "status": "not_found",
            "matched_value": None,
            "candidates": [],
        }

    # 후보 자체가 1개뿐이면 자동 선택
    if len(candidates) == 1:
        return {
            "status": "resolved",
            "matched_value": candidates[0],
            "candidates": [{"candidate": candidates[0], "score": 1.0}],
        }

    # 1) 기존 exact/normalized exact 우선
    exact = match_best_candidate(raw_value, candidates)
    if exact in candidates:
        return {
            "status": "resolved",
            "matched_value": exact,
            "candidates": [{"candidate": exact, "score": 1.0}],
        }

    # 2) fuzzy ranking
    ranked = rank_candidate_matches(raw_value, candidates, top_k=5)

    if not ranked:
        return {
            "status": "not_found",
            "matched_value": None,
            "candidates": [],
        }

    # 점수 있는 후보가 1개만 있으면 자동 선택
    if len(ranked) == 1:
        return {
            "status": "resolved",
            "matched_value": ranked[0]["candidate"],
            "candidates": ranked,
        }

    top1 = ranked[0]
    top2 = ranked[1] if len(ranked) > 1 else None

    top1_score = top1["score"]
    top2_score = top2["score"] if top2 else 0.0
    gap = top1_score - top2_score

    # 자동 선택 기준
    # - 최고 점수 >= 0.80
    # - 차점 대비 0.15 이상 우세
    if top1_score >= 0.80 and gap >= 0.15:
        return {
            "status": "resolved",
            "matched_value": top1["candidate"],
            "candidates": ranked,
        }

    # 후보 제시 기준
    # - 최고 점수 >= 0.50 이면 후보 선택 유도
    if top1_score >= 0.50:
        return {
            "status": "need_clarification",
            "matched_value": None,
            "candidates": ranked,
        }

    return {
        "status": "not_found",
        "matched_value": None,
        "candidates": ranked,
    }

def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def load_db_config() -> DbConfig:
    return DbConfig(
        host=os.getenv('ITAS_DB_HOST', DEFAULT_DB_HOST),
        port=int(os.getenv('ITAS_DB_PORT', DEFAULT_DB_PORT)),
        dbname=os.getenv('ITAS_DB_NAME', DEFAULT_DB_NAME),
        user=os.getenv('ITAS_DB_USER', DEFAULT_DB_USER),
        password=os.getenv('ITAS_DB_PASSWORD', DEFAULT_DB_PASSWORD),
        schema=os.getenv('ITAS_DB_SCHEMA', DEFAULT_DB_SCHEMA),
    )


def load_mes_db_config(config_path: str = 'setting.ini') -> DbConfig:
    base = load_db_config()

    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding='utf-8')

    section = cfg['config'] if 'config' in cfg else {}
    mes_name = section.get('mes_db_name', os.getenv('MES_DB_NAME', DEFAULT_MES_DB_NAME))

    return DbConfig(
        host=base.host,
        port=base.port,
        dbname=mes_name,
        user=base.user,
        password=base.password,
        schema=base.schema,
    )

def resolve_process_candidate_with_rewrites(
    raw_value: str | None,
    candidates: list[str],
    rewrite_candidates: list[str] | None = None,
) -> dict:
    """
    1차: raw_value 자체로 resolve_process_candidate 시도
    2차: rewrite_candidates가 있으면 각 rewrite로 재시도
    가장 좋은 결과를 반환
    """
    # 1차 시도
    primary = resolve_process_candidate(raw_value, candidates)
    if primary["status"] == "resolved":
        return primary

    rewrite_candidates = rewrite_candidates or []
    if not rewrite_candidates:
        return primary

    best_result = primary
    best_score = 0.0

    # primary 후보 점수 참고
    if primary.get("candidates"):
        best_score = max(item.get("score", 0.0) for item in primary["candidates"])

    for rewrite in rewrite_candidates:
        trial = resolve_process_candidate(rewrite, candidates)

        if trial["status"] == "resolved":
            return trial

        if trial.get("candidates"):
            trial_best_score = max(item.get("score", 0.0) for item in trial["candidates"])
            if trial_best_score > best_score:
                best_result = trial
                best_score = trial_best_score

    return best_result

def get_db_connection(db: DbConfig):
    conn = psycopg2.connect(
        host=db.host,
        port=db.port,
        dbname=db.dbname,
        user=db.user,
        password=db.password,
        connect_timeout=10,
        application_name='LLM_UPH_ReadOnly',
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn


def read_sql_df(query: str, db: DbConfig, params: Optional[dict] = None) -> pd.DataFrame:
    conn = get_db_connection(db)
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def normalize_process_name(name: str | None) -> str | None:
    if not name:
        return name
    name = str(name).strip()
    name = name.replace("공정", "").strip()
    return name


def normalize_customer_model(name: str | None) -> str | None:
    if not name:
        return name
    return str(name).strip()


def _mes_customer_model_condition(customer_model: str | None) -> tuple[str, dict]:
    customer_model = normalize_customer_model(customer_model)
    if customer_model:
        return " AND customer_model = %(customer_model)s ", {"customer_model": customer_model}
    return "", {}


# =========================================================
# ITAS
# =========================================================
def fetch_itas_latest_date(db: DbConfig):
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)
    q = f"SELECT MAX(work_date) AS latest_date FROM {schema_q}.{table_q};"
    df = read_sql_df(q, db)
    if df.empty or pd.isna(df['latest_date'].iloc[0]):
        return None
    return pd.to_datetime(df['latest_date'].iloc[0]).normalize()


def fetch_itas_uph_day(db: DbConfig, process_name: str, selected_date: pd.Timestamp) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)

    query = f"""
    SELECT
        work_date AS 날짜,
        process_name AS 공정명,
        machine_no AS 호기,
        uph AS uph
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      AND work_date = %(work_date)s
    ORDER BY machine_no;
    """
    df = read_sql_df(
        query,
        db,
        params={'process_name': process_name, 'work_date': selected_date.date()},
    )

    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.normalize()
        df['uph'] = pd.to_numeric(df['uph'], errors='coerce')

    return df


def fetch_itas_uph_trend(db: DbConfig, process_name: str, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)

    query = f"""
    SELECT
        work_date AS 날짜,
        AVG(uph) AS uph,
        CASE WHEN MAX(uph) > 0 THEN 1 - (AVG(uph) / MAX(uph)) END AS uph_deviation_rate,
        (MAX(uph) - MIN(uph)) AS bestworst_gap
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY work_date
    ORDER BY work_date;
    """
    df = read_sql_df(
        query,
        db,
        params={
            'process_name': process_name,
            'start_date': start_date.date(),
            'end_date': end_date.date(),
        },
    )

    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.normalize()
        for col in ['uph', 'uph_deviation_rate', 'bestworst_gap']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def fetch_itas_uph_machine_trend(
    db: DbConfig,
    process_name: str,
    machine_no: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)

    query = f"""
    SELECT
        work_date AS 날짜,
        machine_no AS 호기,
        uph AS uph
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      AND machine_no = %(machine_no)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    ORDER BY work_date;
    """
    df = read_sql_df(
        query,
        db,
        params={
            'process_name': process_name,
            'machine_no': str(machine_no),
            'start_date': start_date.date(),
            'end_date': end_date.date(),
        },
    )

    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.normalize()
        df['uph'] = pd.to_numeric(df['uph'], errors='coerce')

    return df


def fetch_itas_best_worst_machine(db: DbConfig, process_name: str, selected_date: pd.Timestamp):
    process_name = normalize_process_name(process_name)
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(ITAS_UPH_TABLE)

    query = f"""
    WITH ranked AS (
        SELECT
            machine_no,
            uph,
            ROW_NUMBER() OVER (ORDER BY uph DESC NULLS LAST, machine_no) AS rn_best,
            ROW_NUMBER() OVER (ORDER BY uph ASC NULLS LAST, machine_no) AS rn_worst
        FROM {schema_q}.{table_q}
        WHERE process_name = %(process_name)s
          AND work_date = %(work_date)s
          AND uph IS NOT NULL
    )
    SELECT
        MAX(CASE WHEN rn_best = 1 THEN machine_no END) AS best_machine,
        MAX(CASE WHEN rn_worst = 1 THEN machine_no END) AS worst_machine
    FROM ranked;
    """
    df = read_sql_df(
        query,
        db,
        params={'process_name': process_name, 'work_date': selected_date.date()},
    )

    if df.empty:
        return None, None

    best_machine = df.iloc[0]['best_machine']
    worst_machine = df.iloc[0]['worst_machine']

    return (
        str(best_machine) if pd.notna(best_machine) else None,
        str(worst_machine) if pd.notna(worst_machine) else None,
    )


# =========================================================
# MES
# =========================================================
def fetch_mes_latest_date(db: DbConfig):
    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)
    q = f"SELECT MAX(work_date) AS latest_date FROM {schema_q}.{table_q};"
    df = read_sql_df(q, db)
    if df.empty or pd.isna(df['latest_date'].iloc[0]):
        return None
    return pd.to_datetime(df['latest_date'].iloc[0]).normalize()


def fetch_mes_uph_day(db: DbConfig, process_name: str, selected_date: pd.Timestamp, customer_model: str | None = None) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)
    model_sql, model_params = _mes_customer_model_condition(customer_model)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    SELECT
        work_date AS 날짜,
        process_name AS 공정명,
        customer_model AS 모델,
        equipment_name AS 호기,
        SUM(uph) AS uph
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      {model_sql}
      AND work_date = %(work_date)s
    GROUP BY work_date, process_name, customer_model, equipment_name
    ORDER BY equipment_name;
    """

    params = {
        'process_name': process_name,
        'work_date': selected_date.date(),
    }
    params.update(model_params)

    df = read_sql_df(query, db, params=params)

    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.normalize()
        df['uph'] = pd.to_numeric(df['uph'], errors='coerce')

    return df


def fetch_mes_uph_trend(db: DbConfig, process_name: str, start_date: pd.Timestamp, end_date: pd.Timestamp, customer_model: str | None = None) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)
    model_sql, model_params = _mes_customer_model_condition(customer_model)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    SELECT
        work_date AS 날짜,
        AVG(uph) AS uph,
        CASE WHEN MAX(uph) > 0 THEN 1 - (AVG(uph) / MAX(uph)) END AS uph_deviation_rate,
        (MAX(uph) - MIN(uph)) AS bestworst_gap
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      {model_sql}
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY work_date
    ORDER BY work_date;
    """

    params = {
        'process_name': process_name,
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    }
    params.update(model_params)

    df = read_sql_df(query, db, params=params)

    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.normalize()
        for col in ['uph', 'uph_deviation_rate', 'bestworst_gap']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    return df


def fetch_mes_uph_machine_trend(
    db: DbConfig,
    process_name: str,
    machine_no: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    customer_model: str | None = None,
) -> pd.DataFrame:
    process_name = normalize_process_name(process_name)
    model_sql, model_params = _mes_customer_model_condition(customer_model)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    SELECT
        work_date AS 날짜,
        equipment_name AS 호기,
        SUM(uph) AS uph
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      {model_sql}
      AND equipment_name = %(machine_no)s
      AND work_date BETWEEN %(start_date)s AND %(end_date)s
    GROUP BY work_date, equipment_name
    ORDER BY work_date;
    """

    params = {
        'process_name': process_name,
        'machine_no': str(machine_no),
        'start_date': start_date.date(),
        'end_date': end_date.date(),
    }
    params.update(model_params)

    df = read_sql_df(query, db, params=params)

    if not df.empty:
        df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce').dt.normalize()
        df['uph'] = pd.to_numeric(df['uph'], errors='coerce')

    return df


def fetch_mes_best_worst_machine(db: DbConfig, process_name: str, selected_date: pd.Timestamp, customer_model: str | None = None):
    process_name = normalize_process_name(process_name)
    model_sql, model_params = _mes_customer_model_condition(customer_model)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    WITH machine_uph AS (
        SELECT
            equipment_name AS machine_no,
            SUM(uph) AS uph
        FROM {schema_q}.{table_q}
        WHERE process_name = %(process_name)s
          {model_sql}
          AND work_date = %(work_date)s
          AND uph IS NOT NULL
        GROUP BY equipment_name
    ),
    ranked AS (
        SELECT
            machine_no,
            uph,
            ROW_NUMBER() OVER (ORDER BY uph DESC NULLS LAST, machine_no) AS rn_best,
            ROW_NUMBER() OVER (ORDER BY uph ASC NULLS LAST, machine_no) AS rn_worst
        FROM machine_uph
    )
    SELECT
        MAX(CASE WHEN rn_best = 1 THEN machine_no END) AS best_machine,
        MAX(CASE WHEN rn_worst = 1 THEN machine_no END) AS worst_machine
    FROM ranked;
    """

    params = {
        'process_name': process_name,
        'work_date': selected_date.date(),
    }
    params.update(model_params)

    df = read_sql_df(query, db, params=params)

    if df.empty:
        return None, None

    best_machine = df.iloc[0]['best_machine']
    worst_machine = df.iloc[0]['worst_machine']

    return (
        str(best_machine) if pd.notna(best_machine) else None,
        str(worst_machine) if pd.notna(worst_machine) else None,
    )

def fetch_mes_customer_model_stats_by_process(db: DbConfig, process_name: str) -> list[dict]:
    """
    특정 공정명에 연결된 customer_model 후보 목록 + 건수 + 최신일 조회
    - row_count 내림차순 정렬
    - row_count <= 0 인 후보 제외
    반환 예:
    [
        {"customer_model": "ABC123", "row_count": 1520, "latest_date": "2026-04-22"},
        {"customer_model": "XYZ999", "row_count": 380, "latest_date": "2026-04-21"},
    ]
    """
    process_name = normalize_process_name(process_name)

    schema_q = quote_ident(db.schema)
    table_q = quote_ident(MES_UPH_TABLE)

    query = f"""
    SELECT
        customer_model,
        COUNT(*) AS row_count,
        MAX(work_date) AS latest_date
    FROM {schema_q}.{table_q}
    WHERE process_name = %(process_name)s
      AND customer_model IS NOT NULL
      AND TRIM(customer_model) <> ''
    GROUP BY customer_model
    HAVING COUNT(*) > 0
    ORDER BY COUNT(*) DESC, MAX(work_date) DESC, customer_model;
    """

    df = read_sql_df(query, db, params={"process_name": process_name})

    if df.empty:
        return []

    df["customer_model"] = df["customer_model"].astype(str).str.strip()
    df["row_count"] = pd.to_numeric(df["row_count"], errors="coerce").fillna(0).astype(int)
    df["latest_date"] = pd.to_datetime(df["latest_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # row_count <= 0 제거 + 빈 문자열 제거
    df = df[
        (df["customer_model"] != "") &
        (df["row_count"] > 0)
    ].copy()

    if df.empty:
        return []

    return df.to_dict(orient="records")