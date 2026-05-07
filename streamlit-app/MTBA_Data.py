import os
import sys
import csv
import html
import time as tm
import traceback
import subprocess
from pathlib import Path
from datetime import datetime, time

import win32com.client
import pandas as pd
import numpy as np


# ===================== 사용자 설정 =====================
KEYWORDS = ["Alarm_count", "Run_Time", "Production"]   # 제목/본문에 포함될 키워드
MATCH_MODE = "any"                                     # "any" 또는 "all"
SAVE_DIR = r"D:\PythonProject\Project\MTBA_Streamlit/Data"
MASTER_DIR = r"D:\PythonProject\Project\MTBA_Streamlit/Master_Data"

SEARCH_IN = "subject_body"                             # "subject" 또는 "subject_body"
INCLUDE_SUBFOLDERS = False
MARK_AS_READ = False
OPEN_MAIL = False
TARGET_FOLDER_PATH = None
# 예: ["받은 편지함", "업무", "보고서"]

# ===== 스케줄 설정 =====
RUN_TIMES = ["08:15"]               # 여러 개 가능
RUN_ON_START = False                               # 시작 즉시 1회 실행 여부
CHECK_INTERVAL_SECONDS = 15                           # 몇 초마다 현재 시간 확인할지

# ===== 후속 py 실행 설정 =====
NEXT_PY_FILES = [
    r"D:\PythonProject\Project\MTBA_Streamlit/ETL/load_to_postgres.py"
]
RUN_NEXT_ONLY_IF_SUCCESS = True                       # main_work 성공 시에만 후속 실행
STOP_CHAIN_ON_ERROR = True                            # 후속 py 여러 개일 때 하나 실패하면 그 체인 중단
# ======================================================


