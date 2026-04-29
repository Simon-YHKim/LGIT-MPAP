# Quickstart: Build a Skill End-to-End

A worked example that walks through Mode: Create start to finish.
Use this when you need a concrete template for a minimal but real
skill. For the rules, see `best-practices.md`. For the rationale,
see `design-principles.md`.

## Contents

- [Scenario](#scenario)
- [Step 1 — Interview](#step-1--interview)
- [Step 2 — Baseline & evals](#step-2--baseline--evals)
- [Step 3 — File plan](#step-3--file-plan)
- [Step 4 — Scaffold](#step-4--scaffold)
- [Step 5 — Validate](#step-5--validate)
- [Step 6 — Test](#step-6--test)
- [Step 7 — Version & package](#step-7--version--package)
- [Post-ship: observe in real use](#post-ship-observe-in-real-use)

## Scenario

The user says: "Make me a skill that converts CSV files to Markdown
tables. I want to say 'csv to md' or 'convert this csv' and have
Claude run it."

## Step 1 — Interview

Ask the four required rounds. The user's answers:

1. **What:** "Convert a CSV file to a Markdown table and save it as
   a new .md file next to the original."
2. **When:** `"csv to md"`, `"convert this csv"`, `"csv → md"`,
   `.csv` file types, pandas mentions.
3. **Output:** a new `.md` file at the same path with `.csv`
   replaced by `.md`.
4. **Dependencies:** Python stdlib only (csv module).
5. **Freedom:** low-medium — the operation is deterministic, but
   the user may want column alignment options.
6. **Target models:** all.

**Gate pass:** purpose is one sentence ("Convert a CSV file to a
Markdown table and save it as a .md file next to the original.").
3 trigger phrases. Output named. Dependency: "stdlib".

## Step 2 — Baseline & evals

Before writing SKILL.md, design the evals.

Run the task on Claude **without** any skill: Claude typically
writes ad-hoc code that ignores edge cases (no header row, commas
inside quoted fields, empty CSV). That's the gap to close.

Write `evals/cases.json`:

```json
{
  "skill": "converting-csv-to-markdown",
  "version": "0.1.0",
  "cases": [
    {
      "id": "basic",
      "prompt": "Convert this file to a Markdown table: sample.csv",
      "fixtures": ["sample.csv with 3 cols, 5 rows, plain values"],
      "assertions": [
        {"id": "md-exists", "text": "A file sample.md is created alongside sample.csv"},
        {"id": "has-header-sep", "text": "The Markdown table has a header row and a `|---|---|---|` separator"},
        {"id": "row-count", "text": "The Markdown table has exactly 5 data rows"}
      ]
    },
    {
      "id": "quoted-commas",
      "prompt": "Convert quoted.csv to Markdown.",
      "fixtures": ["quoted.csv containing a field with a comma inside quotes"],
      "assertions": [
        {"id": "preserves-quoted-field", "text": "The comma inside the quoted field is preserved, not split into two columns"}
      ]
    },
    {
      "id": "empty",
      "prompt": "Convert empty.csv to Markdown.",
      "fixtures": ["empty.csv is an empty file"],
      "assertions": [
        {"id": "handles-empty", "text": "The skill exits with a clear message and does not crash"}
      ]
    }
  ]
}
```

**Gate pass:** `test_skill.py --dry-run` validates the schema.

## Step 3 — File plan

Show the user:

```
converting-csv-to-markdown/
├── SKILL.md                 # 70-line menu, triggers + workflow
├── scripts/
│   └── csv_to_md.py         # deterministic converter (stdlib only)
└── evals/
    └── cases.json           # 3 test cases from Step 2
```

No `references/*.md` — the skill is too small. Disclosure pattern:
Pattern 1 (high-level guide), minus the reference links.

**Gate pass:** user approves the plan.

## Step 4 — Scaffold

Copy `templates/SKILL.md.tmpl` and fill in:

```markdown
---
name: converting-csv-to-markdown
description: Converts CSV files to Markdown tables. Use when the user wants to turn a .csv into a Markdown table, or says "csv to md", "convert this csv", "csv → md". Produces a new .md file alongside the input. Handles quoted fields and empty files gracefully. Use whenever a .csv file is mentioned together with Markdown output.
version: 0.1.0
compatibility:
  - python>=3.9
---

# Converting CSV to Markdown

## Overview

Converts a CSV file to a GitHub-flavored Markdown table and writes
the result next to the source as `<name>.md`. Handles quoted fields
containing commas and empty files.

## Workflow

1. Resolve the input path from the user's message. Refuse anything
   that is not a regular file ending in `.csv`.
2. Run: `python scripts/csv_to_md.py <input.csv>`. The script
   writes `<input>.md` alongside and exits non-zero on error.
3. If the script exits non-zero, read stderr, explain the problem
   to the user, and stop. Do not retry silently.
4. Report the output path and the number of rows written.

## Principles

- **Stdlib only.** The `csv` module handles quoted fields
  correctly; don't reach for pandas just for a table.
- **Fail loud, succeed quiet.** The script writes the output file
  and prints nothing on success. Errors go to stderr with a
  concrete message.

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/csv_to_md.py` | Read a CSV file and write an aligned GitHub-flavored Markdown table next to it. |
```

And `scripts/csv_to_md.py`:

```python
#!/usr/bin/env python3
"""Convert a CSV file to a Markdown table written next to the source.

Usage:
    csv_to_md.py <input.csv>
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def convert(input_path: Path) -> Path:
    if input_path.suffix.lower() != ".csv":
        raise SystemExit(f"error: {input_path} is not a .csv file")
    if not input_path.is_file():
        raise SystemExit(f"error: {input_path} not found")

    rows: list[list[str]] = []
    with input_path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            rows.append(row)

    output_path = input_path.with_suffix(".md")

    if not rows:
        output_path.write_text("(empty table)\n", encoding="utf-8")
        return output_path

    header, *body = rows
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for r in body:
        # Pad short rows so the table stays rectangular.
        r = r + [""] * (len(header) - len(r))
        lines.append("| " + " | ".join(r[: len(header)]) + " |")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    args = p.parse_args(argv)
    convert(args.input)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## Step 5 — Validate

```bash
python scripts/validate_skill.py path/to/converting-csv-to-markdown
```

Expected output:

```
Validating: path/to/converting-csv-to-markdown

  [INFO   ] I006: description score 0.85 (SKILL.md)

  0 error(s), 0 warning(s)
  Result: OK
```

**Gate pass:** validator exits 0.

## Step 6 — Test

```bash
python scripts/test_skill.py path/to/converting-csv-to-markdown \
    --cases path/to/converting-csv-to-markdown/evals/cases.json \
    --out path/to/converting-csv-to-markdown/evals/grading.json
```

For each case, spawn a subagent with the skill loaded, run the
prompt against a fixture file, and grade each assertion against
the final state of the output file (outcome, not path).

**Gate pass:** all 3 cases pass. If `empty` fails because the
script crashes, fix it and re-run.

## Step 7 — Version & package

```bash
python scripts/version_log.py path/to/converting-csv-to-markdown \
    init --version 0.1.0 --message "Initial release"
```

Report to the user:

- **Path:** `path/to/converting-csv-to-markdown/`
- **Description:** "Converts CSV files to Markdown tables..."
- **How to load:** `cp -r path/to/converting-csv-to-markdown/ ~/.claude/skills/`
- **Baseline grading:** 3/3 cases passing
- **Next steps:** Observe Claude in real use on a fresh .csv file,
  note any gaps, feed them back into SKILL.md using the Claude A /
  Claude B loop from `testing.md`.

## Post-ship: observe in real use

Open a fresh Claude session. Drop a `.csv` file into it. Ask:
"convert this csv to md". Watch whether:

- The skill fires at all (trigger tuning)
- Claude runs the script or writes inline code (if inline, the
  description may be under-triggering — add more hooks)
- Claude reports the row count correctly (workflow step 4)
- Claude handles a weird input (e.g. a `.csv` with no header row)

Return each observation to the skill as a new assertion or a
SKILL.md clarification. That's the iteration loop.
