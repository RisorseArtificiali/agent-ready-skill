#!/usr/bin/env python3
"""coverage_signals.py — type-annotation & docstring coverage signals.

Feeds (PRD-1): Dim 3 ``feedback_quality``, Dim 7 ``docs_comprehension_signals``.

For Python (precise, via ``ast``):
    - % of functions/methods with a return or any parameter annotation
    - % of modules / classes / functions+methods carrying a docstring

For TS/JS (coarse regex, flagged ``confidence: low``):
    - rough share of function/method signatures with a ``: type`` annotation
    - presence of JSDoc (``/** ... */``) blocks

SAFETY: read-only. Python parsed with ``ast.parse`` (safe parse, no exec).
No writes, no network, no exec.

Usage:
    python3 coverage_signals.py [TARGET_PATH] [--max-files N]

Output: one JSON object on stdout:
    {"script": "coverage_signals", "version": 1, "ok": true, "data": {...}, "warnings": []}
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys

SCRIPT_NAME = "coverage_signals"
VERSION = 1

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "__pycache__",
    ".agent-ready",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
}

DEFAULT_MAX_FILES = 6000
MAX_FILE_BYTES = 1_000_000

PY_EXTS = {".py", ".pyi"}
TS_EXTS = {".ts", ".tsx"}
JS_EXTS = {".js", ".jsx", ".mjs", ".cjs"}

# JS/TS heuristics.
_RE_FUNC_SIG = re.compile(
    r"(?:function\s+[A-Za-z_$][\w$]*\s*\(|"
    r"(?:async\s+)?[A-Za-z_$][\w$]*\s*\([^)]*\)\s*(?::[^={;]+)?\s*(?:=>|\{)|"
    r"(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^={;]+)?\s*=>)"
)
# A typed parameter or typed return looks like ": <Type>".
_RE_TYPE_ANNOT = re.compile(r":\s*[A-Za-z_$][\w$<>\[\].|,\s]*")
_RE_JSDOC = re.compile(r"/\*\*.*?\*/", re.DOTALL)


def _read_text(abs_path: str) -> str | None:
    try:
        if os.path.getsize(abs_path) > MAX_FILE_BYTES:
            return None
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


class _PyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.funcs = 0
        self.funcs_annotated = 0
        self.funcs_with_doc = 0
        self.classes = 0
        self.classes_with_doc = 0

    def _handle_function(self, node) -> None:
        self.funcs += 1
        a = node.args
        annotated = node.returns is not None
        if not annotated:
            all_args = (
                list(a.posonlyargs)
                + list(a.args)
                + list(a.kwonlyargs)
                + ([a.vararg] if a.vararg else [])
                + ([a.kwarg] if a.kwarg else [])
            )
            # Ignore the implicit self/cls for the annotation check.
            checkable = [arg for arg in all_args if arg and arg.arg not in ("self", "cls")]
            annotated = any(arg.annotation is not None for arg in checkable)
        if annotated:
            self.funcs_annotated += 1
        if ast.get_docstring(node):
            self.funcs_with_doc += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):  # noqa: N802
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):  # noqa: N802
        self._handle_function(node)

    def visit_ClassDef(self, node):  # noqa: N802
        self.classes += 1
        if ast.get_docstring(node):
            self.classes_with_doc += 1
        self.generic_visit(node)


def _analyze_python(text: str):
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    visitor = _PyVisitor()
    visitor.visit(tree)
    module_has_doc = 1 if ast.get_docstring(tree) else 0
    return {
        "funcs": visitor.funcs,
        "funcs_annotated": visitor.funcs_annotated,
        "funcs_with_doc": visitor.funcs_with_doc,
        "classes": visitor.classes,
        "classes_with_doc": visitor.classes_with_doc,
        "modules": 1,
        "modules_with_doc": module_has_doc,
    }


def _analyze_jsts(text: str):
    sigs = _RE_FUNC_SIG.findall(text)
    func_count = len(sigs)
    annotated = 0
    for sig in sigs:
        # Count a signature as "typed" if it contains a ": Type" beyond a bare colon.
        if _RE_TYPE_ANNOT.search(sig):
            annotated += 1
    jsdoc_blocks = len(_RE_JSDOC.findall(text))
    return {
        "funcs": func_count,
        "funcs_annotated": annotated,
        "jsdoc_blocks": jsdoc_blocks,
    }


def collect(root: str, max_files: int, warnings: list[str]) -> dict:
    py = {
        "funcs": 0,
        "funcs_annotated": 0,
        "funcs_with_doc": 0,
        "classes": 0,
        "classes_with_doc": 0,
        "modules": 0,
        "modules_with_doc": 0,
        "files": 0,
    }
    jsts = {"funcs": 0, "funcs_annotated": 0, "jsdoc_blocks": 0, "files": 0, "ts_files": 0}
    seen = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in PY_EXTS and ext not in TS_EXTS and ext not in JS_EXTS:
                continue
            if seen >= max_files:
                warnings.append(f"file cap {max_files} reached; coverage is partial")
                break
            abs_path = os.path.join(dirpath, name)
            text = _read_text(abs_path)
            if text is None:
                continue
            seen += 1
            if ext in PY_EXTS:
                res = _analyze_python(text)
                if res is None:
                    warnings.append(f"python parse failed: {os.path.relpath(abs_path, root)}")
                    continue
                for k in ("funcs", "funcs_annotated", "funcs_with_doc", "classes",
                          "classes_with_doc", "modules", "modules_with_doc"):
                    py[k] += res[k]
                py["files"] += 1
            else:
                res = _analyze_jsts(text)
                jsts["funcs"] += res["funcs"]
                jsts["funcs_annotated"] += res["funcs_annotated"]
                jsts["jsdoc_blocks"] += res["jsdoc_blocks"]
                jsts["files"] += 1
                if ext in TS_EXTS:
                    jsts["ts_files"] += 1
        else:
            continue
        break

    def pct(num: int, den: int) -> float | None:
        return round(100.0 * num / den, 2) if den else None

    python_signals = {
        "confidence": "high",
        "files": py["files"],
        "function_count": py["funcs"],
        "class_count": py["classes"],
        "type_annotation_pct": pct(py["funcs_annotated"], py["funcs"]),
        "function_docstring_pct": pct(py["funcs_with_doc"], py["funcs"]),
        "class_docstring_pct": pct(py["classes_with_doc"], py["classes"]),
        "module_docstring_pct": pct(py["modules_with_doc"], py["modules"]),
    }

    jsts_signals = {
        "confidence": "low",
        "files": jsts["files"],
        "ts_files": jsts["ts_files"],
        "function_signature_count": jsts["funcs"],
        "typed_signature_pct": pct(jsts["funcs_annotated"], jsts["funcs"]),
        "jsdoc_block_count": jsts["jsdoc_blocks"],
        "note": "regex heuristic; not AST-accurate",
    }

    return {
        "python": python_signals,
        "typescript_javascript": jsts_signals,
        "files_analyzed": seen,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Type/docstring coverage signals (read-only).")
    parser.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    args = parser.parse_args(argv)

    warnings: list[str] = []
    root = os.path.abspath(args.target)

    if not os.path.isdir(root):
        print(
            json.dumps(
                {
                    "script": SCRIPT_NAME,
                    "version": VERSION,
                    "ok": False,
                    "data": {},
                    "warnings": [f"target is not a directory: {args.target}"],
                }
            )
        )
        return 0

    ok = True
    try:
        data = collect(root, args.max_files, warnings)
    except Exception as exc:
        ok = False
        data = {}
        warnings.append(f"unexpected error: {type(exc).__name__}: {exc}")

    print(
        json.dumps(
            {
                "script": SCRIPT_NAME,
                "version": VERSION,
                "ok": ok,
                "data": data,
                "warnings": warnings,
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