def ensure_save_dir(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def normalize_keywords(keywords):
    """
    - 리스트/튜플: 그대로 사용
    - 문자열: 쉼표(,) 또는 공백 기준 분리
    - 모두 소문자/공백 트림, 빈 문자열 제거
    """
    if keywords is None:
        return []

    if isinstance(keywords, (list, tuple, set)):
        raw = list(keywords)
    elif isinstance(keywords, str):
        sep = "," if "," in keywords else None
        raw = keywords.split(sep)
    else:
        raw = [str(keywords)]

    cleaned = []
    for k in raw:
        k = (k or "").strip().lower()
        if k:
            cleaned.append(k)
    return cleaned


def get_outlook_inbox(target_folder_path=None):
    """
    target_folder_path가 None이면 기본 받은편지함 반환.
    그렇지 않으면 ["받은 편지함", "서브폴더", ...] 경로 탐색.
    """
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    if target_folder_path is None:
        return outlook.GetDefaultFolder(6)  # olFolderInbox

    root = outlook.Folders.Item(1)
    folder = root
    for name in target_folder_path:
        folder = folder.Folders.Item(name)
    return folder


def get_items_today(folder):
    """
    오늘 날짜 메일만 Restrict로 필터링.
    """
    items = folder.Items
    items.IncludeRecurrences = True
    items.Sort("[ReceivedTime]", True)

    today = datetime.now().date()
    start_dt = datetime.combine(today, time.min)
    end_dt = datetime.combine(today, time.max)

    start_str = start_dt.strftime("%m/%d/%Y %H:%M")
    end_str = end_dt.strftime("%m/%d/%Y %H:%M")

    restriction = f"[ReceivedTime] >= '{start_str}' AND [ReceivedTime] <= '{end_str}'"

    try:
        filtered = items.Restrict(restriction)
    except Exception:
        start_str = start_dt.strftime("%m/%d/%Y %I:%M %p")
        end_str = end_dt.strftime("%m/%d/%Y %I:%M %p")
        restriction = f"[ReceivedTime] >= '{start_str}' AND [ReceivedTime] <= '{end_str}'"
        filtered = items.Restrict(restriction)

    return filtered


def iter_all_items(folder, include_subfolders=False):
    """
    폴더 내 모든 메일(옵션에 따라 하위 폴더 포함) 순회
    """
    for item in get_items_today(folder):
        yield item

    if include_subfolders:
        for sub in folder.Folders:
            yield from iter_all_items(sub, include_subfolders=True)


def is_match(item, keywords, search_in: str = "subject", match_mode: str = "any") -> bool:
    """
    - keywords: 리스트/문자열 모두 허용
    - search_in: "subject" 또는 "subject_body"
    - match_mode: "any" 또는 "all"
    """
    kw_list = normalize_keywords(keywords)
    if not kw_list:
        return False

    try:
        subject = item.Subject or ""
    except Exception:
        subject = ""

    subject_l = subject.lower()

    body_l = ""
    if search_in != "subject":
        try:
            body_l = (item.Body or "").lower()
        except Exception:
            body_l = ""

    haystack = subject_l if search_in == "subject" else (subject_l + "\n" + body_l)

    presence = [(kw in haystack) for kw in kw_list]
    return all(presence) if match_mode.lower() == "all" else any(presence)


def unique_path(save_dir: Path, filename: str) -> Path:
    """
    중복 파일명이 있을 경우 _1, _2 붙여 고유 경로 생성
    """
    base = save_dir / filename
    if not base.exists():
        return base

    stem = base.stem
    suffix = base.suffix
    idx = 1
    while True:
        candidate = save_dir / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def save_attachments_from_item(item, save_dir: Path) -> int:
    """
    메일의 모든 첨부파일 저장
    """
    count = 0
    try:
        attachments = item.Attachments
        for i in range(1, attachments.Count + 1):
            att = attachments.Item(i)
            filename = att.FileName
            target = unique_path(save_dir, filename)
            att.SaveAsFile(str(target))
            print(f"[첨부 저장] {target}")
            count += 1
    except Exception as e:
        print(f"[경고] 첨부 저장 중 오류: {e}")
    return count


def find_latest_file(save_dir: str, contains_keywords, exts=(".csv", ".txt")) -> str:
    """
    SAVE_DIR 안에서 특정 키워드를 포함하는 가장 최신 파일 경로 반환
    """
    folder = Path(save_dir)
    if not folder.exists():
        raise FileNotFoundError(f"SAVE_DIR가 존재하지 않습니다: {save_dir}")

    keywords = [str(k).lower().strip() for k in contains_keywords if str(k).strip()]
    candidates = []

    for p in folder.iterdir():
        if not p.is_file():
            continue

        if p.suffix.lower() not in exts:
            continue

        name_l = p.name.lower()
        if all(k in name_l for k in keywords):
            candidates.append(p)

    if not candidates:
        raise FileNotFoundError(
            f"다음 키워드를 포함하는 파일을 찾지 못했습니다: {contains_keywords}\n경로: {save_dir}"
        )

    latest = max(candidates, key=lambda x: x.stat().st_mtime)
    print(f"[최신 파일 선택] keywords={contains_keywords} -> {latest}")
    return str(latest)


def read_csv_with_header_detection(file_path, expected_cols, title_candidates=None, debug_name="CSV"):
    """
    CSV 파일을 안전하게 로드:
    - 여러 인코딩 순차 시도
    - 제목 줄(MTBA_xxx, MTBA_xxx(Test)) 자동 제거
    - 헤더 행 자동 탐지
    - 불량 행 제외
    """
    title_candidates = set(title_candidates or [])
    encodings = ["utf-16", "utf-8-sig", "cp949", "euc-kr", "utf-8"]
    errors = []

    expected_norm = [str(x).strip().replace("\ufeff", "") for x in expected_cols]

    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc, newline="") as f:
                raw_lines = f.read().splitlines()

            raw_lines = [line for line in raw_lines if str(line).strip()]
            if not raw_lines:
                raise ValueError("파일이 비어 있습니다.")

            parsed_lines = []
            for line in raw_lines:
                cleaned = str(line).strip().replace("\ufeff", "")
                if cleaned in title_candidates:
                    continue

                row = next(csv.reader([line], delimiter=",", quotechar='"'))
                row = [html.unescape(str(x).strip().replace("\ufeff", "")) for x in row]

                if not any(str(x).strip() for x in row):
                    continue

                parsed_lines.append(row)

            header_idx = None
            for idx, row in enumerate(parsed_lines):
                if [str(x).strip() for x in row] == expected_norm:
                    header_idx = idx
                    break

            if header_idx is None:
                preview = parsed_lines[:5]
                raise ValueError(
                    f"[{enc}] 헤더를 찾지 못했습니다. 상위 5개 행 미리보기: {preview}"
                )

            data_rows = []
            bad_rows = []

            for row_no, row in enumerate(parsed_lines[header_idx + 1:], start=header_idx + 2):
                if len(row) == 1 and "," in str(row[0]):
                    row = next(csv.reader([row[0]], delimiter=",", quotechar='"'))
                    row = [html.unescape(str(x).strip().replace("\ufeff", "")) for x in row]

                if len(row) < len(expected_norm):
                    row = row + [None] * (len(expected_norm) - len(row))
                elif len(row) > len(expected_norm):
                    bad_rows.append((row_no, len(row), row))
                    continue

                data_rows.append(row)

            if not data_rows:
                raise ValueError(
                    f"[{enc}] 헤더는 찾았지만 데이터 행이 없습니다. bad_rows 예시: {bad_rows[:3]}"
                )

            df = pd.DataFrame(data_rows, columns=expected_norm)

            print(f"[{debug_name}] 사용 인코딩: {enc}")
            print(f"[{debug_name}] 헤더 탐지 성공")
            return df, enc

        except Exception as e:
            errors.append(str(e))

    raise ValueError(
        f"{debug_name} 파일을 정상적으로 읽지 못했습니다.\n" + "\n".join(errors)
    )


