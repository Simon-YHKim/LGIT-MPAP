# Anatomy of a Claude Code Skill

## Contents

- [Layer 1: SKILL.md](#layer-1-skillmd-always-in-context)
- [Layer 2: references](#layer-2-referencesmd-loaded-on-demand)
- [Layer 3: scripts](#layer-3-scripts)
- [Optional layers](#optional-layers)
- [How Claude actually reads skills](#how-claude-actually-reads-skills)
- [Progressive disclosure patterns](#progressive-disclosure-patterns)
- [One-level-deep rule](#one-level-deep-rule)
- [Table of contents for long references](#table-of-contents-for-long-references)
- [The 500-line rule](#the-500-line-rule)

A skill is a directory loaded into Claude's runtime when its
`description` matches the user's request. It has **three layers**,
each with different loading semantics.

```
my-skill/
├── SKILL.md          ← always loaded when triggered (the menu)
├── references/       ← loaded only when SKILL.md says to read them
│   ├── foo.md
│   └── bar.md
└── scripts/          ← executed by Claude via Bash; output enters context
    └── do_thing.py
```

## Layer 1: `SKILL.md` (always in context)

This file is loaded **in full** every time the skill triggers. Keep
it short — **under 500 lines**, ideally under 300. It is a **menu**,
not a manual.

### Frontmatter (required)

```yaml
---
name: my-skill
description: Third-person summary. Use when the user wants to <verb phrase>. Triggers on phrases like "<example>". Produces <output>.
version: 0.1.0
compatibility:
  - python>=3.9
---
```

Constraints (enforced by the validator):

- `name`: ≤ 64 chars, kebab-case, no `anthropic`/`claude` substrings
- `description`: ≤ 1024 chars, third-person, non-empty
- `version`: semver (X.Y.Z)
- `compatibility`: optional list of required tools/runtimes

### Body (required)

Minimum sections:

- `# <Name>` — H1 title
- `## Overview` — one paragraph: what this does and when to use it
- `## Workflow` — numbered imperative steps
- `## References` — pointers to deeper docs under `references/`
- `## Scripts` — table of scripts with purpose (if any)

Optional but recommended:

- `## Principles` — short list of guiding rules
- `## Examples` — 1–2 minimal input/output examples
- `## Mode: X` / `## Mode: Y` — one section per mode for multi-mode skills

## Layer 2: `references/*.md` (loaded on demand)

These are **not** in Claude's context by default. SKILL.md tells
Claude "read `references/foo.md` when you need X". This is
**progressive disclosure** and it's the main reason skills stay
lightweight even when covering complex domains.

**Good reference targets:**

- Long tables, schemas, enums
- Writing-style rubrics
- Playbooks for rare modes
- Deep domain knowledge only needed in edge cases
- Design rationale ("why we do it this way")

**Bad reference targets** (keep in SKILL.md instead):

- The main workflow
- Trigger conditions
- One-line facts
- Anything Claude reads on every invocation

## Layer 3: `scripts/*`

Executable code Claude runs via Bash. Scripts must:

- Exit **non-zero** on failure (so Claude sees the error)
- Print **useful** stderr messages
- Accept `--help` and document args
- Never prompt interactively (Claude can't answer stdin)
- Use stdlib where possible to avoid dependency hell
- Handle errors (solve, don't punt — see `best-practices.md`)

**Key property:** a script's **source** never enters the context
window. Only its **stdout/stderr** does. This makes scripts the best
place for any operation whose code is bulky but whose output is
small: validators, parsers, aggregators, formatters.

**Execute vs reference:** be explicit about what Claude should do:

- Execute: "Run `python scripts/analyze.py input.pdf`"
- Read as reference: "See `scripts/analyze.py` for the extraction
  algorithm"

Most scripts should be executed. If you find yourself asking Claude
to read a script as reference, the algorithm probably belongs in
`references/*.md` instead.

## Optional layers

- `templates/` — files copied into user projects during skill use
- `assets/` — static files (HTML, images, fonts)
- `evals/` — test cases (`cases.json`) and recorded results
- `CHANGELOG.md` — version history (managed by `version_log.py`)

## How Claude actually reads skills

1. **Metadata pre-loaded.** At session start, Claude loads the
   `name` and `description` of every installed skill into its system
   prompt. SKILL.md body is **not** loaded yet.
2. **Trigger fires.** When the user's request matches a skill's
   description, Claude reads `SKILL.md` in full via Read/Bash.
3. **References on demand.** Claude follows `references/*.md` links
   only when SKILL.md tells it to or when it needs the content.
4. **Scripts execute.** Scripts run via Bash. Source doesn't enter
   context; stdout/stderr does.
5. **No context penalty for unopened files.** Reference files and
   datasets don't cost tokens until Claude actually reads them.

This filesystem-based architecture is why progressive disclosure
works: Claude navigates the skill directory like a filesystem and
selectively loads exactly what each task requires.

## Progressive disclosure patterns

There are three canonical patterns. Pick the one that matches your
content.

### Pattern 1 — High-level guide with references

For skills with one main workflow and a few advanced topics.

```markdown
# PDF Processing

## Quick start

    import pdfplumber
    with pdfplumber.open("file.pdf") as pdf:
        text = pdf.pages[0].extract_text()

## Advanced features

**Form filling:** see `references/forms.md`
**API reference:** see `references/api.md`
**Examples:** see `references/examples.md`
```

Claude reads `forms.md`, `api.md`, or `examples.md` only when needed.

### Pattern 2 — Domain-specific organization

For skills spanning multiple independent domains. Organize by domain
so Claude reads only the relevant slice.

```
bigquery-skill/
├── SKILL.md               (overview + navigation)
└── references/
    ├── finance.md         (revenue, billing)
    ├── sales.md           (pipeline, accounts)
    ├── product.md         (usage, features)
    └── marketing.md       (campaigns, attribution)
```

```markdown
# BigQuery Data Analysis

## Available datasets

**Finance:** revenue, ARR, billing → `references/finance.md`
**Sales:** opportunities, pipeline → `references/sales.md`
**Product:** API usage, adoption → `references/product.md`
**Marketing:** campaigns → `references/marketing.md`
```

When the user asks about sales metrics, Claude reads `sales.md`
only — not finance or marketing. Keeps tokens tight.

### Pattern 3 — Conditional details

For skills with common and rare flows in the same domain.

```markdown
# DOCX Processing

## Creating documents

Use docx-js for new documents. See `references/docx-js.md`.

## Editing documents

For simple edits, modify the XML directly.

**For tracked changes:** see `references/redlining.md`
**For OOXML details:** see `references/ooxml.md`
```

Claude reads `redlining.md` or `ooxml.md` only when the user needs
those features.

## One-level-deep rule

**Reference files must not link to other reference files.** When
Claude follows a nested reference, it may partial-read (`head -100`)
instead of reading in full, producing incomplete context. Always
link directly from `SKILL.md` to each reference.

**Bad (too deep):**
```
SKILL.md → references/advanced.md → references/details.md → (the actual info)
```

**Good (flat):**
```
SKILL.md → references/advanced.md
SKILL.md → references/details.md
```

The validator warns when a reference file contains a link to
another reference file.

## Table of contents for long references

If a reference file exceeds 100 lines, put a `## Contents` section
at the top listing the main headings. Claude may partial-read long
files; a TOC guarantees the outline is always visible even when the
body isn't.

```markdown
# API Reference

## Contents

- Authentication and setup
- Core methods
- Advanced features
- Error handling
- Examples

## Authentication and setup
...
```

## The 500-line rule

If `SKILL.md` exceeds 500 lines, you almost certainly have content
that belongs in `references/`. The validator warns at 400 lines and
errors at 500. Use the refactor analyzer to find reference-like
sections (`python scripts/refactor_skill.py <path>`).
