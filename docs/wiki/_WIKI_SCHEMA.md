# Simon-LLM-Wiki — Schema (CLAUDE.md)

> Andrej Karpathy 의 [llm-wiki 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 구현.
> 사용자 (Simon) 의 영속 누적 지식 베이스. RAG 가 매번 새로 합성하는 대신
> 이 wiki 가 페이지로 가지고 있어 교차참조·모순 발견·시간 추적 가능.

본 wiki 는 LLM 이 관리하는 markdown 의 **wiki 가 코드, LLM 이 프로그래머**.

---

## 0. 디렉토리 구조

```
~/.claude/wiki/Simon-LLM-Wiki/
├── raw/                   ← 1. 불변 raw sources (사람이 큐레이션)
│   ├── articles/          (URL 다운로드, PDF 등)
│   ├── papers/
│   └── assets/            (이미지, Obsidian 호환)
├── wiki/                  ← 2. LLM 소유 markdown
│   ├── entities/          (사람·조직·제품 — PascalCase)
│   ├── concepts/          (추상 개념·기법 — kebab-case)
│   ├── sources/           (소스별 요약 — YYYY-MM-DD-slug.md)
│   ├── queries/           (file back 질문 답변)
│   ├── projects/          (실 프로젝트 누적 — LGIT-MPAP 등)
│   ├── index.md           (카탈로그)
│   └── log.md             (시간순 append-only)
└── CLAUDE.md              ← 본 파일 (스키마 규약)
```

---

## 1. 페이지 명명 규약

| 종류 | 위치 | 명명 |
|---|---|---|
| Entity (사람·조직·제품) | `wiki/entities/` | PascalCase. 예: `LG-Innotek.md`, `Karpathy.md` |
| Concept (추상 개념) | `wiki/concepts/` | kebab-case. 예: `rag.md`, `closed-network-deployment.md` |
| Source (외부 소스 요약) | `wiki/sources/` | `YYYY-MM-DD-slug.md`. 예: `2026-04-04-karpathy-llm-wiki.md` |
| Query (file back 답변) | `wiki/queries/` | kebab-case. 예: `rag-vs-llm-wiki.md` |
| Project (장기 프로젝트) | `wiki/projects/` | kebab-case. 예: `lgit-mpap.md` |

---

## 2. Frontmatter 표준

모든 페이지 상단:

```yaml
---
type: entity | concept | source | query | project
tags: [tag1, tag2]
sources: [[2026-04-04-source-slug]]
last_updated: YYYY-MM-DD
---
```

---

## 3. Cross-link 형식

Obsidian 스타일 wiki link:
- `[[Page-Name]]` — 동일 폴더 또는 절대 경로
- `[[concepts/rag]]` — 다른 폴더
- `[[2026-04-04-source-slug]]` — source 페이지

깨진 link 는 `lint.sh` 가 detect.

---

## 4. Ingest 워크플로

```
1. raw/ 에 source 복사 (URL 이면 다운로드)
2. LLM 이 source 읽고 핵심 포인트 추출
3. wiki/sources/<slug>.md 요약 페이지 작성
4. 관련 entity/concept 페이지 갱신 (10-15개 페이지 영향 가능)
5. wiki/index.md 갱신 (alphabetical, 카운트 포함)
6. wiki/log.md 에 entry append
```

`wiki/log.md` 형식:
```markdown
## [YYYY-MM-DD] ingest | <Source Title>
- Updated: entities/X.md, concepts/Y.md
- New: sources/Z.md
- Tokens: ~N
```

---

## 5. Lint 기준

- **Contradictions**: 같은 entity 의 다른 페이지에서 모순 주장
- **Stale claims**: 새 source 가 superseded 한 오래된 주장
- **Orphan pages**: 어디서도 link 되지 않은 페이지
- **Missing pages**: 자주 언급되는데 자기 페이지 없는 entity/concept
- **Broken cross-refs**: 깨진 wiki link
- **Data gaps**: 보강하면 좋을 외부 search 후보

산출: `wiki/lint-report-<date>.md`

---

## 6. 금기 사항

- ❌ `raw/` 디렉토리의 파일 수정 금지 (불변)
- ❌ 시크릿·비밀번호·내부 URL 기록 금지
- ❌ 출처 (citation) 없이 주장 추가 금지 — 모든 claim 은 source 페이지 link 필수
- ❌ index.md / log.md 의 과거 entry 수정 금지 (append-only)
- ❌ frontmatter `last_updated` 갱신 안 하고 본문 수정 금지

---

## 7. Project 페이지 규약

`wiki/projects/<slug>.md` 는 장기 프로젝트의 누적 history.

필수 섹션:
1. **Overview** — 프로젝트 정의, 환경, 스택
2. **Timeline** — 시간순 milestone (commit hash 포함)
3. **Decisions** — 의식적 결정 + 근거
4. **Mistakes & Lessons** — 실수 + 해결법 + 예방책
5. **Open items** — 진행 중·deferred·next
6. **Cross-refs** — 관련 entities / concepts

특히 **Mistakes & Lessons** 가 핵심: 미래의 자신 / 다른 엔지니어가 같은 실수 안 하도록.

---

## 8. 인간 vs LLM 역할

| 인간 (Simon) | LLM |
|---|---|
| 소스 큐레이션 | 요약·교차참조·파일링 |
| 좋은 질문 | bookkeeping |
| 탐험 방향 결정 | 일관성 유지 |
| 판단·통찰 | 모순 detect |

> "The tedious part of maintaining a knowledge base is not the reading
> or the thinking — it's the bookkeeping. LLMs don't get bored." — Karpathy

---

_본 wiki 의 첫 commit. LLM 이 매 ingest / query / lint 시 본 schema 를 우선 참조._
