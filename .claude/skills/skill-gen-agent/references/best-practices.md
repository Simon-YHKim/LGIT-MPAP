# Best Practices for Claude Code Skills

Distilled from Anthropic's official skill authoring guide
(platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices),
from the skill-creator project, and from Skill-Gen Agent's own
experience. These are the rules `validate_skill.py` enforces.

For the *reasoning* behind these rules, read
`design-principles.md`.

## Contents

- 1. Frontmatter constraints
- 2. Description rules (third person, "Use when", triggers, output, pushy, ≤1024)
- 3. Naming (gerund form, kebab-case, reserved words)
- 4. Progressive disclosure (500-line rule, pattern selection, one level deep, TOC)
- 5. Degrees of freedom (high / medium / low)
- 6. Concise is key (Claude is already smart)
- 7. Writing style (imperative, consistent terminology, no time-sensitive info)
- 8. Script authoring rules (solve-don't-punt, no voodoo constants, forward slashes, stdlib)
- 9. Workflow patterns (checklist, feedback loop, plan-validate-execute, template, examples, conditional)
- 10. MCP tool references (fully qualified names)
- 11. Trigger tuning (under vs over)
- 12. Validator-enforced rules

## 1. Frontmatter constraints (hard)

```yaml
---
name: kebab-case-name        # ≤ 64 chars, [a-z0-9-], must not contain
                             # "anthropic" or "claude"
description: Third-person... # ≤ 1024 chars, non-empty
version: 0.1.0               # semver
compatibility:               # optional
  - python>=3.9
---
```

Validator errors on any violation of these.

## 2. Description rules

The description is the **only** signal Claude uses to decide whether
to load the skill. It shares the system prompt with 100+ other
skills' metadata. Treat it as the highest-leverage field in the
package.

### 2.1 Write in third person

The description is injected into the system prompt. First-person
("I can help...") and second-person ("you can use...") confuse the
matcher.

- **Good:** "Processes Excel files and generates reports. Use when
  the user mentions .xlsx, pivot tables, or spreadsheet analysis."
- **Bad:** "I can help you process Excel files."
- **Bad:** "You can use this to process Excel files."

### 2.2 Lead with "Use when..."

This pattern primes Claude's matcher to pattern-match against user
intent. It is an empirical best practice, not a style rule.

### 2.3 Include verbatim trigger phrases

Claude's matcher loves concrete phrases over abstract ones. Include:

- Literal user phrases in quotes: `"convert xlsx"`, `"스킬 만들어"`
- File extensions: `.xlsx`, `.pdf`, `.ipynb`
- Tool/library names: `pandas`, `BigQuery`, `GitHub`
- API names: `Claude API`, `Anthropic SDK`

### 2.4 State the output

"Produces a ...", "Returns ...", "Writes ...", "Edits ... in place".
This helps Claude pick between two similar skills.

### 2.5 Be pushy (but not greedy)

Under-triggering is worse than over-triggering. A missed trigger is
invisible; an over-trigger is merely annoying. Use "Use whenever...",
"always", "proactively" for the primary trigger case. But add
negative hints ("Do NOT use for general X") if the skill really
shouldn't fire on adjacent requests.

### 2.6 Keep it under 1024 characters

Hard cap from the spec. Aim for 200–600 chars — long enough to carry
triggers and output, short enough to not bloat the system prompt.

## 3. Naming

### 3.1 Gerund form preferred

Anthropic's official guidance recommends gerund form (verb-ing) for
skill names:

- `processing-pdfs`, `analyzing-spreadsheets`, `managing-databases`,
  `testing-code`, `writing-documentation`

Acceptable alternatives:

- Noun phrase: `pdf-processing`, `spreadsheet-analysis`
- Action-verb: `process-pdfs`, `analyze-spreadsheets`

### 3.2 Avoid

- Vague: `helper`, `utils`, `tools`, `common`
- Generic: `documents`, `data`, `files`
- Reserved: anything containing `anthropic` or `claude`
- Inconsistent patterns across your skill library

### 3.3 Kebab-case, all lowercase

`[a-z][a-z0-9]*(-[a-z0-9]+)*`. The directory name, the frontmatter
`name`, and the package identifier must all match.

## 4. Progressive disclosure

### 4.1 The 500-line rule

`SKILL.md` body (everything after the frontmatter) must stay under
500 lines. Soft limit 400. This is not a style rule — it's the
practical ceiling where Claude can still treat the file as "in
context" on every invocation.

### 4.2 Pattern selection

See `anatomy.md` for the three canonical patterns (high-level with
references, domain-specific, conditional-details). Pick the one that
matches your content.

### 4.3 One level deep

`references/*.md` should not link to other reference files. When
Claude follows a nested reference, it may use `head -100` to
preview, which produces incomplete context. Every reference file
should be reachable directly from `SKILL.md` in one hop.

### 4.4 Long reference files need a TOC

If a reference file exceeds 100 lines, put a table of contents at
the top. Claude may partial-read long files, and a TOC guarantees
the outline is always seen even when the body isn't.

## 5. Degrees of freedom

Match instruction specificity to task fragility.

| Freedom | When | Form |
|---------|------|------|
| **High** | Multiple valid approaches, context-dependent | Prose describing the goal |
| **Medium** | Preferred pattern exists, configuration varies | Pseudocode or parameterized script |
| **Low** | Fragile, error-prone, sequence-critical | Exact commands, "do not modify" |

Analogy: Claude is a robot on a path. Narrow bridge with cliffs →
low freedom (exact commands). Open field → high freedom (general
direction). Choosing the wrong level is a common failure mode: too
restrictive and Claude can't adapt, too loose and Claude invents
destructive approaches.

## 6. Concise is key

### 6.1 Default assumption: Claude is already very smart

Don't explain what Claude knows. Don't define standard formats. Don't
recap basic programming. For each line, ask:

- Does Claude really need this?
- Can I assume Claude knows this?
- Does this paragraph justify its token cost?

### 6.2 Good vs bad

**Good (≈50 tokens):**
```markdown
## Extract PDF text

Use pdfplumber:

    import pdfplumber
    with pdfplumber.open("file.pdf") as pdf:
        text = pdf.pages[0].extract_text()
```

**Bad (≈150 tokens):**
> PDF (Portable Document Format) files are a common file format that
> contains text, images, and other content. To extract text from a
> PDF, you'll need to use a library. There are many libraries
> available, but pdfplumber is recommended because...

The concise version trusts Claude to know what PDFs are.

## 7. Writing style

### 7.1 Imperative voice

"Read the file. Parse the YAML." Not "You should read..." or "The
file can be read by...". Third-person exposition in descriptions;
imperative in workflows.

### 7.2 Consistent terminology

Pick one term and stick with it. Don't mix "API endpoint" / "URL" /
"route" / "path". Don't mix "field" / "box" / "element". Don't mix
"extract" / "pull" / "get". Claude's pattern matching degrades with
synonyms.

### 7.3 No time-sensitive information

Never write "before August 2025, use X; after, use Y". Dates rot.
Instead, document the current method in the main body and push
deprecated methods into an "Old patterns" collapsible section with
a deprecation date.

### 7.4 No hedging

"Do X" > "You might consider doing X". "Run the validator" > "It
would be a good idea to consider running the validator".

## 8. Script authoring rules

### 8.1 Solve, don't punt

Handle error conditions in the script. Don't throw and "let Claude
figure it out". Scripts are mechanism, Claude is policy — catching
`FileNotFoundError` is mechanism's job.

```python
# Good
try:
    text = path.read_text()
except FileNotFoundError:
    path.write_text("")  # initialize with default
    text = ""

# Bad
text = open(path).read()  # will crash; good luck, Claude
```

### 8.2 No voodoo constants

Magic numbers need justification. If you can't explain why, Claude
certainly can't.

```python
# Good
# HTTP requests typically complete within 30s; longer accounts for
# slow CI networks.
REQUEST_TIMEOUT = 30

# Bad
TIMEOUT = 47  # why 47?
```

### 8.3 Don't assume packages are installed

When SKILL.md tells Claude to run a script that needs a library,
either: (a) pin it in `compatibility`, (b) tell Claude to install it
first, or (c) have the script `ImportError`-catch with a clear
install hint.

### 8.4 Forward slashes only

`scripts/helper.py`, never `scripts\helper.py`. Windows-style paths
break on Unix. Validator catches this.

### 8.5 Exit codes matter

`0` = success, non-zero = failure. Claude checks the exit code; a
script that prints "ERROR" but exits 0 will be treated as success.

### 8.6 Stdlib where possible

Every external dependency is a failure mode. The validator, refactor
analyzer, and version log scripts in this skill are all pure stdlib
for a reason.

## 9. Workflow patterns

### 9.1 Checklist pattern

For complex, multi-step workflows, provide a copyable checklist
Claude can paste into its reply and tick off. This prevents skipped
steps and gives the user visibility.

```markdown
## Workflow

Copy this checklist and tick off as you go:

    - [ ] Step 1: analyze
    - [ ] Step 2: plan
    - [ ] Step 3: validate
    - [ ] Step 4: execute
    - [ ] Step 5: verify
```

### 9.2 Feedback loop (validate → fix → repeat)

Any quality-critical step should loop until it passes:

```markdown
1. Make edits
2. Run validator
3. If validator fails:
   - Read error carefully
   - Fix the specific issue
   - Go to step 2
4. Proceed only when validator passes
```

### 9.3 Plan-validate-execute for risky work

For batch operations, destructive edits, or anything hard to
reverse: emit an intermediate plan file, run a validator on the plan,
then execute. Catches errors before they touch originals.

### 9.4 Template pattern

Provide output templates. Match strictness to need:

- **Strict** ("ALWAYS use this exact structure") for API responses,
  data formats, anything a downstream parser reads.
- **Flexible** ("Use this as a sensible default, adapt as needed")
  for analysis reports, summaries, creative output.

### 9.5 Examples pattern

If output quality depends on tone/style, show input/output pairs.
Examples teach more than descriptions.

### 9.6 Conditional workflow pattern

For skills with multiple modes, dispatch up front:

```markdown
1. Determine task type:
   **Creating new?** → follow "Creation workflow"
   **Editing existing?** → follow "Editing workflow"
```

### 9.7 Avoid too many options

Present one default with one escape hatch. Not "use A or B or C or
D". The default should be opinionated: "Use pdfplumber for text.
For scanned PDFs requiring OCR, use pdf2image + pytesseract instead."

## 10. MCP tool references

When a skill invokes MCP tools, use the fully qualified form
`ServerName:tool_name`. Without the prefix, Claude may fail to
resolve the tool when multiple MCP servers are available.

```markdown
Use the BigQuery:bigquery_schema tool to retrieve table schemas.
Use the GitHub:create_issue tool to create issues.
```

## 11. Trigger tuning

- **Under-triggering** (skill never fires): description too vague,
  missing verbatim phrases, missing file/tool hooks. Make it pushier.
- **Over-triggering** (skill fires on unrelated tasks): description
  too broad. Narrow the "Use when..." clause, add negative hints,
  remove overly general keywords.

## 12. Validator-enforced rules

The following are hard errors (validator fails):

- Missing or malformed frontmatter
- Missing required fields (`name`, `description`, `version`)
- `name` not kebab-case, >64 chars, or contains `anthropic`/`claude`
- `description` empty or >1024 chars
- `version` not valid semver
- SKILL.md body > 500 lines
- TODO / FIXME / `<placeholder>` markers
- Broken relative links
- Windows backslash paths in SKILL.md
- Reference file linking to another reference file (depth > 1)
- First-person description ("I can", "I'll", "I help")

Warnings (validator passes but flags):

- SKILL.md body > 400 lines
- `description` score below 0.6 on the rubric
- `name` doesn't match directory name
- Long reference file (>100 lines) without a TOC
- Description near the 1024 char cap
