#!/usr/bin/env python3
"""repo_map.py — stdlib-only repo symbol map + in-degree ranking.

Feeds (PRD-1): Dim 2 ``repo_map_availability``, Dim 7 ``docs_comprehension_signals``.

Extracts symbols (classes, functions/methods) and import/reference edges, ranks
files and symbols by in-degree using a pure-Python graph (no graph library), and
emits a token-budgeted ranked map.

SAFETY: read-only. Python files are parsed with ``ast.parse`` (a safe parse — it
never imports or executes the target code). Other languages use coarse regex
heuristics flagged as lower confidence. No writes, no network, no exec.

Usage:
    python3 repo_map.py [TARGET_PATH] [--max-files N] [--token-budget N]

Output: one JSON object on stdout:
    {"script": "repo_map", "version": 1, "ok": true, "data": {...}, "warnings": []}
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys

SCRIPT_NAME = "repo_map"
VERSION = 1

# Directories never worth walking into.
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

# Bounds to keep the scan fast on large repos.
DEFAULT_MAX_FILES = 4000
DEFAULT_TOKEN_BUDGET = 6000  # approx tokens for the emitted map
MAX_FILE_BYTES = 1_000_000  # skip files larger than ~1MB
MAX_RANKED_FILES = 60
MAX_SYMBOLS_PER_FILE = 40
MAX_RANKED_SYMBOLS = 80

# Language detection by extension.
PY_EXTS = {".py", ".pyi"}
JS_TS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
GO_EXTS = {".go"}
RUST_EXTS = {".rs"}
RUBY_EXTS = {".rb"}
JAVA_EXTS = {".java"}
C_LIKE_EXTS = {".c", ".h", ".cpp", ".cc", ".hpp", ".cs"}

REGEX_EXTS = JS_TS_EXTS | GO_EXTS | RUST_EXTS | RUBY_EXTS | JAVA_EXTS | C_LIKE_EXTS

# Lightweight per-language symbol/definition regexes (lower confidence).
_REGEX_SYMBOL_PATTERNS = {
    "js": [
        re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)"),
        re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)"),
        re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\("),
        re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?[A-Za-z_$(]"),
    ],
    "go": [
        re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"),
        re.compile(r"^\s*type\s+([A-Za-z_]\w*)\s+"),
    ],
    "rust": [
        re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)"),
        re.compile(r"^\s*(?:pub\s+)?struct\s+([A-Za-z_]\w*)"),
        re.compile(r"^\s*(?:pub\s+)?enum\s+([A-Za-z_]\w*)"),
        re.compile(r"^\s*(?:pub\s+)?trait\s+([A-Za-z_]\w*)"),
    ],
    "ruby": [
        re.compile(r"^\s*def\s+([A-Za-z_]\w*[!?=]?)"),
        re.compile(r"^\s*class\s+([A-Za-z_]\w*)"),
        re.compile(r"^\s*module\s+([A-Za-z_]\w*)"),
    ],
    "java": [
        re.compile(r"^\s*(?:public|private|protected)?\s*(?:abstract\s+|final\s+)?class\s+([A-Za-z_]\w*)"),
        re.compile(r"^\s*(?:public|private|protected)?\s*interface\s+([A-Za-z_]\w*)"),
    ],
    "c": [
        re.compile(r"^\s*(?:struct|class)\s+([A-Za-z_]\w*)"),
    ],
}

# Lightweight import/reference regexes per language.
_REGEX_IMPORT_PATTERNS = {
    "js": [
        re.compile(r"""(?:import|export)\s+(?:[\w*{},\s]+\s+from\s+)?['"]([^'"]+)['"]"""),
        re.compile(r"""require\(\s*['"]([^'"]+)['"]\s*\)"""),
    ],
    "go": [
        re.compile(r"""^\s*import\s+(?:[A-Za-z_.]+\s+)?["`]([^"`]+)["`]"""),
    ],
    "rust": [
        re.compile(r"^\s*use\s+([A-Za-z_][\w:]*)"),
    ],
    "ruby": [
        re.compile(r"""^\s*require(?:_relative)?\s+['"]([^'"]+)['"]"""),
    ],
    "java": [
        re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)"),
    ],
    "c": [
        re.compile(r"""^\s*#\s*include\s+[<"]([^>"]+)[>"]"""),
    ],
}