def Alram_count():
    """
    1) 최신 Alarm_count 파일 로드
    2) Master 2개 파일 병합하여 Master_Result 생성
    3) 알람 원본 집계
    4) Master 기준 필터링
    5) 설비별/날짜별 최종 알람발생건수 집계
    """

    alarm_file = find_latest_file(SAVE_DIR, ["alarm_count"])

    alarm_expected_cols = [
        "사업부",
        "제품군",
        "공장",
        "영역",
        "공정",
        "설비",
        "알람발생마감년월일",
        "알람코드",
        "알람내용(무시기준적용후2)",
        "알람발생건수"
    ]

    df_Alram_count_raw, _ = read_csv_with_header_detection(
        alarm_file,
        expected_cols=alarm_expected_cols,
        title_candidates={"MTBA_Alarm_count", "MTBA_Alarm_count(Test)"},
        debug_name="Alarm_count"
    )

    df_MasterData1 = pd.read_excel(
        f"{MASTER_DIR}/MTBA Alarm 포함여부(모델구분).xlsx",
        engine="openpyxl",
        sheet_name="알람명(코드포함)"
    )
    df_MasterData2 = pd.read_excel(
        f"{MASTER_DIR}/MTBA Alarm 포함여부(등급횟수 포함).xlsx",
        engine="openpyxl",
        sheet_name="알람명(코드포함)"
    )

    # -------------------------------------------------
    # 1. Master 병합
    # -------------------------------------------------
    key_cols = ["공장ID", "공정ID", "공정", "알람코드"]

    A = df_MasterData1.copy()
    B = df_MasterData2.copy()

    A.columns = A.columns.str.strip()
    B.columns = B.columns.str.strip()

    A["알람코드"] = pd.to_numeric(A["알람코드"], errors="coerce")
    B["알람코드"] = pd.to_numeric(B["알람코드"], errors="coerce")

    B_sub = B[key_cols + ["중요등급"]].drop_duplicates(subset=key_cols)

    Master_result = A.merge(B_sub, on=key_cols, how="left", suffixes=("", "_B"))

    # 중요등급 dtype warning 방지
    if "중요등급" not in Master_result.columns:
        Master_result["중요등급"] = pd.Series([pd.NA] * len(Master_result), dtype="object")
    else:
        Master_result["중요등급"] = Master_result["중요등급"].astype("object")

    if "중요등급_B" in Master_result.columns:
        Master_result["중요등급_B"] = Master_result["중요등급_B"].astype("object")

        mask = Master_result["중요등급"].isna() | (
            Master_result["중요등급"].astype(str).str.strip() == ""
        )

        Master_result.loc[mask, "중요등급"] = Master_result.loc[mask, "중요등급_B"]
        Master_result = Master_result.drop(columns=["중요등급_B"])

    Master_result.to_excel(f"{SAVE_DIR}/Master_Result.xlsx", index=False)

    # -------------------------------------------------
    # 2. Alarm 원본 전처리
    # -------------------------------------------------
    df_Alram_count_raw.columns = df_Alram_count_raw.columns.str.strip()

    if "알람발생마감년월일" in df_Alram_count_raw.columns and "날짜" not in df_Alram_count_raw.columns:
        df_Alram_count_raw = df_Alram_count_raw.rename(columns={"알람발생마감년월일": "날짜"})

    use_cols = [
        "제품군",
        "공장",
        "공정",
        "설비",
        "날짜",
        "알람코드",
        "알람내용(무시기준적용후2)",
        "알람발생건수"
    ]

    missing = [c for c in use_cols if c not in df_Alram_count_raw.columns]
    if missing:
        raise KeyError(f"Alarm 원본에 필요한 컬럼이 없습니다: {missing}")

    df_Alram_count = df_Alram_count_raw[use_cols].copy()

    df_Alram_count["날짜"] = pd.to_datetime(df_Alram_count["날짜"], errors="coerce")
    df_Alram_count["알람코드"] = pd.to_numeric(df_Alram_count["알람코드"], errors="coerce")
    df_Alram_count["알람발생건수"] = pd.to_numeric(
        df_Alram_count["알람발생건수"], errors="coerce"
    ).fillna(0)

    for col in ["제품군", "공장", "공정", "설비", "알람내용(무시기준적용후2)"]:
        df_Alram_count[col] = df_Alram_count[col].astype(str).str.strip()

    # -------------------------------------------------
    # 3. 설비+날짜+알람코드+알람내용 기준 집계
    # -------------------------------------------------
    Alram_result = (
        df_Alram_count.groupby(
            ["제품군", "공장", "공정", "설비", "날짜", "알람코드", "알람내용(무시기준적용후2)"],
            as_index=False
        )["알람발생건수"]
        .sum()
    )

    Alram_result = Alram_result.sort_values(
        by=["설비", "알람내용(무시기준적용후2)", "날짜"],
        ascending=[True, True, True]
    ).reset_index(drop=True)

    Alram_result.to_excel(f"{SAVE_DIR}/alarm_count_raw.xlsx", index=False)

    # -------------------------------------------------
    # 4. Master 기준 필터링
    # -------------------------------------------------
    alarm = Alram_result.copy()
    master = Master_result.copy()

    alarm.columns = alarm.columns.str.strip()
    master.columns = master.columns.str.strip()

    alarm["공정"] = alarm["공정"].astype(str).str.strip()
    master["공정"] = master["공정"].astype(str).str.strip()

    alarm["알람코드"] = pd.to_numeric(alarm["알람코드"], errors="coerce")
    master["알람코드"] = pd.to_numeric(master["알람코드"], errors="coerce")

    master_sub = (
        master[["공정", "알람코드", "Model", "중요등급"]]
        .dropna(subset=["공정", "알람코드"])
        .drop_duplicates(subset=["공정", "알람코드"])
    )

    filtered_alarm = alarm.merge(
        master_sub,
        on=["공정", "알람코드"],
        how="inner",
        sort=False
    )

    filtered_alarm.to_excel(f"{SAVE_DIR}/alarm_count_filter.xlsx", index=False)

    # -------------------------------------------------
    # 5. 설비별 / 날짜별 최종 알람발생건수 집계
    # -------------------------------------------------
    filtered_alarm["날짜"] = pd.to_datetime(filtered_alarm["날짜"], errors="coerce")
    filtered_alarm["알람발생건수"] = pd.to_numeric(
        filtered_alarm["알람발생건수"], errors="coerce"
    ).fillna(0)

    for col in ["제품군", "공장", "공정", "설비"]:
        filtered_alarm[col] = filtered_alarm[col].astype(str).str.strip()

    alarm_by_eq_date = (
        filtered_alarm.groupby(
            ["제품군", "공장", "공정", "설비", "날짜"],
            as_index=False
        )["알람발생건수"]
        .sum()
        .sort_values(["제품군", "공장", "공정", "설비", "날짜"])
        .reset_index(drop=True)
    )

    alarm_by_eq_date.to_excel(f"{SAVE_DIR}/alarm_count_filter_sum.xlsx", index=False)

    return alarm_by_eq_date


