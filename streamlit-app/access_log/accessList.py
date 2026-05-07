import os
import sqlite3
import pandas as pd

# 현재 파일 기준 DB 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "access_logs.db")

# SQLite 연결
conn = sqlite3.connect(DB_PATH)

try:
    # access_log 테이블 전체 조회
    query = "SELECT * FROM access_log"
    df = pd.read_sql_query(query, conn)

    # 전체 출력 옵션
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", None)

    print(df)
    print(df["client_ip"].drop_duplicates().sort_values(ascending=False).reset_index(drop=True))

finally:
    conn.close()