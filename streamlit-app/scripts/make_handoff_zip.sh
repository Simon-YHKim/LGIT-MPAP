#!/usr/bin/env bash
# make_handoff_zip.sh — 이전 엔지니어가 zip 으로 인수했던 것처럼,
# 현재 코드를 단일 zip 파일로 패키징.
#
# 출력: dist/LGIT-MPAP-vitals-<short_hash>-<YYYYMMDD>.zip
#
# 포함:
#   · streamlit-app/         — 실제 deploy 대상 (백엔드 + UI + scripts)
#   · streamlit-app/.streamlit/secrets.toml — 폐쇄망 정책상 포함
#   · docs/STAGE2_RELEASE_NOTES.md — 인수 인계 1장
#   · docs/design/preview-streamlit-clone.html + streamlit-clone.css —
#                              디자인 시안 reference (받는 사람이 시각만 미리 보기 용)
#   · docs/design/fonts/      — LG EI 폰트 woff2 (cf. streamlit-app 안에도 있음)
#   · README_HANDOFF.txt      — 본 스크립트가 자동 생성한 quick start
#
# 제외:
#   · .git/                   — 코드만 보내고 싶음 (git history X)
#   · __pycache__/            — Python 캐시
#   · .venv/                  — 가상환경
#   · *.pyc / *.pyo
#   · streamlit-app/access_log/access_logs.db   — runtime 로그 (개인정보 가능)
#   · streamlit-app/access_log/access_stats_output/  — runtime 통계
#   · streamlit-app/logs/                       — runtime 로그
#   · streamlit-app/uploads/                    — 사용자 업로드 (개인정보 가능)
#   · streamlit-app/__pycache__/                — 캐시
#   · streamlit-app/.idea/                      — IntelliJ/PyCharm 메타
#   · .DS_Store / Thumbs.db                     — OS 메타
#
# 사용:
#   bash streamlit-app/scripts/make_handoff_zip.sh
#   bash streamlit-app/scripts/make_handoff_zip.sh --include-data
#       (Master_Data, ETL/Data 같은 큰 dataset 도 포함; 기본은 skip)

set -euo pipefail
cd "$(dirname "$0")/../.."  # repo root

INCLUDE_DATA=false
[ "${1:-}" = "--include-data" ] && INCLUDE_DATA=true

SHORT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
DATE_STAMP=$(date +%Y%m%d)
ZIP_BASE="LGIT-MPAP-vitals-${SHORT_HASH}-${DATE_STAMP}"
OUT_DIR="dist"
ZIP_PATH="${OUT_DIR}/${ZIP_BASE}.zip"

mkdir -p "$OUT_DIR"
rm -f "$ZIP_PATH"

# Quick-start README 생성 (zip 내부에 포함)
TMP_README=$(mktemp)
cat > "$TMP_README" <<'EOF'
LG Innotek Vitals — Streamlit 앱 인수 패키지
===============================================

이 zip 안에는:
  · streamlit-app/         — 실 deploy 코드
  · docs/STAGE2_RELEASE_NOTES.md — 1장 변경 내역
  · docs/design/           — 디자인 시안 미리보기 (HTML + CSS + 폰트)
  · README_HANDOFF.txt     — 본 파일

빠른 시작 (PostgreSQL 4 DB 가 이미 준비된 회사 PC 기준):

1) 압축 해제:
   unzip LGIT-MPAP-vitals-XXXXX-YYYYMMDD.zip

2) Python 3.11 + 가상환경:
   cd LGIT-MPAP-vitals-XXXXX-YYYYMMDD
   python -m venv .venv
   source .venv/bin/activate          # macOS/Linux
   .venv\Scripts\activate             # Windows

3) 패키지 설치:
   pip install streamlit==1.55.0 sqlalchemy psycopg2-binary pandas \
               plotly matplotlib openpyxl requests st-aggrid \
               streamlit-extras tomli

4) 사전 점검 (선택):
   bash streamlit-app/scripts/preflight.sh

5) 실행:
   cd streamlit-app
   streamlit run login.py

   브라우저가 자동으로 http://localhost:8501 에 열림.

디자인만 미리 확인하고 싶을 때 (Python / DB 불필요):
   docs/design/preview-streamlit-clone.html  더블클릭 → Chrome 으로 열림.

자세한 변경 내역 / 페이지별 확인 포인트:
   docs/STAGE2_RELEASE_NOTES.md 참조.

DB 패스워드:
   streamlit-app/.streamlit/secrets.toml 에 설정되어 있음.
   코드의 fallback (!Q2w3e4r5t) 도 동일. PG 가 다른 비번 쓰면 둘 다 갱신.

문의: 생산혁신센터 Max Capa 팀
EOF

