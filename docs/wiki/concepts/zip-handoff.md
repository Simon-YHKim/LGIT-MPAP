---
type: concept
tags: [handoff, deployment, lg-innotek, packaging]
last_updated: 2026-05-08
related:
  - "[[projects/lgit-mpap]]"
  - "[[concepts/closed-network-deployment]]"
---

# Zip Handoff Pattern

> 폐쇄망 사내 환경에서 엔지니어 → 엔지니어로 코드를 인수할 때 사용하는
> 단일 zip 파일 패키징 패턴. LGIT-MPAP 의 표준 인수 방식.

## 왜 zip 인가

- **GitHub UI 접근 불가** 한 사내 PC 가 있을 수 있음
- **순간적 인수**: 받는 사람이 git/clone/branch 모르고도 압축만 풀면 됨
- **runtime 잔재 제외**: build artifact, 캐시, 로그 등 의도적 제외
- **README 자동 동봉**: 받는 사람이 README 만 따라가면 됨

## LGIT-MPAP 의 zip 빌더

`streamlit-app/scripts/make_handoff_zip.sh`:

```bash
bash streamlit-app/scripts/make_handoff_zip.sh
# → dist/LGIT-MPAP-vitals-<short_hash>-<YYYYMMDD>.zip
```

### 포함
- `streamlit-app/` (실 deploy 코드)
- `streamlit-app/.streamlit/secrets.toml` (폐쇄망 정책)
- `streamlit-app/img/bgi.mp4`, `streamlit-app/ui/vitals/fonts/*.woff2`
- `docs/STAGE2_RELEASE_NOTES.md`, `docs/design/preview-streamlit-clone.html`
- `README_HANDOFF.txt` (auto-generated quick-start)

### 제외
- `.git/`, `__pycache__/`, `*.pyc`, `.venv/`, `.idea/`
- `access_log/access_logs.db`, `logs/`, `uploads/` (runtime, 개인정보 가능)
- `Master_Data/`, `ETL/Data/` (회사 dataset, 큰 용량)
- `.DS_Store`, `Thumbs.db`

옵션: `--include-data` 로 Master_Data 포함 가능.

## 받는 사람 흐름

```
1. unzip LGIT-MPAP-vitals-<hash>-<date>.zip
2. cd LGIT-MPAP-vitals-<hash>-<date>
3. cat README_HANDOFF.txt   ← Python / 패키지 / streamlit run 안내
4. (가상환경 + pip install + DB 환경 확인)
5. cd streamlit-app && streamlit run login.py
```

## 운영 머신 덮어쓰기 시 보존할 것

- `.streamlit/secrets.toml` — 머신별 실 비번
- `.streamlit/config.toml` — 머신별 streamlit 설정
- `access_log/`, `logs/`, `uploads/` — runtime / 개인정보
- `Master_Data/`, `ETL/Data/` — 회사 dataset
- `pages/setting.ini` — 머신별 설정

위 항목 백업 → 코드만 덮어쓰기 → 위 항목 복원.

## Lesson

이전 엔지니어가 zip 으로 인수했던 패턴 — 회사 운영 흐름의 일부.
GitHub 없이도, git 모르는 사람도 받을 수 있는 패키징은 가치 있음.
