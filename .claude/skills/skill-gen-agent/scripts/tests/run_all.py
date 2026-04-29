#!/usr/bin/env python3
"""Integration test runner for Skill-Gen Agent scripts.

Usage:
    python scripts/tests/run_all.py [--verbose]

Builds temporary fixture skills in a tmp dir, runs each helper
script against them, and checks exit codes + expected output
fragments. Pure stdlib. Deletes all fixtures on exit.

Exit code 0 iff every test passes.

Tests performed:

    1. validate_skill on a clean skill           → exit 0
    2. validate_skill on every negative fixture  → exit 1 + expected code
    3. refactor_skill on a healthy skill         → "No refactor needed"
    4. refactor_skill on a bloated skill         → suggests moving
    5. version_log init + bump + show           → correct sequence
    6. test_skill --dry-run on valid cases.json  → "dry-run ok"
    7. test_skill --dry-run on broken cases.json → exit 2
    8. validator catches each error code we advertise in
       best-practices.md (one fixture per code)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
PY = sys.executable


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Runner:
    tmp: Path
    verbose: bool = False
    results: list[TestResult] = field(default_factory=list)

    # -- helpers --------------------------------------------------

    def run(self, *args: str, check: bool = False
            ) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [PY, *args],
            capture_output=True,
            text=True,
            check=check,
        )
        if self.verbose:
            print(f"$ {' '.join(str(a) for a in args)}")
            if proc.stdout:
                print(proc.stdout)
            if proc.stderr:
                print(proc.stderr, file=sys.stderr)
        return proc

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append(TestResult(name, passed, detail))
        marker = "PASS" if passed else "FAIL"
        print(f"  [{marker}] {name}" + (f" — {detail}" if detail else ""))

    def make_skill(self, name: str, skill_md: str,
                   refs: dict[str, str] | None = None) -> Path:
        skill = self.tmp / name
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text(skill_md, encoding="utf-8")
        if refs:
            (skill / "references").mkdir(exist_ok=True)
            for fname, content in refs.items():
                (skill / "references" / fname).write_text(
                    content, encoding="utf-8")
        return skill

    # -- individual tests -----------------------------------------

    def t_validate_clean(self) -> None:
        skill = self.make_skill(
            "clean-skill",
            CLEAN_SKILL_MD,
        )
        p = self.run(str(SCRIPTS / "validate_skill.py"), str(skill))
        ok = p.returncode == 0 and "Result: OK" in p.stdout
        self.record("validate_skill on clean skill", ok,
                    f"exit={p.returncode}")

    def t_validate_negative_codes(self) -> None:
        """Each case asserts that a specific error code fires."""
        cases: list[tuple[str, str, str]] = [
            (
                "E004a: name too long",
                f"name: {'a' * 65}\n"
                'description: Use when the user wants a thing. Triggers on "do thing". Produces a file.\n'
                "version: 0.1.0",
                "E004a",
            ),
            (
                "E004: name not kebab",
                "name: BadName\n"
                'description: Use when the user wants a thing. Triggers on "do thing". Produces a file.\n'
                "version: 0.1.0",
                "E004",
            ),
            (
                "E004b: reserved word claude",
                "name: claude-thing\n"
                'description: Use when the user wants a thing. Triggers on "do thing". Produces a file.\n'
                "version: 0.1.0",
                "E004b",
            ),
            (
                "E004b: reserved word anthropic",
                "name: anthropic-helper\n"
                'description: Use when the user wants a thing. Triggers on "do thing". Produces a file.\n'
                "version: 0.1.0",
                "E004b",
            ),
            (
                "E005: bad semver",
                "name: bad-semver\n"
                'description: Use when the user wants a thing. Triggers on "do thing". Produces a file.\n'
                "version: not.a.version",
                "E005",
            ),
            (
                "E006a: description too long",
                "name: long-desc\n"
                f"description: Use when the user wants X. {'Very long filler. ' * 80}\n"
                "version: 0.1.0",
                "E006a",
            ),
            (
                "E006b: first-person description",
                "name: first-person\n"
                "description: I can help you process spreadsheets\n"
                "version: 0.1.0",
                "E006b",
            ),
            (
                "E008: TODO marker",
                "name: has-todo\n"
                'description: Use when the user wants a thing. Triggers on "do thing". Produces a file.\n'
                "version: 0.1.0",
                "E008",
                "\n\n# T\n\nTODO fix me\n",
            ),
            (
                "E011: Windows path",
                "name: windows-path\n"
                'description: Use when the user wants a thing. Triggers on "do thing". Produces a file.\n'
                "version: 0.1.0",
                "E011",
                '\n\n# T\n\nRun `scripts\\helper.py`\n',
            ),
        ]
        for entry in cases:
            name, fm, expected_code, *extra = entry
            body = extra[0] if extra else "\n\n# Title\n\n## Overview\n\nx\n"
            skill_md = f"---\n{fm}\n---{body}"
            slug = "neg-" + expected_code.lower().replace(":", "-")
            skill = self.make_skill(slug, skill_md)
            p = self.run(str(SCRIPTS / "validate_skill.py"), str(skill))
            ok = p.returncode == 1 and expected_code in p.stdout
            self.record(f"validator {name}", ok,
                        f"exit={p.returncode}, code={expected_code}")

    def t_validate_e012_nested(self) -> None:
        skill = self.make_skill(
            "nested-refs",
            CLEAN_SKILL_MD_WITH_REF,
            refs={
                "a.md": "# A\n\nSee [b](b.md) for more.\n",
                "b.md": "# B\n",
            },
        )
        p = self.run(str(SCRIPTS / "validate_skill.py"), str(skill))
        ok = p.returncode == 1 and "E012" in p.stdout
        self.record("validator E012 (nested reference)", ok,
                    f"exit={p.returncode}")

    def t_validate_w013_no_toc(self) -> None:
        long_ref = "\n".join([f"line {i}" for i in range(120)])
        skill = self.make_skill(
            "long-ref",
            CLEAN_SKILL_MD_WITH_REF,
            refs={"a.md": f"# A\n\n{long_ref}\n"},
        )
        p = self.run(str(SCRIPTS / "validate_skill.py"), str(skill))
        ok = p.returncode == 0 and "W013" in p.stdout
        self.record("validator W013 (long ref without TOC)", ok,
                    f"exit={p.returncode}")

    def t_refactor_healthy(self) -> None:
        skill = self.make_skill("healthy", CLEAN_SKILL_MD)
        p = self.run(str(SCRIPTS / "refactor_skill.py"), str(skill))
        ok = p.returncode == 0 and "No refactor needed" in p.stdout
        self.record("refactor_skill on healthy skill", ok,
                    f"exit={p.returncode}")

    def t_refactor_bloated(self) -> None:
        big_body = "\n".join([
            "## Section",
            "",
            *[f"Some descriptive content line {i}." for i in range(600)],
        ])
        skill_md = CLEAN_SKILL_MD + "\n" + big_body + "\n"
        skill = self.make_skill("bloated", skill_md)
        p = self.run(str(SCRIPTS / "refactor_skill.py"), str(skill))
        ok = (p.returncode == 0
              and "exceeds 500 lines" in p.stdout)
        self.record("refactor_skill flags bloated body", ok,
                    f"exit={p.returncode}")

    def t_version_log_full_cycle(self) -> None:
        skill = self.make_skill("versioned", CLEAN_SKILL_MD_NO_VERSION)
        p = self.run(str(SCRIPTS / "version_log.py"), str(skill),
                     "init", "--version", "0.1.0", "--message", "init")
        if p.returncode != 0:
            self.record("version_log init", False, f"exit={p.returncode}")
            return
        p = self.run(str(SCRIPTS / "version_log.py"), str(skill),
                     "bump", "--minor", "--message", "add feature")
        if p.returncode != 0 or "0.1.0 -> 0.2.0" not in p.stdout:
            self.record("version_log bump --minor", False, p.stdout.strip())
            return
        p = self.run(str(SCRIPTS / "version_log.py"), str(skill),
                     "bump", "--patch", "--message", "fix")
        if p.returncode != 0 or "0.2.0 -> 0.2.1" not in p.stdout:
            self.record("version_log bump --patch", False, p.stdout.strip())
            return
        p = self.run(str(SCRIPTS / "version_log.py"), str(skill), "show")
        ok = "version: 0.2.1" in p.stdout and "## 0.2.1" in p.stdout \
            and "## 0.1.0" in p.stdout
        self.record("version_log full cycle (init→minor→patch→show)",
                    ok, "")

    def t_test_skill_dry_run_ok(self) -> None:
        skill = self.make_skill("with-cases", CLEAN_SKILL_MD)
        (skill / "evals").mkdir(exist_ok=True)
        (skill / "evals" / "cases.json").write_text(
            json.dumps({
                "skill": "with-cases",
                "cases": [{
                    "id": "c1",
                    "prompt": "do a thing",
                    "assertions": [
                        {"id": "a1", "text": "something happened"}
                    ],
                }],
            }),
            encoding="utf-8",
        )
        p = self.run(str(SCRIPTS / "test_skill.py"), str(skill),
                     "--cases", str(skill / "evals" / "cases.json"),
                     "--dry-run")
        ok = p.returncode == 0 and "dry-run ok" in p.stdout
        self.record("test_skill --dry-run on valid cases", ok,
                    f"exit={p.returncode}")

    def t_test_skill_dry_run_bad(self) -> None:
        skill = self.make_skill("bad-cases", CLEAN_SKILL_MD)
        (skill / "evals").mkdir(exist_ok=True)
        (skill / "evals" / "cases.json").write_text(
            '{"skill": "bad-cases"}',  # no 'cases' key
            encoding="utf-8",
        )
        p = self.run(str(SCRIPTS / "test_skill.py"), str(skill),
                     "--cases", str(skill / "evals" / "cases.json"),
                     "--dry-run")
        ok = p.returncode == 2
        self.record("test_skill --dry-run rejects malformed cases", ok,
                    f"exit={p.returncode}")

    # -- orchestration --------------------------------------------

    def t_fix_clean_is_noop(self) -> None:
        skill = self.make_skill("fix-clean", CLEAN_SKILL_MD)
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--fix")
        ok = p.returncode == 0 and "no fixes needed" in p.stdout
        self.record("fix mode is no-op on clean skill", ok,
                    f"exit={p.returncode}")

    def t_fix_windows_path(self) -> None:
        skill_md = CLEAN_SKILL_MD + '\nRun `scripts\\foo.py` now.\n'
        skill = self.make_skill("fix-winpath", skill_md)
        # Dry-run
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--fix")
        if not (p.returncode == 1 and "[windows-path]" in p.stdout):
            self.record("fix --fix detects Windows path", False,
                        f"exit={p.returncode}")
            return
        # Apply
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--fix", "--apply")
        content = (skill / "SKILL.md").read_text(encoding="utf-8")
        ok = p.returncode == 0 \
            and "`scripts/foo.py`" in content \
            and "scripts\\foo.py" not in content
        self.record("fix --apply rewrites Windows path", ok, "")

    def t_fix_trailing_ws_and_newline(self) -> None:
        # Intentionally omit final newline, add trailing spaces
        text = CLEAN_SKILL_MD.rstrip("\n") + "   \ntrailing   \n"
        text = text.rstrip("\n")  # no final newline
        skill = self.make_skill("fix-ws", text)
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--fix", "--apply")
        content = (skill / "SKILL.md").read_text(encoding="utf-8")
        ends_ok = content.endswith("\n")
        no_trailing = all(
            ln == ln.rstrip() for ln in content.splitlines()
        )
        ok = p.returncode == 0 and ends_ok and no_trailing
        self.record("fix --apply strips trailing ws + adds final newline",
                    ok, "")

    def t_fix_crlf(self) -> None:
        crlf_text = CLEAN_SKILL_MD.replace("\n", "\r\n")
        skill = self.make_skill("fix-crlf", crlf_text)
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--fix", "--apply")
        content = (skill / "SKILL.md").read_text(encoding="utf-8")
        ok = p.returncode == 0 and "\r\n" not in content \
            and "\r" not in content
        self.record("fix --apply normalizes CRLF to LF", ok, "")

    def t_fix_toc_long_ref(self) -> None:
        sections = "\n\n".join(
            f"## Section {i}\n\ncontent {i}" for i in range(1, 25)
        )
        long_ref = f"# Ref\n\nintro\n\n{sections}\n"
        # Pad to > 100 lines
        long_ref += "\n" + "\n".join(f"line {i}" for i in range(80))
        skill = self.make_skill(
            "fix-toc",
            CLEAN_SKILL_MD_WITH_REF,
            refs={"a.md": long_ref},
        )
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--fix", "--apply")
        content = (skill / "references" / "a.md").read_text(encoding="utf-8")
        ok = p.returncode == 0 and "## Contents" in content \
            and "- Section 1" in content
        self.record("fix --apply inserts TOC into long reference", ok, "")

    def t_fix_idempotent(self) -> None:
        skill_md = CLEAN_SKILL_MD + '\nRun `scripts\\foo.py` now.\n'
        skill = self.make_skill("fix-idem", skill_md)
        self.run(str(SCRIPTS / "refactor_skill.py"),
                 str(skill), "--fix", "--apply")
        # Second run must be a no-op
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--fix")
        ok = p.returncode == 0 and "no fixes needed" in p.stdout
        self.record("fix mode is idempotent (second pass no-op)", ok,
                    f"exit={p.returncode}")

    def t_apply_requires_fix(self) -> None:
        skill = self.make_skill("fix-apply-only", CLEAN_SKILL_MD)
        p = self.run(str(SCRIPTS / "refactor_skill.py"),
                     str(skill), "--apply")
        ok = p.returncode == 2 and "--apply requires --fix" in p.stderr
        self.record("--apply without --fix is rejected", ok,
                    f"exit={p.returncode}")

    def run_all(self) -> int:
        print("Skill-Gen Agent integration tests")
        print()
        self.t_validate_clean()
        self.t_validate_negative_codes()
        self.t_validate_e012_nested()
        self.t_validate_w013_no_toc()
        self.t_refactor_healthy()
        self.t_refactor_bloated()
        self.t_version_log_full_cycle()
        self.t_test_skill_dry_run_ok()
        self.t_test_skill_dry_run_bad()
        self.t_fix_clean_is_noop()
        self.t_fix_windows_path()
        self.t_fix_trailing_ws_and_newline()
        self.t_fix_crlf()
        self.t_fix_toc_long_ref()
        self.t_fix_idempotent()
        self.t_apply_requires_fix()

        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        print()
        print(f"  {passed} passed, {failed} failed, "
              f"{len(self.results)} total")
        return 0 if failed == 0 else 1


# --- fixture blocks ----------------------------------------------

CLEAN_SKILL_MD = """---
name: clean-skill
description: Use when the user wants to test a clean skill. Triggers on phrases like "clean skill", "test clean", "sample skill". Produces a sample output file.
version: 0.1.0
---

# Clean Skill

## Overview

Minimal fixture for integration tests.

## Workflow

1. Read the input.
2. Write the output.
3. Report to the user.
"""

CLEAN_SKILL_MD_WITH_REF = """---
name: clean-skill
description: Use when the user wants to test a clean skill. Triggers on phrases like "clean skill", "test clean", "sample skill". Produces a sample output file.
version: 0.1.0
---

# Clean Skill

## Overview

Minimal fixture with a reference.

## Workflow

1. Read `references/a.md`.
2. Report.
"""

CLEAN_SKILL_MD_NO_VERSION = """---
name: clean-skill
description: Use when the user wants to test a clean skill. Triggers on phrases like "clean skill", "test clean", "sample skill". Produces a sample output file.
---

# Clean Skill

## Overview

Minimal fixture without version — for `version_log init`.

## Workflow

1. Read.
2. Write.
"""


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="skill-gen-tests-") as tmp:
        runner = Runner(tmp=Path(tmp), verbose=args.verbose)
        return runner.run_all()


if __name__ == "__main__":
    sys.exit(main())
