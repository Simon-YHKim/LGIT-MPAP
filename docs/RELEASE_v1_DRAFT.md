# Release Draft — `vitals-stage2-v1`

> 본 문서: GitHub Release 생성 시 description 으로 그대로 복붙용.
> 사용자가 webUI 에서 release 만들 때 1분 작업.

---

## Tag 이름 (suggested)
```
vitals-stage2-v1
```

## Release Title (suggested)
```
STAGE 2 — visual integration handoff (v1)
```

## Description (Release body 용 — 아래 ━━ 사이 통째로 복붙)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Vitals — STAGE 2 visual integration

이전 엔지니어가 zip 으로 인수했던 streamlit-app 코드에 대해 **STAGE 1 + STAGE 2** 작업 완료.
31 commits, 백엔드 0% 변경, 시각만 정렬.

## What changed

| 영역 | 변경 |
|---|---|
| 백엔드 (DB·인증·SQL·session_state·연결방식·CDN fallback) | **0%** (이전 엔지니어 결정 100% 보존) |
| 표현 layer | 모든 페이지 상단 와인 6px strip + 좌측 wine 4px sub-head bar |
| 카드·버튼·입력 | 직사각형 (Vitals 'rectangles only' 원칙) |
| Off-Vitals hex | 모두 Vitals 토큰 매핑 |
| Preview HTML 시안 | 21건 broken 인터랙션 fix + orphan modal / YouTube iframe 제거 |
| XSS | `8_Patch_Note.py` stored XSS 4 사이트 `html.escape` |
| 검증 인프라 | `backend_freeze` + `no_external` + `smoke_compile` + `dark_tokens` 4 게이트 추가 |

## Quality gates (모두 PASS)

```
verify_backend_freeze   PASS — 37 files / 576 fns / 223 SQL / 87 session keys
verify_no_external      PASS — 56 files clean
verify_dark_mode_tokens PASS — light + dark coherent
smoke_compile           PASS — 49 .py compile clean
design_score            96.6 / 100
```

## How to use this release

### Option A — Just the source
**Download Source code (zip)** ← GitHub 가 자동 첨부.
폴더 압축 풀고 `streamlit-app/` 안에 들어가 `streamlit run login.py`.

### Option B — Curated handoff zip (with `README_HANDOFF.txt`)
업로드된 `LGIT-MPAP-vitals-<hash>-<date>.zip` 다운로드. `__pycache__` 같은 잔재 제외 + auto-generated quick-start 포함.

### Option C — From source
```bash
git clone https://github.com/Simon-YHKim/LGIT-MPAP
cd LGIT-MPAP
git checkout vitals-stage2-v1   # 또는 claude/streamlit-vitals-Sry57
bash streamlit-app/scripts/preflight.sh
cd streamlit-app
streamlit run login.py
```

## Documentation

- **`docs/STAGE2_RELEASE_NOTES.md`** — 1장 변경 내역 + 페이지별 확인 포인트
- **`docs/design/preview-streamlit-clone.html`** — 시안 미리보기 (DB 없이 브라우저로)
- **`streamlit-app/scripts/preflight.sh`** — deploy 전 1-shot 점검

## Backend preservation guarantee

이번 작업 동안 한 번도 변경되지 않은 것 (AST diff 자동 검증):
- 모든 SQL 쿼리 문자열 (223개)
- 모든 함수 시그니처 (576개)
- 모든 `st.session_state` 키 (87개)
- 모든 import 문
- DB 연결 방식 (`get_conn` 매 호출 fresh psycopg2)
- 인증 흐름 (`login.py`, `auth_guard.py`)
- DB 패스워드 fallback 패턴
- PG dialect (`NOW()`)
- CDN fallback (`Pretendard`, `IBM Plex Mono`)

→ 새 페이지 추가 / SQL 수정 / 디버깅하는 방법은 **이전과 100% 동일**.

## Branch

`claude/streamlit-vitals-Sry57` — 31 commits 이 모두 이 브랜치에 있음.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---

## 사용자가 GitHub UI 에서 할 일 (1분)

### 1. Release UI 진입
브라우저로 접속:
```
https://github.com/Simon-YHKim/LGIT-MPAP/releases/new
```

### 2. Tag 입력
- **Choose a tag** dropdown → 직접 타이핑 → `vitals-stage2-v1`
- "Create new tag: vitals-stage2-v1 on publish" 선택
- **Target**: `claude/streamlit-vitals-Sry57` 브랜치 선택

### 3. Release title
```
STAGE 2 — visual integration handoff (v1)
```

### 4. Description
위의 ━━ 사이 마크다운 통째로 복붙.

### 5. (선택) Curated zip 첨부
본인 PC 또는 회사 PC 에서:
```bash
git fetch origin
git checkout claude/streamlit-vitals-Sry57
git pull
bash streamlit-app/scripts/make_handoff_zip.sh
# → dist/LGIT-MPAP-vitals-f189550-20260508.zip (~26MB)
```
이 파일을 release 페이지 하단의 **"Attach binaries by dropping them here"** 영역에 drag-and-drop.

이 단계 생략해도 GitHub 가 자동으로 "Source code (zip)" 첨부함. Curated zip 의 장점은 `README_HANDOFF.txt` + `__pycache__` 제외.

### 6. Publish
- (선택) ✅ "Set as the latest release" 체크
- ✅ "Create a discussion for this release" — 사내 인수 인계 흐름이면 끄는 게 깔끔
- **Publish release** 클릭

→ 완료. 이후 누구나 `https://github.com/Simon-YHKim/LGIT-MPAP/releases/tag/vitals-stage2-v1` 에서 다운 가능.

---

## 왜 자동화 안 됐는지

이번 세션에서 release 자동 생성 시도했지만:
- GitHub MCP 툴 제공 목록에 release 생성 / asset 업로드 기능 없음 (read-only: `list_releases`, `get_latest_release`, `get_release_by_tag`)
- `gh` CLI 시스템 정책상 차단
- `git push origin <tag>` 시도 → HTTP 403 (org/repo tag push 권한 없음)

→ 사람이 webUI 에서 마지막 단계 (3분) 직접.
