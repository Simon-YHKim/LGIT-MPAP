# Refactor Playbook

Common smells in existing skills and how to fix them. The refactor
analyzer (`scripts/refactor_skill.py`) detects many of these
automatically, and its `--fix` mode can apply the safe mechanical
ones without human judgment.

## Auto-fix mode

```bash
# Dry-run: report pending fixes, exit 1 if any
python scripts/refactor_skill.py <skill> --fix

# Apply the fixes
python scripts/refactor_skill.py <skill> --fix --apply
```

Safe mechanical fixes (applied automatically):

| Smell | Fix |
|---|---|
| Windows backslash paths in SKILL.md (E011) | replace `\` with `/` inside quoted paths |
| Long reference file (>100 lines) without TOC (W013) | insert `## Contents` block listing all H2 headings |
| Trailing whitespace on any line of a `.md` file | strip |
| Missing trailing newline on a `.md` file | add |
| CRLF line endings | normalize to LF |

Fix mode is **idempotent**: a second pass on an already-fixed skill
produces zero changes and exits 0.

Fix mode does **not** touch semantic smells — first-person
descriptions, reserved names, TODO markers, nested references, and
>500-line bodies all require human judgment and are surfaced by
`--analyze` (the default mode) for manual repair.

## Smell: SKILL.md is over 500 lines

**Fix:** Move long sections to `references/`. Candidates:

- Tables of schemas/enums → `references/schemas.md`
- Detailed writing rubrics → `references/style.md`
- Rare-mode playbooks → `references/<mode>.md`

Replace moved content in SKILL.md with a one-line pointer:
"See `references/schemas.md` when you need X."

## Smell: Description is vague or short

Symptom: validator reports description score < 0.6, or the user
says "Claude never picks up my skill".

**Fix:**

1. Rewrite to start with "Use when…".
2. Write in third person.
3. Add 3+ verbatim trigger phrases.
4. Add concrete hooks (file extensions, tool names).
5. Add the output format.

See `best-practices.md` sections 2.1–2.6.

## Smell: First-person description

Symptom: description contains "I can help...", "I'll...", "you can
use this to...". Validator flags this.

**Fix:** Rewrite in third person. "Processes Excel files..." not "I
process Excel files...".

## Smell: Reserved word in name

Symptom: `name` contains `anthropic` or `claude`. These are
reserved and the validator errors.

**Fix:** Rename. `anthropic-helper` → `api-helper`; `claude-tools`
→ `llm-tools`.

## Smell: Description over 1024 characters

Symptom: validator errors. Description is being clipped in the
system prompt.

**Fix:** Trim. Keep the "Use when..." clause, the top 3 trigger
phrases, and the output format. Push the rest into SKILL.md body.

## Smell: Name exceeds 64 characters

**Fix:** Shorten. Acronyms and gerund forms usually help.

## Smell: Descriptive voice instead of imperative

Symptom: sections full of "You might want to read the file" / "This
function can be used to…".

**Fix:** Rewrite in imperative: "Read the file." / "Use this
function to…". Run `refactor_skill.py --analyze` to see the
imperative / descriptive ratio per section.

## Smell: Claude rewrites the same code every invocation

Symptom: SKILL.md has a long code block Claude copies and runs;
correctness is suspect; tokens are wasted.

**Fix:** Extract to `scripts/<name>.py` with argparse. In SKILL.md
just say `Run: python scripts/<name>.py <args>`. The script's
source no longer enters context — only its output does.

## Smell: Library behaviour hard-coded from memory

Symptom: the skill references API calls that no longer exist, or
wrong signatures.

**Fix:**

1. Identify the authoritative source (`mcp__*query-docs`, official
   docs site).
2. Add a note in SKILL.md: "Before coding, fetch current docs with
   `mcp__*query-docs`."
3. Pin the library in `compatibility`.

## Smell: No test cases

Symptom: the skill has never been evaluated; users report
intermittent failures.

**Fix:**

1. Create `evals/cases.json` with 2–3 real prompts.
2. Run `test_skill.py`.
3. Record the baseline grading.

## Smell: No version history

**Fix:** `python scripts/version_log.py <skill> init --version 0.1.0 --message "..."`.

## Smell: Skill triggers on unrelated requests (over-triggering)

**Fix:**

1. Narrow the "Use when…" clause.
2. Add negative hints: "Do NOT use for general X."
3. Remove overly broad keywords from the description.
4. Re-test with the eval cases and verify it still fires on the
   *right* ones.

## Smell: SKILL.md has placeholder TODOs

Symptom: validator fails with `TODO` / `FIXME` / `<placeholder>`.

**Fix:** Finish them or delete them. Never ship TODOs.

## Smell: Broken reference link

Symptom: SKILL.md references a file that doesn't exist.

**Fix:** Create the file, or remove the pointer from SKILL.md.

## Smell: Nested references (depth > 1)

Symptom: `references/a.md` links to `references/b.md`. When Claude
follows nested refs it may partial-read, producing incomplete
context. Validator flags this.

**Fix:** Flatten. Every reference file must be reachable directly
from SKILL.md in one hop. If the nested reference really is
needed, inline it or promote it to a sibling file linked from
SKILL.md.

## Smell: Long reference file with no TOC

Symptom: a `references/*.md` file is >100 lines but has no
`## Contents` section at the top.

**Fix:** Add a TOC listing the H2 headings. Guarantees Claude sees
the outline even on partial reads.

## Smell: Windows-style paths

Symptom: `scripts\foo.py` or `references\bar.md` in SKILL.md.
Breaks on Unix. Validator errors.

**Fix:** Replace backslashes with forward slashes. Always forward
slashes, even in a Windows-only skill.

## Smell: Voodoo constants in scripts

Symptom: `TIMEOUT = 47`, `RETRIES = 5` with no comment explaining
why.

**Fix:** Either document the choice with a comment ("HTTP timeouts
typically complete within 30s; longer accounts for slow CI") or
move the value to a config constant with a named rationale.

## Smell: Scripts punt on errors

Symptom: a script raises `FileNotFoundError` and relies on Claude
to handle it. Produces flaky behaviour.

**Fix:** Catch and resolve in the script. Initialize missing files
with defaults, return a safe value, or exit with a clear error
message telling Claude what to do next.

## Smell: Time-sensitive information

Symptom: SKILL.md says "before August 2025, use the v1 API; after,
use v2".

**Fix:** Document the *current* method as the primary path. Move
deprecated methods into a collapsed "Old patterns" section with a
deprecation date. Never branch on real-time dates.

## Smell: Inconsistent terminology

Symptom: the skill mixes "API endpoint" / "URL" / "route" / "path"
for the same concept.

**Fix:** Pick one term, grep the skill package, replace the others.
Claude's pattern matcher degrades with synonyms.

## Smell: Too many options presented

Symptom: "Use pypdf or pdfplumber or PyMuPDF or pdf2image or …".

**Fix:** Pick one default and document it. Offer at most one escape
hatch for a specific edge case. "Use pdfplumber for text. For
scanned PDFs requiring OCR, use pdf2image + pytesseract."
