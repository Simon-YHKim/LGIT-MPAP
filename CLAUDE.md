# CLAUDE.md — LG Innotek Vitals (LGIT-MPAP)

> 이 파일은 본 레포에서 새 Claude Code 세션 시작 시 자동 로드된다.
> 작업 시 **반드시** 따라야 할 대원칙과 프로젝트 컨텍스트를 정리한다.
>
> 글로벌 지침: `~/.claude/CLAUDE.md`
> 누적 학습: `~/.claude/instincts/project-patterns.md` 의 `LGIT-MPAP` 섹션
> STAGE 2 인수 인계: `docs/STAGE2_RELEASE_NOTES.md`

---

## 0. 한 줄 요약

**이전 엔지니어가 정한 "데이터 호출 앞단" (DB·인증·SQL·session·연결방식·CDN fallback) 은 한 줄도 변경 금지. 변경 가능한 것은 표현 layer 만 (HTML 구조 / CSS / 시각 정렬).**

---

## 1. 절대 변경 금지 (회사 방식 보존)

이전 엔지니어가 의식적으로 잡은 것 — 회사 운영 환경에 최적화된 결정.

| 영역 | 보존 패턴 | 이유 |
|---|---|---|
| **DB 연결 방법** | `get_conn()` 매 호출 fresh `psycopg2.connect(...)` | 트랜잭션 격리 / 회사 PG 설정 호환 |
| **DB 패스워드 fallback** | `os.getenv('X', '!Q2w3e4r5t')` literal | 폐쇄망 새 PC 즉시 작동 (외부 공격자 0) |
| **인증 흐름** | `auth_guard.require_login()` + `st.session_state` 키 | 손대지 말 것 |
| **SQL dialect** | `NOW()` (Postgres-only) | 회사 표준 |
| **CDN @import** | `Pretendard` / `IBM Plex Mono` from cdn.jsdelivr/googleapis | 외부망 환경 fallback 의도 |
| **session_state 키** | 87개 기존 키 (selected_post_id, role, edit_mode, mtba_*, cmp_* 등) | 추가 OK / 변경·삭제 X |
| **함수 시그니처** | 576개 기존 함수의 이름·인자 | 추가 OK / 시그니처 변경 X |
| **SQL 쿼리 문자열** | 223개 기존 SQL | 추가 OK / 문자열 변경 X |
| **secrets.toml + setting.ini** | git 에 password 평문 commit | `streamlit-app/.gitignore` 의 의식적 결정 |

**검증 도구**: `python streamlit-app/scripts/verify_backend_freeze.py`
이 게이트가 PASS 안 하면 backend 가 변경된 것 → 즉시 revert.

baseline JSON 갱신은 의도적 함수 추가 시만 (변경·삭제 시는 절대 X):
`python streamlit-app/scripts/verify_backend_freeze.py --emit-baseline`

---

## 2. 변경 가능 (표현 layer)

데이터를 받아온 후 어떻게 보여줄지는 자유. 단 Vitals 디자인 룰 준수.

| 영역 | 가능한 변경 |
|---|---|
| `st.markdown(unsafe_allow_html=True)` 의 HTML 구조 | OK (DB 값은 `html.escape` 필수) |
| 페이지별 inline `<style>` 블록 | OK (Vitals 토큰 사용) |
| `ui/vitals/components.py` 의 primitive 추가/사용 | OK (기존 함수 시그니처는 보존) |
| `ui/vitals/theme.py` 의 CSS 토큰 / 클래스 | OK (단 dark mode 동기화 유지) |
| Preview HTML/CSS (`docs/design/`) | OK |

---

## 3. Vitals 디자인 원칙

| 원칙 | 구현 |
|---|---|
| **Rectangles only** | `border-radius: 0` (status dot 50%, 의식적 pill 999px 만 예외) |
| **Wine identity** | 모든 페이지 상단 `render_top_strip()` (6px wine bar) |
| **Section rhythm** | `render_sub_head(title, meta)` (좌 4px wine + h3 + 우 메타) |
| **No emoji UI** | `🌐 / ● / ▸` 같은 emoji → SVG (Pretendard 시스템 fallback OK) |
| **No multi-color** | UI 색상 3개 이내: `--primary` (wine), `--ink-body`, `--page-bg` |
| **No bouncy easing** | `120ms ~ 180ms` linear / ease-out |
| **Vitals tokens only** | 33개 토큰 외 hex 사용 금지 (검증: `measure_design_integration.py`) |

---

## 4. 폐쇄망 compliance

