# LGIT-MPAP (LG Innotek Vitals) — Cowork 핸드오프 프롬프트

> 다음 Claude Code 세션에서 이 프로젝트를 이어받아 작업할 때 첫 메시지로
> 그대로 붙여 넣으세요. (또는 본 .md 를 `cat` 으로 보여주세요.)

---

## 0. 한 줄 컨텍스트

**LG Innotek 광학솔루션 사업부 · 생산혁신센터 Max Capa TDR** 의 폐쇄망
설비 생산성 분석 플랫폼 **Vitals** (이전: MPAP / Stethos). 캐치프레이즈
"공정의 호흡을 데이터로 듣다". Streamlit 1.55 + PostgreSQL 4 DB + vLLM.
이전 엔지니어로부터 zip 파일로 인수받아 표현 layer 만 정렬 중.

---

## 1. 절대 대원칙 (어기면 즉시 revert)

이전 엔지니어가 회사 폐쇄망 환경에 맞춰 의식적으로 잡은 백엔드는
**한 줄도 손대지 말 것.** 변경 가능한 것은 표현 layer (HTML 구조 / CSS /
시각 정렬) 만.

| 영역 | 보존 패턴 | 이유 |
|---|---|---|
| DB 연결 | `get_conn()` 매 호출 fresh `psycopg2.connect(...)` | 회사 PG 호환 |
| DB 패스워드 fallback | `os.getenv('X', '!Q2w3e4r5t')` literal | 폐쇄망 (외부공격자 0) |
| 인증 | `auth_guard.require_login()` + `st.session_state` | 손대지 X |
| SQL dialect | `NOW()` (Postgres-only) | 회사 표준 |
| CDN @import | Pretendard / IBM Plex Mono CDN | 폐쇄망 fallback |
| session_state 키 87개 | 추가 OK / 변경·삭제 X | 기존 흐름 보존 |
| 함수 576개 / SQL 223개 | 추가 OK / 시그니처·문자열 변경 X | baseline 검증 |
| `secrets.toml` + `setting.ini` 평문 password | git 에 commit 의식적 | 인수자 즉시 작동 |

**검증 게이트** (commit 후 4개 모두 PASS 필수):
```bash
python streamlit-app/scripts/verify_backend_freeze.py        # 576 fn / 223 SQL / 87 sess
python streamlit-app/scripts/verify_no_external.py           # 외부 URL 0
python streamlit-app/scripts/verify_dark_mode_tokens.py      # dark CSS 일관
bash streamlit-app/scripts/smoke_compile.sh                  # 49 .py syntax
bash streamlit-app/scripts/preflight.sh                      # 종합 1-shot
```

하나라도 FAIL → **commit 금지, 즉시 revert.**

---

## 2. Vitals 디자인 룰 (반드시 준수)

| 원칙 | 구현 |
|---|---|
| **Rectangles only** | `border-radius: 0` (status dot 50%, 의식적 pill 999px 만 예외) |
| **Wine identity** | 모든 페이지 상단 `render_top_strip()` (6px wine bar) |
| **Section rhythm** | `render_sub_head(title, meta)` |
| **No emoji UI** | 🌐 / ● / ▸ → SVG (Pretendard 시스템 fallback OK) |
| **3-color max** | `--primary` (wine) + `--ink-body` + `--page-bg` |
| **No bouncy easing** | 120~180ms linear / ease-out |
| **33 Vitals tokens only** | hex 직접 사용 금지 (`measure_design_integration.py`) |

DB 값을 HTML 로 출력할 때 **반드시 `html.escape()`** (Stored XSS 방지).

---

## 3. 폐쇄망 compliance

- 폰트 woff2 자체 호스팅 (`streamlit-app/ui/vitals/fonts/*.woff2` 5개)
- 비디오 mp4 자체 호스팅 (`streamlit-app/img/bgi.mp4` 10MB)
- 외부 URL 검출 게이트 (`verify_no_external.py`) — Pretendard / Plex CDN 만 ALLOW
- `youtube.com` 같은 도메인 0 (폐쇄망 차단)

---

## 4. 진행 상황 (2026-05-08 ~ 05-09)

### 브랜치
- 현재: `claude/vitals-stage3-ux` (origin push 완료)
- Base: `streamlit-source`
- 누적 38+ commits (STAGE 1 + 2 + 3)

### 최근 commits (시간 역순)
```
00871bd  chore(stage3): design score 재측정 — login.py 97.2 → 97.3
8bc0d91  fix(stage3): 사용자 피드백 6종 — 모달/로그인/메일/MTBA/패치/단색
466444e  fix(stage3): 사용자 명시 task 11종 실 처리 — preview HTML/CSS
c3ffd80  feat(stage3-streamlit): preview 변경의 streamlit-app mirror
9a6e5bf  fix(stage3): 사용자 명시 task 11종 일괄
e4b6e5c  fix(stage3): footer 제거 + Home_1 (s2-b) layout
```