def Runtime_sum():
    """
    최신 Run_time 파일을 읽어서
    설비별 / 날짜별 RunTime(분) 합계를 집계
    """

    file_path = find_latest_file(SAVE_DIR, ["run_time"])

    expected_cols = [
        "사업부",
        "제품군",
        "공장",
        "영역",
        "공정",
        "설비",
        "설비상태이전코드",
        "설비상태변경마감년월일",
        "설비상태변경소요시간(분)"
    ]

    df_Run_time, _ = read_csv_with_header_detection(
        file_path,
        expected_cols=expected_cols,
        title_candidates={"MTBA_Run_time", "MTBA_Run_time(Test)"},
        debug_name="Run_time"
    )

    df_Run_time.columns = (
        pd.Index(df_Run_time.columns)
        .astype(str)
        .str.strip()
        .str.replace("\ufeff", "", regex=False)
    )

    if "설비상태변경마감년월일" in df_Run_time.columns and "날짜" not in df_Run_time.columns:
        df_Run_time = df_Run_time.rename(columns={"설비상태변경마감년월일": "날짜"})
        print("[Runtime_sum] 날짜 컬럼명 변경 완료")

    use_cols = [
        "제품군",
        "공장",
        "공정",
        "설비",
        "날짜",
        "설비상태변경소요시간(분)"
    ]

    missing_cols = [col for col in use_cols if col not in df_Run_time.columns]
    if missing_cols:
        raise KeyError(
            f"필요 컬럼이 없습니다: {missing_cols}\n현재 컬럼: {df_Run_time.columns.tolist()}"
        )

    df_Run_time = df_Run_time[use_cols].copy()

    df_Run_time["날짜"] = pd.to_datetime(df_Run_time["날짜"], errors="coerce")
    df_Run_time["설비상태변경소요시간(분)"] = pd.to_numeric(
        df_Run_time["설비상태변경소요시간(분)"], errors="coerce"
    ).fillna(0)

    for col in ["제품군", "공장", "공정", "설비"]:
        df_Run_time[col] = df_Run_time[col].astype(str).str.strip()

    df_Run_time = df_Run_time.dropna(subset=["날짜"])
    df_Run_time = df_Run_time[df_Run_time["설비"].ne("")]

    Runtime_result = (
        df_Run_time.groupby(
            ["제품군", "공장", "공정", "설비", "날짜"],
            as_index=False
        )["설비상태변경소요시간(분)"]
        .sum()
        .sort_values(["제품군", "공장", "공정", "설비", "날짜"])
        .reset_index(drop=True)
    )

    Runtime_result["설비상태변경소요시간(분)"] = Runtime_result["설비상태변경소요시간(분)"].round(2)

    output_path = f"{SAVE_DIR}/Runtime_summary_by_date.xlsx"
    Runtime_result.to_excel(output_path, index=False)

    print(f"[Runtime_sum] 저장 완료: {output_path}")
    print(f"[Runtime_sum] 결과 건수: {len(Runtime_result):,}")

    return Runtime_result


