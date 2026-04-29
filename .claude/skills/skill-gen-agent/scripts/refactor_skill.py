#!/usr/bin/env python3
"""Analyze or auto-fix a skill.

Usage:
    refactor_skill.py <skill-path> [--analyze] [--format human|json]
    refactor_skill.py <skill-path> --fix [--apply]

Analyze mode (default) produces a report with:
    - Body/section line counts
    - Imperative vs. descriptive voice ratio
    - Description quality score
    - Sections that look like reference material
    - Placeholder/TODO markers
    - Refactor suggestions

Fix mode applies safe mechanical transformations:
    - Insert `## Contents` TOC into long reference files (>100 lines)
    - Replace Windows-style backslash paths with forward slashes in SKILL.md
    - Strip trailing whitespace from .md files
    - Ensure a single trailing newline on .md files
    - Normalize CRLF line endings to LF

Fix mode is dry-run by default; pass --apply to actually write.
Fix mode does NOT touch semantic smells (first-person descriptions,
reserved names, TODO markers, nested references, >500-line bodies).
Those require human judgment and are reported by analyze mode.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Reuse validate_skill helpers.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from validate_skill import parse_frontmatter, score_description  # noqa: E402


DESCRIPTIVE_MARKERS = [
    r"\byou might\b", r"\byou may\b", r"\byou could\b",
    r"\bcan be\b", r"\bshould be\b", r"\bwould be\b",
    r"\bit is recommended\b", r"\bit is possible\b",
]
IMPERATIVE_HINTS = [
    # Imperative verb at start of a line, list item, numbered step, or
    # after common Markdown prefixes like `- `, `* `, `1. `, `**Gate:** `.
    r"^(?:[-*]\s+|\d+\.\s+|\*\*[A-Za-z ]+:\*\*\s*)?"
    r"(Run|Read|Write|Use|Call|Check|Load|Parse|Open|Create|Delete|"
    r"Add|Remove|Print|Return|Do\s+(?:not|NOT)|Never|Apply|Fix|"
    r"Report|Spawn|Validate|Test|Ask|Detect|Follow|Generate|Copy|"
    r"Move|Rename|Bump|Record|Grade|Prefer|Avoid|Keep|Set|Match|"
    r"Pick|Handle|Include|Exclude|Ensure|Update|Refuse|Show|Start|"
    r"Stop|Flatten|Install|Fetch|Invoke|Push|Merge)\b",
]


@dataclass
class SectionStats:
    title: str
    lines: int
    imperative_hits: int = 0
    descriptive_hits: int = 0
    looks_like_reference: bool = False


@dataclass
class RefactorReport:
    skill_path: str
    body_lines: int
    description_score: float
    description_reasons: list[str]
    sections: list[SectionStats] = field(default_factory=list)
    placeholders: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


def split_sections(body: str) -> list[tuple[str, list[str]]]:
    """Return list of (title, lines) split on H2 headers."""
    out: list[tuple[str, list[str]]] = []
    current_title = "(preamble)"
    current: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current:
                out.append((current_title, current))
            current_title = line[3:].strip()
            current = []
        else:
            current.append(line)
    if current:
        out.append((current_title, current))
    return out


def analyze_section(title: str, lines: list[str]) -> SectionStats:
    stats = SectionStats(title=title, lines=len(lines))
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for pat in IMPERATIVE_HINTS:
            if re.match(pat, stripped):
                stats.imperative_hits += 1
                break
        for pat in DESCRIPTIVE_MARKERS:
            if re.search(pat, stripped, re.IGNORECASE):
                stats.descriptive_hits += 1
                break
    # Heuristic: a section with many table rows, code blocks with
    # schemas, or over 60 lines without imperative verbs is likely
    # reference material.
    joined = "\n".join(lines)
    table_rows = joined.count("\n|")
    schemas = joined.count("```json") + joined.count("```yaml")
    if (stats.lines > 60 and stats.imperative_hits < 3) \
            or table_rows > 8 or schemas >= 2:
        stats.looks_like_reference = True
    return stats


def analyze(skill_path: Path) -> RefactorReport:
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        raise SystemExit(f"error: {skill_md} not found")
    text = skill_md.read_text(encoding="utf-8")
    fm, body, _ = parse_frontmatter(text)

    desc = str(fm.get("description", ""))
    score, reasons = score_description(desc)

    report = RefactorReport(
        skill_path=str(skill_path),
        body_lines=body.count("\n") + 1,
        description_score=round(score, 3),
        description_reasons=reasons,
    )

    for title, lines in split_sections(body):
        report.sections.append(analyze_section(title, lines))

    placeholder_re = re.compile(r"\b(TODO|FIXME|XXX|<placeholder>)\b",
                                re.IGNORECASE)
    for i, line in enumerate(text.splitlines(), start=1):
        if placeholder_re.search(line):
            report.placeholders.append(f"L{i}: {line.strip()}")

    # Build suggestions.
    if report.body_lines > 500:
        report.suggestions.append(
            "SKILL.md body exceeds 500 lines. Move the largest "
            "reference-like sections to references/*.md.")
    elif report.body_lines > 400:
        report.suggestions.append(
            "SKILL.md body is over 400 lines. Consider splitting.")

    for s in report.sections:
        if s.looks_like_reference:
            report.suggestions.append(
                f"Section '{s.title}' ({s.lines} lines) looks like "
                "reference material; move to references/.")
        if s.descriptive_hits > s.imperative_hits and s.lines > 10:
            report.suggestions.append(
                f"Section '{s.title}' is descriptive-heavy "
                f"({s.descriptive_hits} descriptive vs "
                f"{s.imperative_hits} imperative). Rewrite in "
                "imperative voice.")

    if score < 0.6:
        report.suggestions.append(
            f"Description score {score:.2f} < 0.6. "
            "Rewrite to lead with 'Use when...', add verbatim trigger "
            "phrases, state the output.")

    if report.placeholders:
        report.suggestions.append(
            f"{len(report.placeholders)} placeholder(s)/TODO(s) found. "
            "Resolve or delete before release.")

    if not report.suggestions:
        report.suggestions.append("No refactor needed. Skill looks healthy.")

    return report


def to_human(report: RefactorReport) -> str:
    lines = [
        f"Refactor analysis: {report.skill_path}",
        "",
        f"  body lines: {report.body_lines}",
        f"  description score: {report.description_score}",
    ]
    if report.description_reasons:
        for r in report.description_reasons:
            lines.append(f"    - {r}")
    lines.append("")
    lines.append("Sections:")
    for s in report.sections:
        tag = " [REFERENCE-LIKE]" if s.looks_like_reference else ""
        lines.append(f"  - {s.title}: {s.lines} lines "
                     f"(imp {s.imperative_hits} / desc {s.descriptive_hits})"
                     f"{tag}")
    if report.placeholders:
        lines.append("")
        lines.append("Placeholders / TODOs:")
        for p in report.placeholders:
            lines.append(f"  - {p}")
    lines.append("")
    lines.append("Suggestions:")
    for s in report.suggestions:
        lines.append(f"  * {s}")
    return "\n".join(lines)


# -----------------------------------------------------------------
# Fix mode: safe mechanical transformations
# -----------------------------------------------------------------

LONG_REF_THRESHOLD = 100  # matches validate_skill.LONG_REF_LINES


@dataclass
class FixAction:
    """One pending or applied fix."""
    path: str        # relative to skill root
    kind: str        # "toc" | "windows-path" | "trailing-ws" | "final-newline" | "crlf"
    detail: str      # human-readable description


def _strip_trailing_whitespace(text: str) -> tuple[str, int]:
    """Return (new_text, changed_line_count)."""
    new_lines: list[str] = []
    changes = 0
    # Don't strip newline chars themselves.
    for raw in text.splitlines(keepends=True):
        if raw.endswith("\r\n"):
            body, nl = raw[:-2], "\r\n"
        elif raw.endswith(("\n", "\r")):
            body, nl = raw[:-1], raw[-1]
        else:
            body, nl = raw, ""
        stripped = body.rstrip()
        if stripped != body:
            changes += 1
        new_lines.append(stripped + nl)
    return "".join(new_lines), changes


def _normalize_crlf(text: str) -> tuple[str, int]:
    if "\r\n" not in text and "\r" not in text:
        return text, 0
    count = text.count("\r\n") + text.replace("\r\n", "").count("\r")
    new_text = text.replace("\r\n", "\n").replace("\r", "\n")
    return new_text, count


def _ensure_final_newline(text: str) -> tuple[str, bool]:
    if text == "" or text.endswith("\n"):
        return text, False
    return text + "\n", True


def _extract_h2_headings(body: str) -> list[str]:
    out: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## ") and not line.startswith("## Contents"):
            out.append(line[3:].strip())
    return out


def _build_toc_block(headings: list[str]) -> str:
    lines = ["## Contents", ""]
    for h in headings:
        lines.append(f"- {h}")
    lines.append("")
    return "\n".join(lines) + "\n"


def _insert_toc(text: str, headings: list[str]) -> str:
    """Insert a Contents block after the first H1 and intro paragraph.

    Strategy: find the first H1 line. Skip blank lines and non-heading
    paragraph text until the next blank line before an H2. Insert the
    TOC block there. If no H1, insert at the top.
    """
    toc = _build_toc_block(headings)
    lines = text.splitlines(keepends=True)

    # Find first H1.
    h1_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            h1_idx = i
            break
    if h1_idx is None:
        return toc + "\n" + text

    # From H1, skip to the line before the first H2.
    insert_at = None
    for j in range(h1_idx + 1, len(lines)):
        if lines[j].startswith("## "):
            insert_at = j
            break
    if insert_at is None:
        insert_at = len(lines)

    new_lines = lines[:insert_at] + [toc + "\n"] + lines[insert_at:]
    return "".join(new_lines)


def _fix_windows_paths_line(line: str) -> tuple[str, int]:
    """Replace Windows backslash paths inside backticks/quotes."""
    pattern = re.compile(
        r"([`\"'])([a-zA-Z0-9_.-]+(?:\\[a-zA-Z0-9_.-]+)+)([`\"'])"
    )
    count = [0]

    def repl(m: re.Match[str]) -> str:
        count[0] += 1
        open_q, path, close_q = m.group(1), m.group(2), m.group(3)
        return f"{open_q}{path.replace(chr(92), '/')}{close_q}"

    return pattern.sub(repl, line), count[0]


def collect_fixes(skill_path: Path) -> tuple[list[FixAction], dict[Path, str]]:
    """Walk the skill and compute pending fixes.

    Returns (actions, new_content_by_path). new_content_by_path maps
    every file that would change to its post-fix content, so --apply
    can write atomically and --dry-run can preview.
    """
    actions: list[FixAction] = []
    new_content: dict[Path, str] = {}

    def rel(p: Path) -> str:
        try:
            return p.relative_to(skill_path).as_posix()
        except ValueError:
            return str(p)

    # Walk all .md files in the skill (SKILL.md, references/*.md, etc.)
    md_files = sorted(skill_path.rglob("*.md"))

    for md in md_files:
        if not md.is_file():
            continue
        # Skip files outside the skill boundary and anything in evals/.
        try:
            md.relative_to(skill_path)
        except ValueError:
            continue
        if any(part == "evals" for part in md.relative_to(skill_path).parts):
            continue

        original = md.read_text(encoding="utf-8", errors="replace")
        current = original

        # 1. CRLF -> LF
        current, crlf_changes = _normalize_crlf(current)
        if crlf_changes:
            actions.append(FixAction(
                rel(md), "crlf",
                f"normalize {crlf_changes} CRLF line ending(s)"))

        # 2. Trailing whitespace
        current, ws_changes = _strip_trailing_whitespace(current)
        if ws_changes:
            actions.append(FixAction(
                rel(md), "trailing-ws",
                f"strip trailing whitespace on {ws_changes} line(s)"))

        # 3. Final newline
        current, added = _ensure_final_newline(current)
        if added:
            actions.append(FixAction(
                rel(md), "final-newline",
                "add missing trailing newline"))

        # 4. Windows-path fixes — only in SKILL.md
        if md.name == "SKILL.md":
            fixed_lines: list[str] = []
            wp_total = 0
            for line in current.splitlines(keepends=True):
                if line.endswith("\n"):
                    body, nl = line[:-1], "\n"
                else:
                    body, nl = line, ""
                new_body, count = _fix_windows_paths_line(body)
                wp_total += count
                fixed_lines.append(new_body + nl)
            if wp_total:
                current = "".join(fixed_lines)
                actions.append(FixAction(
                    rel(md), "windows-path",
                    f"rewrite {wp_total} Windows-style path(s) to forward slashes"))

        # 5. TOC on long reference files
        is_ref = (md.parent.name == "references" and md.name != "SKILL.md")
        if is_ref:
            line_count = current.count("\n") + (0 if current.endswith("\n") else 1)
            if line_count > LONG_REF_THRESHOLD:
                lower = current.lower()
                if "## contents" not in lower \
                        and "## table of contents" not in lower:
                    # Split frontmatter/body carefully: reference files
                    # typically have no frontmatter, so operate on body
                    # directly.
                    headings = _extract_h2_headings(current)
                    if headings:
                        current = _insert_toc(current, headings)
                        actions.append(FixAction(
                            rel(md), "toc",
                            f"insert `## Contents` with "
                            f"{len(headings)} entries"))

        if current != original:
            new_content[md] = current

    return actions, new_content


def apply_fixes(new_content: dict[Path, str]) -> None:
    for path, content in new_content.items():
        path.write_text(content, encoding="utf-8")


def format_fix_report(actions: list[FixAction], apply: bool) -> str:
    header = "Applied fixes:" if apply else "Pending fixes (dry-run):"
    lines = [header, ""]
    if not actions:
        lines.append("  (no fixes needed)")
        return "\n".join(lines)
    by_path: dict[str, list[FixAction]] = {}
    for a in actions:
        by_path.setdefault(a.path, []).append(a)
    for path in sorted(by_path):
        lines.append(f"  {path}")
        for a in by_path[path]:
            lines.append(f"    - [{a.kind}] {a.detail}")
    lines.append("")
    verb = "applied" if apply else "would apply"
    lines.append(f"  {len(actions)} fix(es) {verb}")
    if not apply:
        lines.append("  Run with --apply to write changes.")
    return "\n".join(lines)


def cmd_fix(args: argparse.Namespace) -> int:
    actions, new_content = collect_fixes(args.skill_path)
    if args.apply:
        apply_fixes(new_content)
    print(format_fix_report(actions, apply=args.apply))
    # Non-zero exit in dry-run mode if there are pending fixes, so CI
    # can gate on "is this skill clean?".
    if not args.apply and actions:
        return 1
    return 0


# -----------------------------------------------------------------
# CLI
# -----------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("skill_path", type=Path)
    p.add_argument("--analyze", action="store_true",
                   help="analyze and report (default)")
    p.add_argument("--fix", action="store_true",
                   help="apply safe mechanical fixes (dry-run unless --apply)")
    p.add_argument("--apply", action="store_true",
                   help="with --fix, actually write changes")
    p.add_argument("--format", choices=("human", "json"), default="human")
    args = p.parse_args(argv)

    if not args.skill_path.is_dir():
        print(f"error: {args.skill_path} is not a directory", file=sys.stderr)
        return 2

    if args.apply and not args.fix:
        print("error: --apply requires --fix", file=sys.stderr)
        return 2

    if args.fix:
        return cmd_fix(args)

    report = analyze(args.skill_path)
    if args.format == "json":
        print(json.dumps(asdict(report), indent=2))
    else:
        print(to_human(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
