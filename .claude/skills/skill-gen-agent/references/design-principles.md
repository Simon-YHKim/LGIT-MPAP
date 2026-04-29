# Design Principles

The *why* behind Skill-Gen Agent's rules. Distilled from Anthropic's
engineering philosophy for agentic systems and the Unix programming
philosophy. Read this when you need to decide a judgment call the
other reference files don't cover.

## Contents

- I. Decouple the brain from the hands
- II. Progressive disclosure is the main lever
- III. Single Point of Truth (SPOT)
- IV. Orthogonality
- V. Textuality
- VI. Transparency and fail-noisily
- VII. Least surprise
- VIII. Data over control flow
- IX. Ergonomic tool design
- X. Decouple policy from mechanism
- XI. Favor composition over frameworks
- XII. The model is already smart
- XIII. Evaluate the outcome, not the path
- XIV. Plan → validate → execute for risky work
- XV. Iterate with Claude in the loop
- Quick decision table

## I. Decouple the brain from the hands

Skills are brains; scripts are hands. SKILL.md contains instructions
Claude reads; `scripts/` contains deterministic code Claude executes.
Never mix them. When you put deterministic logic in the prose, Claude
re-derives it every invocation (slow, expensive, sometimes wrong).
When you put heuristics in a script, you lose Claude's judgment.

Corollary: **a script's output is the only thing that enters the
context window**, not its source. Push bulk data processing into
scripts so the context stays clean.

## II. Progressive disclosure is the main lever

The context window is a public good. Every token in `SKILL.md` is
paid on every invocation. Every token in `references/*.md` is paid
only when Claude explicitly reads it. Treat this asymmetry as the
primary tool for controlling cost and performance.

Heuristic: if a section is read in fewer than half of real
invocations, move it to `references/`. If Claude is reading the same
reference file every time, move *that* content into SKILL.md.

## III. Single Point of Truth (SPOT)

Any given fact, rule, schema, or workflow step must exist in **one**
authoritative place. Duplication is where drift starts. Use the
validator's broken-link and duplicate-content checks to catch it
early.

Corollary: when you update a rule, search the whole skill package
for the old version. One source of truth across SKILL.md, references,
scripts, and templates.

## IV. Orthogonality

A change to one module must not cause a surprise in another. Scripts
should be standalone (no cross-imports of mutable state). Reference
files should not assume the reader has read another reference file.
Each file pulls its own weight.

## V. Textuality

Everything in a skill is plain text: Markdown, YAML, JSON, Python. No
binary blobs, no serialized pickles, no proprietary formats. This
lets `grep`, `diff`, `git`, and Claude itself read and modify the
package freely.

## VI. Transparency and fail-noisily

Scripts must exit non-zero with a concrete stderr message on failure.
Validators must point to the exact file and line. Never swallow
errors. Never print "success" on a partial result. When Claude hits a
failure, it must be loud enough to react to.

Corollary: silence is golden on success. A script that prints
nothing on success and loudly on failure is easier to compose in a
pipeline than one that narrates every step.

## VII. Least surprise

An argparse script with `--help` beats a bespoke DSL. `kebab-case.md`
beats `KebabCase.md`. `scripts/foo.py` beats `bin/tools/foo`. Follow
the conventions Claude has seen a thousand times; save novelty for
where it actually helps.

## VIII. Data over control flow

Prefer a table, map, or config file to a cascade of if/else. When a
skill has multiple modes, describe them in a table at the top of
SKILL.md, then dispatch to a section per mode. When a validator has
many rules, encode them as data (a list of `(code, check_fn)`) rather
than one long function.

## IX. Ergonomic tool design (design for the model, not the human)

A tool in a skill context means a script the model invokes. Design
for the model:

- **Semantic identifiers** beat UUIDs in returned data.
- **Poka-yoke** (mistake-proofing): validate arguments up front,
  refuse ambiguous input, require uniqueness for destructive edits.
  Example: `str_replace` should refuse to run if `old_str` matches
  more than once.
- **Pushy error messages**: don't just say "failed", say what the
  model should do next. "Field 'foo' not found. Available: bar, baz."

## X. Decouple policy from mechanism

The *rules* of a skill (what to check, what to produce) are policy.
The *code* that enforces them is mechanism. Keep them in different
files so policy can evolve without touching mechanism. Example: the
validator's rubric lives in `best-practices.md`; the validator's
Python code lives in `validate_skill.py`. Changing a rule shouldn't
require a code change.

## XI. Favor composition over frameworks

A skill is a pile of small, composable pieces (SKILL.md, references,
scripts, templates). Don't introduce a "SkillBuilder" class or a
meta-framework. Claude composes them at runtime by reading and
executing.

## XII. The model is already smart

Don't explain what Claude already knows. Don't define "PDF" or
"YAML" or "kebab-case" — Claude has seen them. Instead, add the
context Claude *doesn't* have: your specific rules, your domain
constraints, your opinionated defaults.

Bad: "A JSON file is a text file containing structured data in the
JavaScript Object Notation format..."
Good: "Write the result to `evals/grading.json` using the schema in
`testing.md`."

## XIII. Evaluate the outcome, not the path

When grading whether a skill worked, check the final state (was the
right file produced? does the validator pass?), not the sequence of
tool calls. Claude often finds a cleverer path than the one you
expected; don't punish it for that.

## XIV. Plan → validate → execute for risky work

For any destructive or high-stakes operation (batch edits, mass
renames, schema migrations), emit an intermediate plan file, run a
validator on the plan, then execute. This pattern catches errors
while they're still cheap to fix and gives Claude an artifact to
iterate on without touching originals.

## XV. Iterate with Claude in the loop

The best way to improve a skill is to use it, observe where Claude
struggles, and feed those observations back into SKILL.md. Don't
guess what Claude needs — watch. Claude A (the author) edits the
skill based on what Claude B (the user) actually does. See
`testing.md` for the pattern.

---

## Quick decision table

When making a design call, ask:

| Question | Answer |
|---|---|
| Should this go in SKILL.md or references/? | Read on every invocation? → SKILL.md. Otherwise → references/. |
| Should Claude write this code every time, or should I script it? | Deterministic and non-creative? → script. Heuristic? → instructions. |
| Should I add this explanation? | Would Claude already know it? → omit. Is it specific to *my* domain? → include. |
| Should I add this check to the validator? | Does violating it break real skills? → yes. Is it taste? → no. |
| Should I add this option? | Does it change behavior meaningfully? → yes. Is it a knob for its own sake? → no. |
| Should I fail loudly or quietly? | Always loudly on failure, always quietly on success. |
| Should I add this to the workflow? | Does every real user need it? → yes. Is it an edge case? → push to a reference file. |