def MTBA_result():
    """
    날짜 기준 설비별 MTBA 계산
    MTBA = 설비상태변경소요시간(분) / 알람발생건수
    단, 알람발생건수 = 0 이면 MTBA = 설비상태변경소요시간(분)
    """

    df_Alram_count = Alram_count()
    df_Run_time = Runtime_sum()

    df_Alram_count.columns = df_Alram_count.columns.str.strip()
    df_Run_time.columns = df_Run_time.columns.str.strip()

    alarm_use_cols = ["제품군", "공장", "공정", "설비", "날짜", "알람발생건수"]
    status_use_cols = ["제품군", "공장", "공정", "설비", "날짜", "설비상태변경소요시간(분)"]

    df_Alram_count = df_Alram_count[alarm_use_cols].copy()
    df_Run_time = df_Run_time[status_use_cols].copy()

    df_Alram_count["날짜"] = pd.to_datetime(df_Alram_count["날짜"], errors="coerce")
    df_Run_time["날짜"] = pd.to_datetime(df_Run_time["날짜"], errors="coerce")

    df_Alram_count["알람발생건수"] = pd.to_numeric(
        df_Alram_count["알람발생건수"], errors="coerce"
    ).fillna(0)

    df_Run_time["설비상태변경소요시간(분)"] = pd.to_numeric(
        df_Run_time["설비상태변경소요시간(분)"], errors="coerce"
    ).fillna(0)

    for col in ["제품군", "공장", "공정", "설비"]:
        df_Alram_count[col] = df_Alram_count[col].astype(str).str.strip()
        df_Run_time[col] = df_Run_time[col].astype(str).str.strip()

    alarm_summary = (
        df_Alram_count.groupby(
            ["제품군", "공장", "공정", "설비", "날짜"],
            as_index=False
        )["알람발생건수"]
        .sum()
    )

    status_summary = (
        df_Run_time.groupby(
            ["제품군", "공장", "공정", "설비", "날짜"],
            as_index=False
        )["설비상태변경소요시간(분)"]
        .sum()
    )

    mtba_df = pd.merge(
        status_summary,
        alarm_summary,
        on=["제품군", "공장", "공정", "설비", "날짜"],
        how="outer"
    )

    mtba_df["설비상태변경소요시간(분)"] = mtba_df["설비상태변경소요시간(분)"].fillna(0)
    mtba_df["알람발생건수"] = mtba_df["알람발생건수"].fillna(0)

    mtba_df["MTBA"] = np.where(
        mtba_df["알람발생건수"] > 0,
        mtba_df["설비상태변경소요시간(분)"] / mtba_df["알람발생건수"],
        mtba_df["설비상태변경소요시간(분)"]
    )

    mtba_df["설비상태변경소요시간(분)"] = mtba_df["설비상태변경소요시간(분)"].round(2)
    mtba_df["알람발생건수"] = mtba_df["알람발생건수"].round(0).astype("Int64")
    mtba_df["MTBA"] = mtba_df["MTBA"].round(2)

    mtba_df = mtba_df.sort_values(
        ["제품군", "공장", "공정", "설비", "날짜"]
    ).reset_index(drop=True)

    mtba_df["날짜"] = mtba_df["날짜"].dt.strftime("%Y-%m-%d")

    mtba_df.to_excel(f"{SAVE_DIR}/mtba_result.xlsx", index=False)

    print(f"[MTBA_result] 저장 완료: {SAVE_DIR}/mtba_result.xlsx")
    return mtba_df