### 이번 세션 (STAGE 3 라운드 4) 처리 내역 — `8bc0d91`

1. **설정 모달 차단 해소** — 4개 `vit-modal-backdrop`
   (cmp-proc / alarm-detail / team-procs / settings) 의 inline
   `style="display:none !important;"` 제거. JS `removeAttribute('hidden')`
   만으로는 inline style 우선이라 모달이 안 떴음 → 이제 `[hidden]` attribute
   만으로 toggle 정상.

2. **로그인 viewport 풀**
   - preview HTML/CSS: `sc-login-app` absolute inset 0, `sc-login-shell`
     `min-height:0; height:100%`, `:has(.sc-login-section.is-active)` 시
     block-container padding 0 + 사이드바 hide + body overflow:hidden.
   - streamlit `login_ui/styles.py`: `[data-testid="stAppViewContainer"]
     { height:100vh; overflow:hidden }`, `block-container padding-top`
     2.5rem → 0.75rem.

3. **문의 메일 ↔ 프로필 attach** — border + margin 제거 + 같은 `var(--card-bg)`
   로 한 덩어리. `vit-sidebar-user` padding 12/16 → 10/16/4, contact 의
   `border-top: 1px dashed` → 0.

4. **MTBA 그래프 와인~검은 grayscale** — `data-period` scope 로 안전 교체:
   - 1주전: `#D88FA2` → `#8B0830`
   - 2주전: `#7E0027` → `#6B1E3A`
   - 지난달: `#B57F1B` → `#4B1E2A`
   - 2달전: `#6B7280` → `#2E1419`
   - 범례 dot 4개 동기화. 선택 기간 `#A50034` / 지난해 `#1F2430` 유지.
   - **CMP/UPH 동일 hex 는 별도 의미라 손대지 않음.**

5. **패치노트 panel 높이 일치** — 부모 grid `align-items: stretch`,
   column 컨테이너 + 내부 `sc-soft-card` 에 `flex:1 1 auto`. 목록만
   `overflow-y:auto`.

6. **그라데이션 → 단색** — `vit-page-hero / sc-page-banner /
   sc-card-bad/warn/good / sc-proc-card.is-* / sc-aggrid thead` 9 사이트
   Vitals 단색 토큰으로 치환. vignette 만 의식적 유지 (영상 위 가독).

### 검증 결과
- 4 게이트 PASS — backend (576 fn / 223 SQL / 87 sess), no-external,
  dark-tokens, smoke-compile.
- 디자인 점수 **97.8 / 100** (목표 95+ 통과).
- `/review`: **0 CRITICAL / 3 INFORMATIONAL.**

### `/review` INFO 잔여 (다음 세션 판단)
- **INFO-1** (conf 7): login `html, body { overflow:hidden !important }` 가
  작은 화면 (1366×768) 에서 회원가입 폼 자를 위험.
  → `@media (max-height: 760px)` 보강 권장.
- **INFO-2** (conf 6): preview-only `:has()` selector — streamlit-app 영향
  없음, IE/Edge Legacy 만 깨짐.
- **INFO-3** (conf 5): MTBA bar 4개 신규 hex 는 preview SVG inline 만 존재
  — streamlit-app/css 미반영, dark mode mirror 시 토큰화 필요.

---

## 5. 다음에 할 일 (우선순위)

### 즉시 (사용자 컨펌 후)
1. **SimonK 인스팅트 append** — `~/.claude/instincts/project-patterns.md`
   의 LGIT-MPAP 섹션에 이번 세션 학습 추가:
   - inline `display:none !important` + JS `removeAttribute` 안티패턴
   - `data-period` scope 로 동일 hex 의 의미 분리
   - Streamlit `[data-testid="stAppViewContainer"]` height:100vh 로
     viewport 풀 만드는 패턴.

2. **LLM Wiki ingest** — `Simon-YHKim/Simon-LLM-Wiki` 의
   `wiki/projects/lgit-mpap.md` 에 STAGE 3 라운드 4 timeline + decisions
   추가 (이미 일부 작성).

### 단기 (사용자 피드백 대기)
- INFO-1 보강 (`@media (max-height: 760px)` login 규칙).
- 사용자 5월 8+ 피드백 6 항목 잔여 점검:
  1. 16:9 모니터 비율 최적화
  2. 대시보드 좌우 여백 = patch note
  3. 스크롤 최소화 (S3-B 기준)
  4. 사이드바 user profile 항상 최하단 + 설정 버튼 기능
  5. 문의 메일 위치
  6. 텍스트 정리 (Max Capa 팀 → Max Capa TDR / streamlit clone / 제작)
