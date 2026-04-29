---
name: review
description: Use when the user asks for a code review or feedback on code—triggers include "review this", "code review", "리뷰해줘", "check this code", "feedback on my code", "is this good". Produces a prioritized review with severity levels (blocker / major / minor / nit) and actionable fix suggestions.
version: 1.0.0
author: general-dev
---

# Code Review Skill

Provide actionable, prioritized feedback on code changes.

## Workflow

1. **Identify scope** — What is being reviewed?
   - Uncommitted changes: `git diff` (and `git diff --staged`)
   - Branch vs main: `git diff main...HEAD`
   - Specific files: read them in full
   - PR: fetch the diff via the GitHub MCP tools

2. **Read context** — Don't review in isolation:
   - Read the files being modified, not just the diff hunks
   - Check related tests and callers
   - Understand the intent before judging

3. **Review checklist** — Evaluate against:

   **Correctness**
   - Logic errors, off-by-one, null/undefined handling
   - Race conditions, concurrency issues
   - Error handling at boundaries

   **Security**
   - Input validation, injection risks (SQL, XSS, command)
   - Secrets in code, insecure defaults
   - Authentication/authorization checks

   **Maintainability**
   - Naming clarity
   - Function/file size and single responsibility
   - Dead code, duplicate code
   - Unnecessary complexity or premature abstraction

   **Testing**
   - Are tests included? Do they cover edge cases?
   - Are tests deterministic?

   **Performance** (only if it matters here)
   - N+1 queries, unnecessary loops, memory leaks

4. **Report format** — Group by severity:
   - 🔴 **Blocking** — must fix before merge
   - 🟡 **Should fix** — important but not blocking
   - 🟢 **Nit / suggestion** — optional polish

   For each issue: cite `file_path:line_number`, explain the problem, and propose a concrete fix.

## Principles

- Be specific. "This is confusing" is useless; "rename `x` to `userCount` because..." is actionable.
- Praise good patterns when you see them.
- Don't nitpick style if a formatter exists — let the tool handle it.
- Distinguish facts ("this throws on null") from opinions ("I prefer guard clauses").
