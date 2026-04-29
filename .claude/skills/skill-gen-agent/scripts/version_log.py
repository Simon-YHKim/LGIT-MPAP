#!/usr/bin/env python3
"""Version and CHANGELOG management for a Claude Code Skill.

Usage:
    version_log.py <skill-path> init  --version X.Y.Z --message "..."
    version_log.py <skill-path> bump  (--major|--minor|--patch) --message "..."
    version_log.py <skill-path> show

Actions:
    init  - Stamp the given version into SKILL.md frontmatter and create
            CHANGELOG.md with the initial entry.
    bump  - Increment the version in SKILL.md and prepend a CHANGELOG entry.
    show  - Print the current version and the last 5 changelog entries.

Exit code 0 on success, non-zero on failure.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def read_skill_md(skill: Path) -> tuple[str, list[str]]:
    md = skill / "SKILL.md"
    if not md.exists():
        raise SystemExit(f"error: {md} not found")
    return md.read_text(encoding="utf-8"), md.read_text(encoding="utf-8").splitlines()


def current_version(text: str) -> str | None:
    m = re.search(r"^version:\s*(.+)$", text, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


def set_version(text: str, new_version: str) -> str:
    if re.search(r"^version:\s*.+$", text, re.MULTILINE):
        return re.sub(r"^version:\s*.+$", f"version: {new_version}",
                      text, count=1, flags=re.MULTILINE)
    # Insert after `name:` line inside frontmatter.
    return re.sub(r"^(name:\s*.+)$",
                  rf"\1\nversion: {new_version}",
                  text, count=1, flags=re.MULTILINE)


def bump(version: str, kind: str) -> str:
    m = SEMVER_RE.match(version)
    if not m:
        raise SystemExit(f"error: current version '{version}' is not simple semver")
    major, minor, patch = map(int, m.groups())
    if kind == "major":
        major, minor, patch = major + 1, 0, 0
    elif kind == "minor":
        minor, patch = minor + 1, 0
    elif kind == "patch":
        patch += 1
    else:
        raise SystemExit(f"error: unknown bump kind {kind!r}")
    return f"{major}.{minor}.{patch}"


def today() -> str:
    return dt.date.today().isoformat()


def prepend_changelog(skill: Path, version: str, message: str) -> None:
    path = skill / "CHANGELOG.md"
    entry = f"## {version} - {today()}\n\n- {message}\n\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing.startswith("# Changelog"):
            head, _, rest = existing.partition("\n")
            new = head + "\n\n" + entry + rest.lstrip()
        else:
            new = "# Changelog\n\n" + entry + existing
    else:
        new = "# Changelog\n\n" + entry
    path.write_text(new, encoding="utf-8")


def cmd_init(args: argparse.Namespace) -> int:
    skill: Path = args.skill_path
    text, _ = read_skill_md(skill)
    if not SEMVER_RE.match(args.version):
        print(f"error: '{args.version}' is not valid semver (X.Y.Z)",
              file=sys.stderr)
        return 2
    new_text = set_version(text, args.version)
    (skill / "SKILL.md").write_text(new_text, encoding="utf-8")
    prepend_changelog(skill, args.version, args.message)
    print(f"Initialized {skill.name} at version {args.version}")
    return 0


def cmd_bump(args: argparse.Namespace) -> int:
    skill: Path = args.skill_path
    text, _ = read_skill_md(skill)
    cur = current_version(text)
    if not cur:
        print("error: no `version:` field in SKILL.md; run `init` first",
              file=sys.stderr)
        return 2
    kind = "major" if args.major else "minor" if args.minor else "patch"
    new = bump(cur, kind)
    new_text = set_version(text, new)
    (skill / "SKILL.md").write_text(new_text, encoding="utf-8")
    prepend_changelog(skill, new, args.message)
    print(f"{skill.name}: {cur} -> {new} ({kind})")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    skill: Path = args.skill_path
    text, _ = read_skill_md(skill)
    cur = current_version(text) or "(unset)"
    print(f"skill:   {skill.name}")
    print(f"version: {cur}")
    log = skill / "CHANGELOG.md"
    if log.exists():
        lines = log.read_text(encoding="utf-8").splitlines()
        print()
        shown = 0
        for ln in lines:
            if ln.startswith("## "):
                shown += 1
                if shown > 5:
                    break
            if shown <= 5:
                print(ln)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("skill_path", type=Path)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp_init = sub.add_parser("init", help="stamp initial version + changelog")
    sp_init.add_argument("--version", required=True)
    sp_init.add_argument("--message", required=True)
    sp_init.set_defaults(func=cmd_init)

    sp_bump = sub.add_parser("bump", help="bump semver + prepend changelog")
    grp = sp_bump.add_mutually_exclusive_group(required=True)
    grp.add_argument("--major", action="store_true")
    grp.add_argument("--minor", action="store_true")
    grp.add_argument("--patch", action="store_true")
    sp_bump.add_argument("--message", required=True)
    sp_bump.set_defaults(func=cmd_bump)

    sp_show = sub.add_parser("show", help="print current version + log")
    sp_show.set_defaults(func=cmd_show)

    args = p.parse_args(argv)
    if not args.skill_path.is_dir():
        print(f"error: {args.skill_path} is not a directory", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