| 룰 | 근거 |
|---|---|
| 모든 폰트 woff2 자체 호스팅 | `streamlit-app/ui/vitals/fonts/*.woff2` 5개 |
| 비디오 mp4 자체 호스팅 | `streamlit-app/img/bgi.mp4` (10MB) |
| 외부 CDN URL 검출 게이트 | `verify_no_external.py` (Pretendard / Plex CDN 만 ALLOW) |
| `https://www.youtube.com/...` 같은 domain 0 | 폐쇄망 차단 |

---

## 5. 검증 도구 (항상 PASS 유지)

```bash
# 4 게이트 — 모든 commit 후 자동 실행 권장
python streamlit-app/scripts/verify_backend_freeze.py        # backend 보존
python streamlit-app/scripts/verify_no_external.py           # 외부 URL 0
python streamlit-app/scripts/verify_dark_mode_tokens.py      # dark CSS 일관
bash streamlit-app/scripts/smoke_compile.sh                  # 49 .py syntax

# 종합 점검 (deploy 전 1-shot)
bash streamlit-app/scripts/preflight.sh

# 디자인 점수 (목표 95+/100)
python streamlit-app/scripts/measure_design_integration.py
```

**4 게이트 중 하나라도 FAIL 면 commit 하지 말 것** — 회사 방식 위반 가능성.

---

## 6. 환경

| 항목 | 값 |
|---|---|
| 회사 / 부서 | LG Innotek 광학솔루션 사업부 · 생산혁신센터 Max Capa 팀 |
| 플랫폼 이름 | Vitals (이전: MPAP / Stethos) |
| 캐치프레이즈 | "공정의 호흡을 데이터로 듣다" |
| 환경 | 폐쇄망 사내 PC + Streamlit + PostgreSQL + vLLM |
| Streamlit 버전 | **1.55.x 권장** (clone.css 의 32 data-testid selector 가 이 버전 기준) |
| Python | 3.11+ |
| DB | PostgreSQL 4개 (MTBA / auth / I-TAS_Data / CMP) |
| 인수 인계 방식 | zip 파일 (이전 엔지니어 방식 그대로) — `bash streamlit-app/scripts/make_handoff_zip.sh` |

---

## 7. 페이지 구조 (시각 정렬 완료)

| 페이지 | 파일 | 시각 패턴 |
|---|---|---|
| login | `login.py` | 비디오 배경 + auth-card (top_strip 의식적 미적용) |
| 0_Home | `pages/0_Home.py` | top_strip + KPI / Best/Worst (3 모드: case0/case1/case2) |
| 1_CMP | `pages/1_CMP_Dashboard.py` | top_strip + section-heading wine bar |
| 2_UPH | `pages/2_UPH_Dashboard.py` | top_strip + page-head eyebrow + 6× sub_head |
| 3_MTBA | `pages/3_MTBA_Dashboard.py` | top_strip + page-banner + @st.dialog 모달 |
| 4_Detail | `pages/4_MTBA_Detail_View.py` | top_strip + page-hero + heatmap @st.dialog |
| 5_Alarm | `pages/5_Alarm_Action_List.py` | top_strip + 3× sub_head + render_csv_export |
| 6_Chat | `pages/6_MaxCapa_Chat.py` | top_strip + chat-head + FastAPI:9000 호출 |
| 8_Patch | `pages/8_Patch_Note.py` | top_strip + 2× sub_head + sc-mono meta |
| 9_Admin | `pages/9_Admin_Analytics.py` | top_strip + 4× sub_head + 10탭 + analytics.* SQL |

---

## 8. 새 작업 시 체크리스트

- [ ] 백엔드 (DB·인증·SQL·session·연결·CDN) 변경 없음? → `verify_backend_freeze.py` PASS?
- [ ] DB 값을 HTML 로 출력? → `html.escape()` 적용?
- [ ] 새 hex 사용? → Vitals 토큰 33개 중 하나? (아니면 매핑)
- [ ] 새 emoji? → SVG 로 교체?
- [ ] 새 `border-radius: <0 아닌 값>`? → 0 으로 (status dot 예외)
- [ ] 새 함수 추가? → `--emit-baseline` 으로 baseline 갱신
- [ ] 새 외부 URL? → `verify_no_external.py` 의 ALLOW_SUBSTRINGS 에 명시 또는 제거
- [ ] commit 전 4 게이트 모두 PASS?

---

## 9. 인수 / 배포

```bash
# zip 인수 (이전 엔지니어 방식)
bash streamlit-app/scripts/make_handoff_zip.sh
# → dist/LGIT-MPAP-vitals-<hash>-<date>.zip

# deploy 전 점검
bash streamlit-app/scripts/preflight.sh
```

자세한 인수 흐름: `docs/STAGE2_RELEASE_NOTES.md` §3
Release 만들기: `docs/RELEASE_v1_DRAFT.md`

---

_2026-05-08 작성. STAGE 1+2 완료 후 codify._