def main_work():
    """
    실제 작업 본체:
    1) Outlook 첨부 저장
    2) MTBA 결과 생성
    """
    save_dir = ensure_save_dir(SAVE_DIR)
    inbox = get_outlook_inbox(TARGET_FOLDER_PATH)

    total_mails = 0
    total_files = 0

    for item in iter_all_items(inbox, INCLUDE_SUBFOLDERS):
        try:
            if getattr(item, "Class", None) != 43:   # 43 = olMail
                continue
        except Exception:
            continue

        try:
            if not is_match(item, KEYWORDS, SEARCH_IN, MATCH_MODE):
                continue

            total_mails += 1

            if OPEN_MAIL:
                item.Display(False)

            saved = save_attachments_from_item(item, save_dir)
            total_files += saved

            try:
                print(f"[메일 매칭] {item.Subject}")
            except Exception:
                print(item)

            if MARK_AS_READ:
                try:
                    item.UnRead = False
                    item.Save()
                except Exception:
                    pass

        except Exception as e:
            print(f"[경고] 메일 처리 중 오류: {e}")
            print(f"저장 경로: {save_dir}")
            continue

    print(f"[메일 처리 완료] 조건에 맞는 메일 {total_mails}개, 저장한 첨부파일 {total_files}개")

    MTBA_result()


