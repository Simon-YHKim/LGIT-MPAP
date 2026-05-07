"""
verify_backend_freeze.py — STAGE 2 백엔드 보존 게이트.

핸드오프 원칙: "preview UI → streamlit-app 덮어쓰기는 CSS 와 HTML 문자열만 교체.
함수 시그니처 / SQL 쿼리 / st.session_state 키 / import 는 보존."

이 스크립트는 그 원칙을 enforce 한다:
  1. STREAMLIT_APP 의 모든 .py 파일을 AST 로 파싱
  2. 각 파일에서 (function name, arg signature), (string SQL 후보),
     (st.session_state 키), (top-level import) 추출
  3. 베이스라인 JSON (commit 시점의 snapshot) 과 비교
  4. 함수 시그니처 / SQL / session key / import 가 사라지거나 변경되면 FAIL
     · 추가는 OK (새 헬퍼 함수 / 새 키 / 새 import 는 핸드오프 원칙 위반 아님)
     · 삭제·수정은 FAIL

사용법:
  # 베이스라인 생성 (STAGE 2 시작 시점에 1회만):
  python scripts/verify_backend_freeze.py --emit-baseline

  # CI / pre-commit 게이트:
  python scripts/verify_backend_freeze.py
  # exit 0 = PASS, exit 1 = REGRESSION

베이스라인 JSON 위치:
  streamlit-app/scripts/backend_freeze_baseline.json
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# 이 파일의 위치 = streamlit-app/scripts/verify_backend_freeze.py
THIS_DIR = Path(__file__).resolve().parent
APP_DIR = THIS_DIR.parent  # streamlit-app/
BASELINE_PATH = THIS_DIR / "backend_freeze_baseline.json"

# 검사 대상 (백엔드 보존 원칙이 적용되는 파일들)
SCAN_TARGETS = [
    "login.py",
    "db.py",
    "queries.py",
    "tracking.py",
    "utils.py",
    "auth_guard.py",
    "access_logger.py",
    "Alarm_Master_Data.py",
    "MTBA_Data.py",
    "reset_mtba_db.py",
]
SCAN_DIRS = [
    "pages",
    "llm_api",
    "mtba_detail_view",
    "ETL",
]

# SQL 후보 패턴: SELECT/INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/WITH/MERGE 시작
_SQL_KEYWORDS = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH|MERGE|TRUNCATE)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _iter_py_files() -> List[Path]:
    files: List[Path] = []
    for name in SCAN_TARGETS:
        p = APP_DIR / name
        if p.exists():
            files.append(p)
    for d in SCAN_DIRS:
        d_path = APP_DIR / d
        if d_path.is_dir():
            files.extend(sorted(d_path.rglob("*.py")))
    # ui/vitals 와 ui/login_ui 는 새 모듈이라 보존 대상 아님
    # ui/analytics 도 새 모듈
    return [f for f in files if "__pycache__" not in str(f)]


def _func_sig(node: ast.AST) -> str:
    """함수 정의 → 'name(arg1, arg2, *, kw=default)' 시그니처 문자열."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    args = node.args
    parts: List[str] = []
    pos = [a.arg for a in args.posonlyargs] if args.posonlyargs else []
    if pos:
        parts.append(", ".join(pos) + ", /")
    parts.extend(a.arg for a in args.args)
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    elif args.kwonlyargs:
        parts.append("*")
    parts.extend(a.arg for a in args.kwonlyargs)
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    return f"{node.name}({', '.join(parts)})"


def _extract_sql_strings(tree: ast.AST) -> Set[str]:
    """문자열 리터럴 중 SQL 키워드로 시작하는 것만 수집 (정규화: lowercase, whitespace 압축)."""
    out: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            if _SQL_KEYWORDS.search(s):
                # 핵심 형태만 — whitespace 정규화 + 짧으면 무시 (false positive 방지)
                normalized = re.sub(r"\s+", " ", s).strip()
                if len(normalized) >= 30:
                    out.add(normalized.lower())
    return out


