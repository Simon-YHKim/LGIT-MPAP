---
type: concept
tags: [deployment, lg-innotek, security, font-hosting]
last_updated: 2026-05-08
related:
  - "[[projects/lgit-mpap]]"
  - "[[concepts/backend-preservation-principle]]"
---

# Closed-Network Deployment

> 인터넷 차단된 사내 PC 에서 운영되는 환경. 모든 외부 의존이 사전에 자체
> 호스팅 / 번들로 들어와 있어야 함.

## LGIT-MPAP 의 폐쇄망 결정들

| 영역 | 처리 |
|---|---|
| **폰트** | LG EI Text (300/400/600/700) + Headline (700) — 5 weight `.woff2` 자체 호스팅 (`streamlit-app/ui/vitals/fonts/`, ~1.7MB) |
| **로그인 비디오** | `streamlit-app/img/bgi.mp4` (~10MB) 자체 호스팅 |
| **CDN @import (의식적)** | `Pretendard` (cdn.jsdelivr) + `IBM Plex Mono` (fonts.googleapis) — 외부망 환경 fallback 의도. 폐쇄망에선 dead load 지만 의식적 유지 |
| **DB 패스워드** | `secrets.toml` + `setting.ini` 에 평문 commit (사내망 정책). 코드 fallback `!Q2w3e4r5t` literal 도 유지 |
| **외부 URL 검출** | `verify_no_external.py` 게이트 — Pretendard / Plex CDN 만 ALLOW |

## 외부 공개 시 한 번에 처리해야 할 것

폐쇄망 → public 전환 시점에 일괄:
1. `secrets.toml` 에서 password 제거 (or git rm)
2. `setting.ini` 의 `db_password` 제거
3. 코드 7곳의 literal fallback 제거
4. **DB password 회전** (이미 git history 노출)
5. `.gitignore` 의 secrets.toml 주석 해제

지금처럼 폐쇄망 환경에선 위 1~5 모두 의미 있는 효과 = 0.

## Lesson

"폐쇄망에선 dead" 라고 보이는 코드가 의식적 fallback 일 수 있음.
삭제 전 의도 확인 필수. ([[concepts/backend-preservation-principle]])
