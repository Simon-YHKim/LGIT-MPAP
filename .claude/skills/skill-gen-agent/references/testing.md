# Testing Skills

## Contents

- [Why test](#why-test)
- [Build evaluations first](#build-evaluations-first)
- [cases.json schema](#casesjson-schema)
- [grading.json schema](#gradingjson-schema)
- [Writing good assertions](#writing-good-assertions)
- [Grade the outcome, not the path](#grade-the-outcome-not-the-path)
- [Test across multiple models](#test-across-multiple-models)
- [Claude A / Claude B iterative development](#claude-a--claude-b-iterative-development)
- [Observing Claude in real use](#observing-claude-in-real-use)
- [Running the test harness](#running-the-test-harness)

## Why test

A skill that has never been invoked is a hypothesis, not a feature.
Testing converts hypotheses into facts. Tests catch:

- Description that under-triggers or over-triggers
- Scripts that crash on realistic inputs
- Workflow steps Claude cannot actually follow
- Library behaviour that drifted since the skill was written
- Drift between Claude model versions

## Build evaluations first

**Create evaluations *before* you write extensive documentation.**
This is the single most important testing habit. It ensures the
skill solves a real problem rather than an imagined one.

The evaluation-driven loop:

1. **Identify the gap.** Run Claude on representative tasks
   *without* a skill. Document the specific failures or missing
   context. These are the holes the skill should fill.
2. **Write 3 eval cases** targeting those gaps.
3. **Measure the baseline.** Record Claude's performance with no
   skill.
4. **Write minimal SKILL.md** — just enough content to pass the
   evals.
5. **Iterate.** Re-run, compare against baseline, refine.

This is the opposite of the "write the docs, then test" habit. It
forces every sentence in the skill to justify itself against a
concrete failure it prevents.

## cases.json schema

Stored at `<skill>/evals/cases.json`:

```json
{
  "skill": "skill-name",
  "version": "0.1.0",
  "cases": [
    {
      "id": "create-basic",
      "prompt": "Create a skill that converts CSV files to Markdown tables.",
      "fixtures": [],
      "assertions": [
        {
          "id": "has-frontmatter",
          "text": "The produced SKILL.md has YAML frontmatter with name, description, version."
        },
        {
          "id": "uses-csv-hook",
          "text": "The description mentions .csv as a trigger hook."
        },
        {
          "id": "has-workflow-section",
          "text": "SKILL.md contains a `## Workflow` section with numbered steps."
        }
      ]
    }
  ]
}
```

- `skill` — name of the skill under test
- `cases` — non-empty list of cases
- Each case: `id`, `prompt`, `assertions` (and optional `fixtures`
  describing required pre-state)

## grading.json schema

Produced by `test_skill.py`:

```json
{
  "skill": "skill-name",
  "run_at": "2026-04-13T12:00:00Z",
  "model": "claude-sonnet-4-6",
  "results": [
    {
      "case_id": "create-basic",
      "passed": 2,
      "failed": 1,
      "assertions": [
        {"id": "has-frontmatter", "passed": true,  "evidence": "found --- at line 1"},
        {"id": "uses-csv-hook",   "passed": true,  "evidence": "description contains '.csv'"},
        {"id": "has-workflow-section", "passed": false, "evidence": "section missing"}
      ]
    }
  ]
}
```

## Writing good assertions

- **Observable.** "SKILL.md has a `## Workflow` section" — yes.
  "The skill is well designed" — no.
- **Single fact per assertion.** Split compound checks into separate
  assertions.
- **Evidence-friendly.** Assertions should map to a grep, a regex,
  a file existence check, or a short human read. If you can't write
  a one-line grader for it, rephrase it.
- **Positive phrasing.** "Produced a file at X" is easier to grade
  than "did not fail to produce a file at X".

## Grade the outcome, not the path

**Critical rule from Article 1 (Anthropic eng philosophy):** grade
the *final state* of the world, not the sequence of tool calls
Claude used to get there. Claude often finds a cleverer path than
the one you expected; don't punish it for that.

- **Good:** "A file `output.csv` exists and contains N rows
  matching the schema."
- **Bad:** "Claude called tool_a, then tool_b, then tool_c in that
  order."

Path-based graders are brittle and reward rote behaviour. Outcome
graders reward real capability.

## Test across multiple models

A skill that works perfectly for Opus may be under-specified for
Haiku. Test with every model you plan to use:

- **Haiku** (fast, cheap): does the skill give enough guidance?
- **Sonnet** (balanced): is it clear and efficient?
- **Opus** (powerful): does it over-explain things Opus already
  knows?

If you target "whatever model the user has", lean toward more
explicit instructions — Haiku's floor dominates the design budget.

Record the model in `grading.json.model` for regression tracking.

## Claude A / Claude B iterative development

The most effective authoring loop uses two Claude instances:

- **Claude A** — the *author*. You work with it to design and
  refine the skill. Claude A understands skill structure and can
  critique its own output.
- **Claude B** — the *user*. A fresh Claude instance with the skill
  loaded. Runs real tasks. Reveals gaps by how it actually behaves.

The loop:

1. Work through a task with Claude A using normal prompting. Notice
   the context you repeatedly provide.
2. Ask Claude A to package that context as a skill.
3. Review Claude A's draft for conciseness: *"Remove the
   explanation of what X means — Claude already knows that."*
4. Test with Claude B on a similar task.
5. Observe where Claude B struggles, succeeds, makes unexpected
   choices.
6. Return to Claude A with specifics: *"When Claude B used the
   skill, it forgot to filter test accounts. The rule is mentioned
   but maybe not prominent enough?"*
7. Repeat.

Why it works: Claude A understands agent needs; you provide domain
expertise; Claude B reveals gaps through real behaviour; iteration
refines based on observation, not assumption.

## Observing Claude in real use

Pay attention to *how* Claude navigates the skill:

- **Unexpected exploration paths** — Claude reads files in an order
  you didn't anticipate. Your structure may not be as intuitive as
  you thought.
- **Missed connections** — Claude fails to follow references to
  important files. Your links might need to be more prominent.
- **Overreliance on one section** — Claude reads the same reference
  file every time. Consider moving it into SKILL.md.
- **Ignored content** — Claude never accesses a bundled file. It
  might be unnecessary or poorly signalled.

Iterate based on what Claude actually does, not on what you
imagine.

## Running the test harness

```bash
python scripts/test_skill.py <skill-path> \
    --cases <skill-path>/evals/cases.json \
    --out <skill-path>/evals/grading.json
```

Exit 0 iff all assertions pass. `--dry-run` only validates the
cases file.

The harness itself is a thin shell: it validates the schema and
scaffolds `grading.json`. The actual subagent invocation and
grading is done by the Skill-Gen Agent orchestrator, because
spawning Claude subagents is outside the stdlib-only scope of the
script. See `scripts/test_skill.py` for details.
