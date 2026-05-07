from sqlalchemy import text
import pandas as pd


def ensure_alarm_whitelist_table(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mtba.alarm_whitelist (
                alarm_code   TEXT NOT NULL,
                alarm_name   TEXT NOT NULL,
                plant_code   TEXT NULL,
                process_code TEXT NULL,
                model_name   TEXT NULL,
                importance   TEXT NULL,
                PRIMARY KEY (alarm_code, alarm_name)
            )
        """))

def load_alarm_whitelist_from_excel(engine, excel_path: str):
    """
    기준 파일의 알람코드 + 알람명 세트를 DB whitelist 테이블에 적재
    - 알람코드는 유니크하다고 가정하되, 사용자의 요구대로 알람명도 함께 저장
    - 알람명/알람코드 둘 다 존재하는 행만 적재
    - Guide/설명 행 제거
    """
    df = pd.read_excel(excel_path, engine="openpyxl")

    # 컬럼명 정리
    df.columns = [str(c).strip() for c in df.columns]

    expected_cols = {
        "공장ID": "plant_code",
        "공정ID": "process_code",
        "알람코드": "alarm_code",
        "알람명": "alarm_name",
        "Model": "model_name",
        "중요등급": "importance",
    }

    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"엑셀에 필요한 컬럼이 없습니다: {missing}")

    df = df[list(expected_cols.keys())].rename(columns=expected_cols)

    # 공백 제거
    for col in ["plant_code", "process_code", "alarm_code", "alarm_name", "model_name", "importance"]:
        df[col] = df[col].astype(str).str.strip()

    # Guide / 설명 행 제거
    # 알람코드는 숫자형으로 해석 가능한 행만 유지
    df["alarm_code_num"] = pd.to_numeric(df["alarm_code"], errors="coerce")
    df = df[df["alarm_code_num"].notna()].copy()

    # 알람명 없는 행 제거
    df = df[df["alarm_name"].notna() & (df["alarm_name"] != "")].copy()

    # 최종 alarm_code는 문자열로 저장 (비교 일관성용)
    df["alarm_code"] = df["alarm_code_num"].astype("Int64").astype(str)

    df = df.drop(columns=["alarm_code_num"])

    # 중복 제거: 알람코드+알람명 세트 기준
    df = df.drop_duplicates(subset=["alarm_code", "alarm_name"]).reset_index(drop=True)

    ensure_alarm_whitelist_table(engine)

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE mtba.alarm_whitelist"))

    df.to_sql(
        "alarm_whitelist",
        engine,
        schema="mtba",
        if_exists="append",
        index=False,
        method="multi"
    )


from db import get_engine

engine = get_engine()
ensure_alarm_whitelist_table(engine)
load_alarm_whitelist_from_excel(engine, "D:/MTBA/MTBA_Streamlit/Master_Data/MTBA Alarm_Master_Data.xlsx")