# === zip 빌드 ===
EXCLUDES=(
    "*.git*"
    "*.git/*"
    "*__pycache__/*"
    "*__pycache__"
    "*.pyc"
    "*.pyo"
    "*.DS_Store"
    "*Thumbs.db"
    "*.venv/*"
    "*.idea/*"
    "*streamlit-app/access_log/access_logs.db"
    "*streamlit-app/access_log/access_stats_output/*"
    "*streamlit-app/logs/*"
    "*streamlit-app/uploads/*"
    "*dist/*"
    "*.claude/*"
    "*node_modules/*"
)

# Master_Data / ETL/Data 큰 파일은 옵션
if [ "$INCLUDE_DATA" = "false" ]; then
    EXCLUDES+=("*streamlit-app/Master_Data/*")
    EXCLUDES+=("*streamlit-app/ETL/Data/*")
fi

# zip 명령에 -x 옵션으로 패턴 전달
EXCLUDE_ARGS=()
for pat in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS+=(-x "$pat")
done

# 본 zip 안의 root 디렉토리명을 zip basename 과 동일하게 만들기 위해
# 임시 staging 디렉토리 사용
STAGE_DIR=$(mktemp -d)
trap 'rm -rf "$STAGE_DIR" "$TMP_README"' EXIT

ROOT_IN_ZIP="$STAGE_DIR/$ZIP_BASE"
mkdir -p "$ROOT_IN_ZIP"

echo "[1/4] Staging 디렉토리에 파일 복사 중..."
# rsync 가 있으면 우선 사용 (exclude 패턴 직관적)
if command -v rsync >/dev/null 2>&1; then
    RSYNC_EXCLUDES=()
    for pat in "${EXCLUDES[@]}"; do
        # zip 패턴 → rsync 패턴 (경로 매칭 단순화)
        clean=$(echo "$pat" | sed 's|^\*||; s|/\*$||')
        RSYNC_EXCLUDES+=(--exclude="$clean")
    done
    rsync -a "${RSYNC_EXCLUDES[@]}" \
        streamlit-app/ docs/ \
        "$ROOT_IN_ZIP/" \
        2>/dev/null
    # 실제 streamlit-app, docs/ 가 root 안으로 들어가도록 재배치
    mkdir -p "$ROOT_IN_ZIP/streamlit-app" "$ROOT_IN_ZIP/docs"
    rm -rf "$ROOT_IN_ZIP/streamlit-app" "$ROOT_IN_ZIP/docs"
    rsync -a "${RSYNC_EXCLUDES[@]}" streamlit-app "$ROOT_IN_ZIP/" 2>/dev/null
    rsync -a "${RSYNC_EXCLUDES[@]}" docs "$ROOT_IN_ZIP/" 2>/dev/null
else
    # rsync 없으면 cp + find rm
    cp -r streamlit-app "$ROOT_IN_ZIP/"
    cp -r docs "$ROOT_IN_ZIP/"
    find "$ROOT_IN_ZIP" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$ROOT_IN_ZIP" -name "*.pyc" -delete 2>/dev/null || true
    find "$ROOT_IN_ZIP" -name ".DS_Store" -delete 2>/dev/null || true
    find "$ROOT_IN_ZIP" -name ".idea" -type d -exec rm -rf {} + 2>/dev/null || true
    rm -rf "$ROOT_IN_ZIP/streamlit-app/access_log/access_logs.db" \
           "$ROOT_IN_ZIP/streamlit-app/access_log/access_stats_output" \
           "$ROOT_IN_ZIP/streamlit-app/logs" \
           "$ROOT_IN_ZIP/streamlit-app/uploads" 2>/dev/null || true
    if [ "$INCLUDE_DATA" = "false" ]; then
        rm -rf "$ROOT_IN_ZIP/streamlit-app/Master_Data" \
               "$ROOT_IN_ZIP/streamlit-app/ETL/Data" 2>/dev/null || true
    fi
fi

# README_HANDOFF 추가
cp "$TMP_README" "$ROOT_IN_ZIP/README_HANDOFF.txt"

echo "[2/4] zip 압축 중..."
( cd "$STAGE_DIR" && zip -rq "$OLDPWD/$ZIP_PATH" "$ZIP_BASE" )

# === 검증 ===
echo "[3/4] zip 검증..."
if ! unzip -t "$ZIP_PATH" >/dev/null 2>&1; then
    echo "[FAIL] zip 무결성 검증 실패"
    exit 1
fi

ZIP_SIZE=$(du -h "$ZIP_PATH" | cut -f1)
FILE_COUNT=$(unzip -l "$ZIP_PATH" | tail -1 | awk '{print $2}')

echo "[4/4] 완료."
echo ""
echo "================================================================"
echo " 산출물: $ZIP_PATH"
echo " 크기:   $ZIP_SIZE"
echo " 파일:   $FILE_COUNT"
echo " commit: $SHORT_HASH ($(git log -1 --pretty=format:'%s' 2>/dev/null | head -c 60))"
echo "================================================================"
echo ""
echo "받는 사람에게 안내할 빠른 시작:"
echo "  unzip $ZIP_PATH"
echo "  cd $ZIP_BASE"
echo "  cat README_HANDOFF.txt"
