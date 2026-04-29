# Interview Question Bank

Use these questions during **Mode: Create** Step 1. Group by topic.
Ask at most 4 at a time.

## Contents

- [Round 1 — Purpose](#round-1--purpose-required)
- [Round 2 — Triggering](#round-2--triggering-required)
- [Round 3 — I/O](#round-3--io-required)
- [Round 4 — Dependencies](#round-4--dependencies-required)
- [Round 5 — Degrees of freedom](#round-5--degrees-of-freedom-required)
- [Round 6 — Models and determinism](#round-6--models-and-determinism-optional)
- [Round 7 — Scope and depth](#round-7--scope-and-depth-optional)
- [Gate for Step 1](#gate-for-step-1)

## Round 1 — Purpose (required)

1. **What should this skill do?** Answer in one sentence, starting
   with a verb. Example: "Convert a Markdown file to a styled PDF."
2. **Who is the user?** (you alone / your team / public)
3. **What problem does it solve that isn't solved by just asking
   Claude?** (determinism, speed, domain knowledge, tooling)

## Round 2 — Triggering (required)

1. **What exact phrases** would a user type that should fire this
   skill? Give 3–5. Include non-English phrases if relevant.
2. **Are there file types** that should trigger it? (e.g. `.xlsx`,
   `.ipynb`)
3. **Are there tools/libraries/APIs** whose name should trigger it?
4. **When should it NOT trigger?** (negative hints)

## Round 3 — I/O (required)

1. **What inputs** does it need? (files, URLs, prompts, env vars)
2. **What does it output?** (a new file, edits in place, a report
   in chat, a side effect on GitHub, etc.)
3. **Where does the output go?** (stdout, a file path, a PR)

## Round 4 — Dependencies (required)

1. **Python version** needed?
2. **Libraries** needed? Which ones, pinned versions?
3. **CLIs** needed? (ffmpeg, git, gh, …)
4. **Network access** needed? (APIs, doc fetching)
5. **MCP servers** needed? If yes, list them with the fully
   qualified tool names (`ServerName:tool_name`).

## Round 5 — Degrees of freedom (required)

This determines how prescriptive the skill should be. See
`best-practices.md` section 5.

1. **How fragile is the task?** Is there one right sequence, or
   many valid approaches?
2. **What's the cost of a wrong step?** (cheap-to-retry /
   destructive / irreversible)
3. **Should Claude be allowed to adapt?** If yes → prose
   instructions (high freedom). If no → exact commands, "do not
   modify" (low freedom). In between → parameterized script or
   pseudocode (medium freedom).

## Round 6 — Models and determinism (optional)

1. **Which models** will use this skill? (Haiku / Sonnet / Opus /
   all)
2. **How reproducible** must the output be? (byte-exact /
   semantically equivalent / creative)
3. **Are there test cases** you can provide? If yes, collect them
   now — they become `evals/cases.json`.
4. **What counts as a failure?** (crashes / wrong output / too
   slow)

If Haiku is in the target list, plan for more explicit instructions
in SKILL.md — Haiku's floor dominates the design budget.

## Round 7 — Scope and depth (optional)

1. **Modes?** Does the skill have multiple operating modes (create
   / refactor / validate / test / ...)?
2. **References?** Is there long-form domain knowledge (schemas,
   tables, playbooks) that should live in `references/`?
3. **Scripts?** Are there deterministic operations that should be
   Python scripts instead of Claude writing code each time?
4. **Disclosure pattern?** Which fits best — high-level guide,
   domain-specific organization, or conditional details? See
   `anatomy.md`.

## Gate for Step 1

Before advancing to Step 2, you must be able to:

- State the skill's purpose in one sentence with no "and...and...".
- List at least 3 concrete trigger phrases.
- Name the output format.
- Name the top dependency (or "none").
- Place the task on the freedom spectrum (high / medium / low).

If you can't, ask another round. Do not guess.