- 추가: 로그인 좌우 분리, 언어 선택 실 기능, Home 흰색 panel 제거.

### 중기 (배포 전)
- `bash streamlit-app/scripts/preflight.sh` 1-shot 점검.
- `bash streamlit-app/scripts/make_handoff_zip.sh` zip 생성
  (이전 엔지니어 인수 방식 유지).
- `docs/RELEASE_v1_DRAFT.md` 기반 GitHub Release 초안.

---

## 6. 페이지 구조 (시각 정렬 완료)

| 페이지 | 파일 | 시각 패턴 |
|---|---|---|
| login | `login.py` | 비디오 배경 + auth-card |
| 0_Home | `pages/0_Home.py` | top_strip + KPI + Best/Worst (case0/1/2) |
| 1_CMP | `pages/1_CMP_Dashboard.py` | top_strip + section-heading wine bar |
| 2_UPH | `pages/2_UPH_Dashboard.py` | top_strip + page-head + 6× sub_head |
| 3_MTBA | `pages/3_MTBA_Dashboard.py` | top_strip + page-banner + @st.dialog |
| 4_Detail | `pages/4_MTBA_Detail_View.py` | top_strip + page-hero + heatmap modal |
| 5_Alarm | `pages/5_Alarm_Action_List.py` | top_strip + 3× sub_head + CSV export |
| 6_Chat | `pages/6_MaxCapa_Chat.py` | top_strip + chat-head + FastAPI:9000 |
| 8_Patch | `pages/8_Patch_Note.py` | top_strip + 2× sub_head + sc-mono meta |
| 9_Admin | `pages/9_Admin_Analytics.py` | top_strip + 4× sub_head + 10탭 |

---

## 7. 새 작업 시 체크리스트

- [ ] 백엔드 변경 없음? → `verify_backend_freeze.py` PASS?
- [ ] DB 값 HTML 출력? → `html.escape()` 적용?
- [ ] 새 hex? → Vitals 토큰 33개 중 하나?
- [ ] 새 emoji? → SVG 로 교체?
- [ ] 새 `border-radius`? → 0 (status dot 예외)?
- [ ] 새 함수 추가? → `verify_backend_freeze.py --emit-baseline`?
- [ ] 새 외부 URL? → `verify_no_external.py` ALLOW 추가 또는 제거?
- [ ] commit 전 4 게이트 PASS?
- [ ] design score `measure_design_integration.py` 95+?

---

## 8. 환경

| 항목 | 값 |
|---|---|
| Repo | `Simon-YHKim/LGIT-MPAP` |
| 현재 브랜치 | `claude/vitals-stage3-ux` |
| 인수 방식 | zip (`make_handoff_zip.sh` → `dist/LGIT-MPAP-vitals-<hash>-<date>.zip`) |
| Streamlit | **1.55.x 권장** (clone.css 의 32 data-testid selector 호환) |
| Python | 3.11+ |
| DB | PostgreSQL 4개 (MTBA / auth / I-TAS_Data / CMP) |
| LLM 백엔드 | vLLM (FastAPI:9000) |

---

## 9. 참고 문서

- `CLAUDE.md` (repo root) — 회사방식 보존 + Vitals 디자인 룰 (필독)
- `docs/STAGE2_RELEASE_NOTES.md` — STAGE 1+2 인수 인계 전체
- `docs/RELEASE_v1_DRAFT.md` — GitHub Release UI 복붙용
- `~/.claude/CLAUDE.md` — 글로벌 지침
- `~/.claude/instincts/project-patterns.md` LGIT-MPAP 섹션 — 누적 학습

---

## 10. 첫 메시지 가이드

새 세션에서 이 프롬프트를 받은 Claude 는 **반드시 다음을 먼저** 하세요:

1. `git status && git log --oneline -10` — 현재 상태 확인
2. `bash streamlit-app/scripts/preflight.sh` — 4 게이트 PASS 확인
3. `python streamlit-app/scripts/measure_design_integration.py` — 디자인 점수
4. `CLAUDE.md` (repo root) 읽기
5. 사용자에게 다음 작업 우선순위 확인 — **임의로 진행 금지**

**금지**:
- 백엔드 (DB / SQL / auth / session / 함수 시그니처) 변경
- `--no-verify` commit
- 4 게이트 FAIL 상태 commit
- `git push --force` 사용자 컨펌 없이
- emoji UI 추가
- hex 직접 사용 (33 토큰 외)
- `border-radius: <0 아닌 값>` (예외만)

---

_2026-05-09 작성. STAGE 3 라운드 4 (8bc0d91 + 00871bd) 직후._