def _lang_for_ext(ext: str) -> str | None:
    if ext in JS_TS_EXTS:
        return "js"
    if ext in GO_EXTS:
        return "go"
    if ext in RUST_EXTS:
        return "rust"
    if ext in RUBY_EXTS:
        return "ruby"
    if ext in JAVA_EXTS:
        return "java"
    if ext in C_LIKE_EXTS:
        return "c"
    return None


def _approx_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token)."""
    return max(1, len(text) // 4)


def _iter_source_files(root: str, max_files: int, warnings: list[str]):
    """Yield (abs_path, rel_path) for candidate source files, bounded."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in PY_EXTS and ext not in REGEX_EXTS:
                continue
            abs_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(abs_path, root)
            count += 1
            if count > max_files:
                warnings.append(f"file cap {max_files} reached; map is partial")
                return
            yield abs_path, rel_path


def _read_text(abs_path: str) -> str | None:
    try:
        if os.path.getsize(abs_path) > MAX_FILE_BYTES:
            return None
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _module_name_from_rel(rel_path: str) -> str:
    """Map a Python file path to a dotted module name (best effort)."""
    no_ext = os.path.splitext(rel_path)[0]
    parts = [p for p in no_ext.replace("\\", "/").split("/") if p and p != "."]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _parse_python(text: str, rel_path: str):
    """Return (symbols, imports) for a Python source via ast. Safe parse only."""
    symbols: list[dict] = []
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None, None

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({"name": node.name, "kind": "function", "line": node.lineno})
        elif isinstance(node, ast.ClassDef):
            symbols.append({"name": node.name, "kind": "class", "line": node.lineno})
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        {"name": f"{node.name}.{child.name}", "kind": "method", "line": child.lineno}
                    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return symbols, imports


def _parse_regex(text: str, lang: str):
    """Coarse regex symbol/import extraction for non-Python languages."""
    symbols: list[dict] = []
    imports: list[str] = []
    sym_patterns = _REGEX_SYMBOL_PATTERNS.get(lang, [])
    imp_patterns = _REGEX_IMPORT_PATTERNS.get(lang, [])
    for lineno, line in enumerate(text.splitlines(), start=1):
        if len(symbols) < MAX_SYMBOLS_PER_FILE * 2:
            for pat in sym_patterns:
                m = pat.match(line)
                if m:
                    symbols.append({"name": m.group(1), "kind": "symbol", "line": lineno})
                    break
        for pat in imp_patterns:
            m = pat.search(line)
            if m:
                imports.append(m.group(1))
                break
    return symbols, imports


