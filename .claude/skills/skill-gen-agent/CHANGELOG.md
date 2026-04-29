# Changelog

## 0.5.0 - 2026-04-13

- Add --fix auto-fix mode to refactor_skill.py. Applies five safe mechanical transformations: insert Contents TOC into long reference files (>100 lines), rewrite Windows backslash paths to forward slashes in SKILL.md, strip trailing whitespace on .md files, ensure final newline, normalize CRLF to LF. Dry-run by default, --apply to write. Idempotent. Semantic smells (first-person, reserved words, placeholder markers, nested references, body >500 lines) remain manual. Integration tests expanded 17 -> 24 checks.

## 0.4.0 - 2026-04-13

- Add scripts/install_skill.py for validated copy to ~/.claude/skills/ or a project dir, with conflict detection and --dry-run/--force. Add scripts/tests/run_all.py integration test suite (17 checks covering validate_skill error codes, refactor_skill heuristics, version_log full cycle, and test_skill schema validation). All tests green.

## 0.3.0 - 2026-04-13

- Refresh subagent definition with 7-step pipeline + Claude A/B loop + expanded non-negotiables. Rewrite SKILL.md.tmpl with third-person / gerund / verbatim-trigger scaffolding and a pre-ship checklist. Add references/quickstart.md with a complete worked example (Mode: Create, csv-to-markdown scenario, start to finish).

## 0.2.1 - 2026-04-13

- Add dogfooding evals/cases.json (5 cases) and improve refactor_skill.py imperative-voice heuristic to recognize list/numbered/gate-prefixed imperative verbs.

## 0.2.0 - 2026-04-13

- Incorporate Anthropic official best-practices guide, Unix philosophy, and Anthropic engineering principles. Add design-principles.md. Expand best-practices.md, anatomy.md, testing.md, refactor-playbook.md, interview.md. Validator now enforces name<=64, reserved words, description<=1024, third-person, Windows paths, nested references, TOC on long refs. Mode: Create is now a 7-step pipeline with evaluation-driven development.