def run_next_py_files(py_files):
    """
    후속 Python 파일들을 순서대로 실행
    - 현재 실행 중인 동일한 Python 인터프리터(가상환경) 사용
    - 실패해도 스케줄러 전체는 죽지 않음
    """
    if not py_files:
        print("[후속 실행] 실행할 후속 py 파일이 없습니다.")
        return True

    python_exe = sys.executable
    print(f"[후속 실행] Python 경로: {python_exe}")

    all_success = True

    for py_file in py_files:
        py_file = str(py_file).strip()
        if not py_file:
            continue

        if not os.path.exists(py_file):
            print(f"[후속 실행] 파일이 존재하지 않습니다: {py_file}")
            all_success = False
            if STOP_CHAIN_ON_ERROR:
                break
            continue

        print(f"[후속 실행 시작] {py_file}")

        try:
            result = subprocess.run(
                [python_exe, py_file],
                check=True,
                text=True
            )
            print(f"[후속 실행 완료] {py_file} / returncode={result.returncode}")

        except subprocess.CalledProcessError as e:
            print(f"[후속 실행 오류] {py_file} / returncode={e.returncode}")
            all_success = False
            if STOP_CHAIN_ON_ERROR:
                break

        except Exception as e:
            print(f"[후속 실행 예외] {py_file} / {e}")
            traceback.print_exc()
            all_success = False
            if STOP_CHAIN_ON_ERROR:
                break

    return all_success


def validate_run_times(run_times):
    """
    RUN_TIMES 형식 검증:
    - 'HH:MM' 형식인지
    - 중복 제거 및 정렬
    """
    if not run_times:
        raise ValueError("RUN_TIMES가 비어 있습니다. 최소 1개 이상의 시간을 설정하세요.")

    normalized = []
    for t in run_times:
        t = str(t).strip()
        try:
            datetime.strptime(t, "%H:%M")
        except ValueError:
            raise ValueError(f"잘못된 시간 형식입니다: {t} (예: '08:30', '18:00')")
        normalized.append(t)

    return sorted(set(normalized))


def run_job_safely():
    """
    1회 작업 실행:
    - main_work() 실행
    - 성공 시 후속 py 실행
    - 실패해도 예외를 밖으로 던지지 않음
    """
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 70)
    print(f"[스케줄 작업 시작] {start_time}")
    print("=" * 70)

    main_success = False

    try:
        main_work()
        main_success = True
        print("[메인 작업 완료] main_work() 정상 종료")
    except Exception as e:
        print(f"[메인 작업 오류] {e}")
        traceback.print_exc()

    try:
        if main_success:
            run_next_py_files(NEXT_PY_FILES)
        else:
            if RUN_NEXT_ONLY_IF_SUCCESS:
                print("[후속 실행 생략] main_work() 실패로 인해 후속 py 실행 안 함")
            else:
                print("[후속 실행 강행] main_work() 실패했지만 후속 py 실행 시도")
                run_next_py_files(NEXT_PY_FILES)
    except Exception as e:
        print(f"[후속 실행 처리 중 오류] {e}")
        traceback.print_exc()

    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 70)
    print(f"[스케줄 작업 종료] {end_time}")
    print("[상태] 다시 시간 대기 상태로 복귀합니다.")
    print("=" * 70 + "\n")


def run_scheduler(run_times, check_interval_seconds=15, run_on_start=False):
    """
    매일 반복 실행 스케줄러
    - 같은 날짜의 같은 시간은 1번만 실행
    - 작업 완료 후 다시 대기 상태로 복귀
    """
    run_times = validate_run_times(run_times)

    last_run_date = {t: None for t in run_times}

    print("==============================================")
    print("[스케줄러 시작]")
    print(f"실행 시간 목록: {run_times}")
    print(f"체크 주기(초): {check_interval_seconds}")
    print(f"시작 즉시 실행 여부: {run_on_start}")
    print("프로그램 종료: Ctrl + C")
    print("==============================================")

    if run_on_start:
        run_job_safely()

    try:
        while True:
            now = datetime.now()
            today = now.date()
            current_hm = now.strftime("%H:%M")

            for run_time in run_times:
                if current_hm == run_time and last_run_date[run_time] != today:
                    print(f"[실행 조건 충족] 현재시간={current_hm}, 예약시간={run_time}")
                    run_job_safely()
                    last_run_date[run_time] = today

            tm.sleep(check_interval_seconds)

    except KeyboardInterrupt:
        print("\n[스케줄러 종료] 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n[스케줄러 치명적 오류] {e}")
        traceback.print_exc()
        print("[스케줄러] 60초 후 자동 재시도합니다.")
        tm.sleep(60)
        run_scheduler(run_times, check_interval_seconds, run_on_start=False)


if __name__ == "__main__":
    run_scheduler(
        run_times=RUN_TIMES,
        check_interval_seconds=CHECK_INTERVAL_SECONDS,
        run_on_start=RUN_ON_START
    )