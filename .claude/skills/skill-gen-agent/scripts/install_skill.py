#!/usr/bin/env python3
"""Install a skill directory into a Claude Code skills location.

Usage:
    install_skill.py <skill-path> [--user | --project DIR]
                     [--force] [--dry-run]

Destinations:
    --user        ~/.claude/skills/<name>/          (default)
    --project DIR <DIR>/.claude/skills/<name>/

Actions:
    1. Validate the source skill with validate_skill.py.
       Refuse to install if the validator exits non-zero unless
       --force is passed.
    2. Determine the destination from the skill's frontmatter name.
    3. If the destination already exists, refuse unless --force.
    4. Copy the tree.
    5. Print the install path.

Exit codes:
    0 — installed successfully
    1 — validator failed (without --force)
    2 — destination exists (without --force)
    3 — source not found / not a skill directory
    4 — argparse / usage error
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from validate_skill import parse_frontmatter  # noqa: E402


def resolve_dest(skill_name: str, mode: str, project: Path | None) -> Path:
    if mode == "user":
        home = Path(os.path.expanduser("~"))
        return home / ".claude" / "skills" / skill_name
    assert project is not None
    return project / ".claude" / "skills" / skill_name


def read_skill_name(source: Path) -> str:
    skill_md = source / "SKILL.md"
    if not skill_md.exists():
        raise SystemExit(f"error: {skill_md} not found")
    text = skill_md.read_text(encoding="utf-8")
    try:
        fm, _, _ = parse_frontmatter(text)
    except ValueError as e:
        raise SystemExit(f"error: invalid frontmatter: {e}")
    name = str(fm.get("name", "")).strip()
    if not name:
        raise SystemExit("error: frontmatter is missing 'name'")
    return name


def run_validator(source: Path) -> int:
    validator = SCRIPT_DIR / "validate_skill.py"
    proc = subprocess.run(
        [sys.executable, str(validator), str(source)],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def copy_tree(source: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] would copy {source} -> {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source, dest,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".DS_Store", "*.swp",
            "evals",  # evals are not shipped
        ),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path,
                   help="path to the skill directory to install")
    grp = p.add_mutually_exclusive_group()
    grp.add_argument("--user", action="store_true",
                     help="install to ~/.claude/skills/ (default)")
    grp.add_argument("--project", type=Path, metavar="DIR",
                     help="install to <DIR>/.claude/skills/")
    p.add_argument("--force", action="store_true",
                   help="overwrite existing dest and skip validator gate")
    p.add_argument("--dry-run", action="store_true",
                   help="print what would happen without writing")
    args = p.parse_args(argv)

    source: Path = args.source.resolve()
    if not source.is_dir():
        print(f"error: {source} is not a directory", file=sys.stderr)
        return 3
    if not (source / "SKILL.md").exists():
        print(f"error: {source} has no SKILL.md", file=sys.stderr)
        return 3

    # 1. Validate
    if not args.force:
        rc = run_validator(source)
        if rc != 0:
            print("error: validator failed; use --force to install anyway",
                  file=sys.stderr)
            return 1
    else:
        print("[--force] skipping validator gate")

    # 2. Read name
    name = read_skill_name(source)

    # 3. Destination
    mode = "project" if args.project else "user"
    dest = resolve_dest(name, mode, args.project)

    if dest.exists():
        if not args.force:
            print(f"error: {dest} already exists; "
                  f"use --force to overwrite", file=sys.stderr)
            return 2
        if args.dry_run:
            print(f"[dry-run] would remove existing {dest}")
        else:
            shutil.rmtree(dest)

    # 4. Copy
    copy_tree(source, dest, args.dry_run)

    # 5. Report
    action = "would install" if args.dry_run else "installed"
    print(f"{action} '{name}' at {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