def _extract_session_state_keys(tree: ast.AST) -> Set[str]:
    """st.session_state["k"] 또는 st.session_state.k 형태의 key 수집."""
    out: Set[str] = set()
    for node in ast.walk(tree):
        # st.session_state["k"]  /  st.session_state['k']
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            v = node.value
            if (
                isinstance(v, ast.Attribute)
                and v.attr == "session_state"
                and isinstance(v.value, ast.Name)
                and v.value.id == "st"
                and isinstance(node.slice.value, str)
            ):
                out.add(node.slice.value)
        # st.session_state.k
        if isinstance(node, ast.Attribute):
            v = node.value
            if (
                isinstance(v, ast.Attribute)
                and v.attr == "session_state"
                and isinstance(v.value, ast.Name)
                and v.value.id == "st"
            ):
                out.add(node.attr)
    return out


def _extract_top_imports(tree: ast.AST) -> Set[str]:
    """top-level import 모듈 이름만 수집."""
    out: Set[str] = set()
    for node in tree.body if hasattr(tree, "body") else []:
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


def _scan_file(path: Path) -> Dict[str, List[str]]:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(path))
    funcs = sorted({_func_sig(n) for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))} - {""})
    return {
        "functions": funcs,
        "sql_strings": sorted(_extract_sql_strings(tree)),
        "session_state_keys": sorted(_extract_session_state_keys(tree)),
        "imports": sorted(_extract_top_imports(tree)),
    }


def _build_snapshot() -> Dict[str, Dict[str, List[str]]]:
    snap: Dict[str, Dict[str, List[str]]] = {}
    for f in _iter_py_files():
        rel = str(f.relative_to(APP_DIR)).replace("\\", "/")
        try:
            snap[rel] = _scan_file(f)
        except SyntaxError as e:
            print(f"[SKIP] {rel}: SyntaxError {e}", file=sys.stderr)
    return snap


def _diff(baseline: Dict, current: Dict) -> List[str]:
    """베이스라인에 있고 현재 없는 것 (= 삭제) 만 violation."""
    issues: List[str] = []
    for path, b in baseline.items():
        c = current.get(path, {})
        if not c:
            issues.append(f"REMOVED FILE: {path}")
            continue
        for kind in ("functions", "sql_strings", "session_state_keys", "imports"):
            b_set = set(b.get(kind, []))
            c_set = set(c.get(kind, []))
            removed = b_set - c_set
            for item in sorted(removed):
                issues.append(f"REMOVED {kind}: {path} :: {item}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-baseline", action="store_true",
        help="현재 상태를 베이스라인으로 저장 (STAGE 2 시작 시 1회).",
    )
    parser.add_argument(
        "--baseline", default=str(BASELINE_PATH),
        help="베이스라인 JSON 경로 (기본: scripts/backend_freeze_baseline.json).",
    )
    args = parser.parse_args()

    snap = _build_snapshot()

    if args.emit_baseline:
        Path(args.baseline).parent.mkdir(parents=True, exist_ok=True)
        with open(args.baseline, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2, sort_keys=True)
        n = sum(len(v.get("functions", [])) for v in snap.values())
        s = sum(len(v.get("sql_strings", [])) for v in snap.values())
        k = sum(len(v.get("session_state_keys", [])) for v in snap.values())
        print(f"[OK] baseline written: {args.baseline}")
        print(f"     {len(snap)} files · {n} functions · {s} SQL · {k} session keys")
        return 0

    if not Path(args.baseline).exists():
        print(f"[ERROR] baseline missing: {args.baseline}", file=sys.stderr)
        print("        run with --emit-baseline first", file=sys.stderr)
        return 2

    with open(args.baseline, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    issues = _diff(baseline, snap)
    if issues:
        print(f"[FAIL] backend freeze violations ({len(issues)}):")
        for i in issues:
            print("  -", i)
        return 1

    n = sum(len(v.get("functions", [])) for v in snap.values())
    s = sum(len(v.get("sql_strings", [])) for v in snap.values())
    k = sum(len(v.get("session_state_keys", [])) for v in snap.values())
    print(f"[PASS] backend freeze ({len(snap)} files · {n} fns · {s} SQL · {k} session keys)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
