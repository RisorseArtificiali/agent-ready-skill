#!/usr/bin/env python3
"""file_metrics.py — per-file LOC, language histogram, oversized-file list.

Feeds (PRD-1): Dim 2 ``file_size_sanity``.

Computes lines-of-code per source file, a language histogram, and lists files
larger than a threshold (default 500 LOC).

SAFETY: read-only. No writes, no network, no exec.

Usage:
    python3 file_metrics.py [TARGET_PATH] [--threshold N] [--max-files N]

Output: one JSON object on stdout:
    {"script": "file_metrics", "version": 1, "ok": true, "data": {...}, "warnings": []}
"""

from __future__ import annotations

import argparse
import json
import os
import sys

SCRIPT_NAME = "file_metrics"
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

DEFAULT_THRESHOLD = 500
DEFAULT_MAX_FILES = 20000
MAX_FILE_BYTES = 5_000_000
MAX_OVERSIZED_LISTED = 100

# Extension -> language label. Counts code-ish files only.
EXT_LANG = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".java": "Java",
    ".kt": "Kotlin",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
    ".bash": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".md": "Markdown",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".toml": "TOML",
    ".json": "JSON",
}


def _count_lines(abs_path: str) -> int | None:
    """Count newline-terminated lines, plus a trailing unterminated line."""
    try:
        if os.path.getsize(abs_path) > MAX_FILE_BYTES:
            return None
    except OSError:
        return None
    lines = 0
    try:
        with open(abs_path, "rb") as fh:
            last_chunk = b""
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                lines += chunk.count(b"\n")
                last_chunk = chunk
            # Count a final line that has content but no trailing newline.
            if last_chunk and not last_chunk.endswith(b"\n"):
                lines += 1
    except OSError:
        return None
    return lines


def collect(root: str, threshold: int, max_files: int, warnings: list[str]) -> dict:
    lang_hist: dict[str, dict] = {}
    oversized: list[dict] = []
    total_files = 0
    total_loc = 0
    capped = False

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            lang = EXT_LANG.get(ext)
            if lang is None:
                continue
            if total_files >= max_files:
                capped = True
                break
            abs_path = os.path.join(dirpath, name)
            loc = _count_lines(abs_path)
            if loc is None:
                continue
            total_files += 1
            total_loc += loc
            bucket = lang_hist.setdefault(lang, {"files": 0, "loc": 0})
            bucket["files"] += 1
            bucket["loc"] += loc
            if loc > threshold:
                oversized.append({"path": os.path.relpath(abs_path, root), "loc": loc, "lang": lang})
        if capped:
            break

    if capped:
        warnings.append(f"file cap {max_files} reached; metrics are partial")

    oversized.sort(key=lambda x: x["loc"], reverse=True)
    oversized_count = len(oversized)
    oversized = oversized[:MAX_OVERSIZED_LISTED]

    # Stable, descending histogram by LOC.
    histogram = dict(
        sorted(lang_hist.items(), key=lambda kv: kv[1]["loc"], reverse=True)
    )

    return {
        "threshold_loc": threshold,
        "total_source_files": total_files,
        "total_loc": total_loc,
        "language_histogram": histogram,
        "oversized_file_count": oversized_count,
        "oversized_files": oversized,
        "oversized_ratio": round(oversized_count / total_files, 4) if total_files else 0.0,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Per-file LOC and language metrics (read-only).")
    parser.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
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
        data = collect(root, args.threshold, args.max_files, warnings)
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