def build_map(root: str, max_files: int, token_budget: int, warnings: list[str]) -> dict:
    # Per-file records keyed by rel_path.
    files: dict[str, dict] = {}
    # Map from a python module name -> rel_path (to resolve internal edges).
    module_index: dict[str, str] = {}
    confidence_by_lang: dict[str, str] = {}

    for abs_path, rel_path in _iter_source_files(root, max_files, warnings):
        text = _read_text(abs_path)
        if text is None:
            continue
        ext = os.path.splitext(rel_path)[1].lower()
        if ext in PY_EXTS:
            symbols, imports = _parse_python(text, rel_path)
            if symbols is None:
                warnings.append(f"python parse failed: {rel_path}")
                continue
            lang = "python"
            confidence = "high"
            mod = _module_name_from_rel(rel_path)
            if mod:
                module_index[mod] = rel_path
        else:
            lang = _lang_for_ext(ext) or "other"
            symbols, imports = _parse_regex(text, lang)
            confidence = "low"
        confidence_by_lang[lang] = confidence
        files[rel_path] = {
            "lang": lang,
            "confidence": confidence,
            "symbols": symbols[:MAX_SYMBOLS_PER_FILE],
            "symbol_count": len(symbols),
            "imports": imports,
            "in_degree": 0,
        }

    # Build in-degree edges. For Python, resolve dotted imports to internal files
    # by longest-prefix match against the module index. For other languages,
    # resolve relative-path imports (./foo, ../bar) heuristically.
    edges = 0
    for rel_path, rec in files.items():
        if rec["lang"] == "python":
            for imp in rec["imports"]:
                target = _resolve_python_import(imp, module_index)
                if target and target != rel_path:
                    files[target]["in_degree"] += 1
                    edges += 1
        else:
            for imp in rec["imports"]:
                target = _resolve_relative_import(imp, rel_path, files)
                if target and target != rel_path:
                    files[target]["in_degree"] += 1
                    edges += 1

    ranked_files = sorted(
        files.items(),
        key=lambda kv: (kv[1]["in_degree"], kv[1]["symbol_count"]),
        reverse=True,
    )

    # Token-budgeted emission: include ranked files until we hit the budget.
    out_files: list[dict] = []
    used_tokens = 0
    for rel_path, rec in ranked_files[:MAX_RANKED_FILES]:
        entry = {
            "path": rel_path,
            "lang": rec["lang"],
            "confidence": rec["confidence"],
            "in_degree": rec["in_degree"],
            "symbols": [s["name"] for s in rec["symbols"][:MAX_SYMBOLS_PER_FILE]],
        }
        cost = _approx_tokens(json.dumps(entry))
        if used_tokens + cost > token_budget and out_files:
            warnings.append("token budget reached; map truncated to top files")
            break
        out_files.append(entry)
        used_tokens += cost

    # Top symbols across the repo by containing-file in-degree.
    top_symbols: list[dict] = []
    for rel_path, rec in ranked_files:
        for sym in rec["symbols"]:
            top_symbols.append(
                {
                    "name": sym["name"],
                    "kind": sym["kind"],
                    "file": rel_path,
                    "line": sym["line"],
                    "file_in_degree": rec["in_degree"],
                }
            )
    top_symbols.sort(key=lambda s: s["file_in_degree"], reverse=True)
    top_symbols = top_symbols[:MAX_RANKED_SYMBOLS]

    return {
        "files_analyzed": len(files),
        "total_edges": edges,
        "confidence_by_lang": confidence_by_lang,
        "ranked_files": out_files,
        "top_symbols": top_symbols,
        "approx_tokens": used_tokens,
        "token_budget": token_budget,
    }


def _resolve_python_import(imp: str, module_index: dict[str, str]) -> str | None:
    """Resolve a dotted import to an internal file via longest-prefix match."""
    if imp in module_index:
        return module_index[imp]
    parts = imp.split(".")
    for i in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:i])
        if prefix in module_index:
            return module_index[prefix]
    return None


def _resolve_relative_import(imp: str, rel_path: str, files: dict[str, dict]) -> str | None:
    """Resolve a relative-path import (./foo, ../bar/baz) to an internal file."""
    if not imp.startswith("."):
        return None
    base_dir = os.path.dirname(rel_path)
    candidate = os.path.normpath(os.path.join(base_dir, imp))
    # Try candidate with each known extension and index files.
    for ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".rb"):
        guess = candidate + ext
        if guess in files:
            return guess
    for idx in ("index.js", "index.ts", "index.jsx", "index.tsx"):
        guess = os.path.normpath(os.path.join(candidate, idx))
        if guess in files:
            return guess
    if candidate in files:
        return candidate
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Repo symbol map + in-degree ranking (read-only).")
    parser.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--token-budget", type=int, default=DEFAULT_TOKEN_BUDGET)
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
        data = build_map(root, args.max_files, args.token_budget, warnings)
    except Exception as exc:  # recoverable: report and continue
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
