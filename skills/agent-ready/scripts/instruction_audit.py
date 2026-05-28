#!/usr/bin/env python3
"""instruction_audit.py — instruction-file bloat / boilerplate / drift signals.

Feeds (PRD-1): Dim 1 ``instruction_conciseness``, ``cross_agent_bridge``.

For each agent instruction file (AGENTS.md, CLAUDE.md, and common vendor
variants):
    - measure length (lines, non-empty lines, approx tokens)
    - detect generic-boilerplate phrases (heuristic list)
Across multiple instruction files:
    - detect duplication (high textual overlap via difflib) — a maintenance/drift
      risk and a signal about whether files are bridged vs divergent copies
    - flag potential contradictions (same directive key, conflicting values)

SAFETY: read-only. No writes, no network, no exec.

Usage:
    python3 instruction_audit.py [TARGET_PATH] [--conciseness-limit N]

Output: one JSON object on stdout:
    {"script": "instruction_audit", "version": 1, "ok": true, "data": {...}, "warnings": []}
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys

SCRIPT_NAME = "instruction_audit"
VERSION = 1
MAX_FILE_BYTES = 1_000_000
DEFAULT_CONCISENESS_LIMIT = 300  # lines; PRD-1 penalizes >~200-300

# Instruction files at repo root (and a couple of well-known nested locations).
ROOT_INSTRUCTION_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CODEX.md",
    ".cursorrules",
    ".windsurfrules",
    ".github/copilot-instructions.md",
    ".pi/SYSTEM.md",
    "opencode.json",
]

# Generic-boilerplate phrases (lower-signal filler often copied verbatim).
_BOILERPLATE_PHRASES = [
    "you are a helpful assistant",
    "you are an ai assistant",
    "as an ai language model",
    "follow best practices",
    "write clean code",
    "write clean, maintainable code",
    "use meaningful variable names",
    "add comments where necessary",
    "make sure to handle errors",
    "always write tests",
    "be concise",
    "be helpful",
    "think step by step",
    "do not hallucinate",
    "use your best judgment",
    "feel free to",
    "as needed",
    "where appropriate",
    "industry standard",
    "production-ready code",
    "high-quality code",
    "follow the dry principle",
    "keep it simple",
]

_APPROX_CHARS_PER_TOKEN = 4

# Directive lines we can compare across files to flag contradictions, e.g.
# "line length 119" vs "line length 100".
_DIRECTIVE_RE = re.compile(
    r"(?i)\b(line[\s-]?length|max[\s-]?line|indent(?:ation)?|tab[\s-]?size|"
    r"python[\s-]?version|node[\s-]?version)\b[^0-9]{0,20}(\d{1,4})"
)


def _read_text(abs_path: str) -> str | None:
    try:
        if os.path.getsize(abs_path) > MAX_FILE_BYTES:
            return None
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _approx_tokens(text: str) -> int:
    return max(0, len(text) // _APPROX_CHARS_PER_TOKEN)


def _normalize_for_overlap(text: str) -> list[str]:
    """Normalize to comparable non-trivial lines."""
    out = []
    for raw in text.splitlines():
        line = raw.strip().lower()
        if len(line) < 8:  # ignore blanks and trivial lines
            continue
        out.append(line)
    return out


def _detect_boilerplate(text: str) -> list[str]:
    low = text.lower()
    return [phrase for phrase in _BOILERPLATE_PHRASES if phrase in low]


def _extract_directives(text: str) -> dict[str, str]:
    directives: dict[str, str] = {}
    for m in _DIRECTIVE_RE.finditer(text):
        key = re.sub(r"[\s\-]+", "_", m.group(1).strip().lower())
        # Normalize synonymous keys.
        if key in ("max_line", "line_length"):
            key = "line_length"
        directives.setdefault(key, m.group(2))
    return directives


def _discover_files(root: str) -> list[str]:
    found: list[str] = []
    for rel in ROOT_INSTRUCTION_FILES:
        abs_path = os.path.join(root, rel)
        if os.path.isfile(abs_path):
            found.append(rel)
    return found


def collect(root: str, conciseness_limit: int, warnings: list[str]) -> dict:
    rel_files = _discover_files(root)

    files_report: list[dict] = []
    norm_lines: dict[str, list[str]] = {}
    directives: dict[str, dict[str, str]] = {}

    for rel in rel_files:
        abs_path = os.path.join(root, rel)
        text = _read_text(abs_path)
        if text is None:
            warnings.append(f"could not read instruction file: {rel}")
            continue
        all_lines = text.splitlines()
        non_empty = [ln for ln in all_lines if ln.strip()]
        boilerplate = _detect_boilerplate(text)
        files_report.append(
            {
                "file": rel,
                "lines": len(all_lines),
                "non_empty_lines": len(non_empty),
                "approx_tokens": _approx_tokens(text),
                "over_conciseness_limit": len(all_lines) > conciseness_limit,
                "boilerplate_phrases": boilerplate,
                "boilerplate_count": len(boilerplate),
            }
        )
        norm_lines[rel] = _normalize_for_overlap(text)
        directives[rel] = _extract_directives(text)

    # Pairwise duplication via difflib ratio over normalized non-trivial lines.
    duplication_pairs: list[dict] = []
    rels = list(norm_lines.keys())
    for i in range(len(rels)):
        for j in range(i + 1, len(rels)):
            a, b = rels[i], rels[j]
            seq_a, seq_b = norm_lines[a], norm_lines[b]
            if not seq_a or not seq_b:
                continue
            ratio = difflib.SequenceMatcher(None, seq_a, seq_b).ratio()
            set_a, set_b = set(seq_a), set(seq_b)
            shared = len(set_a & set_b)
            jaccard = shared / len(set_a | set_b) if (set_a | set_b) else 0.0
            if ratio >= 0.4 or jaccard >= 0.4:
                duplication_pairs.append(
                    {
                        "files": [a, b],
                        "similarity_ratio": round(ratio, 3),
                        "shared_line_jaccard": round(jaccard, 3),
                        "shared_lines": shared,
                    }
                )

    # Contradiction detection: same directive key, differing values across files.
    contradictions: list[dict] = []
    all_keys = set()
    for d in directives.values():
        all_keys.update(d.keys())
    for key in sorted(all_keys):
        values: dict[str, list[str]] = {}
        for rel, d in directives.items():
            if key in d:
                values.setdefault(d[key], []).append(rel)
        if len(values) > 1:
            contradictions.append(
                {
                    "directive": key,
                    "conflicting_values": {val: files for val, files in values.items()},
                }
            )

    total_boilerplate = sum(f["boilerplate_count"] for f in files_report)
    any_over_limit = any(f["over_conciseness_limit"] for f in files_report)

    return {
        "instruction_files_found": rel_files,
        "file_count": len(files_report),
        "files": files_report,
        "conciseness_limit": conciseness_limit,
        "any_over_conciseness_limit": any_over_limit,
        "total_boilerplate_phrases": total_boilerplate,
        "duplication_pairs": duplication_pairs,
        "has_duplication": bool(duplication_pairs),
        "contradictions": contradictions,
        "has_contradictions": bool(contradictions),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Instruction-file bloat/drift audit (read-only).")
    parser.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
    parser.add_argument("--conciseness-limit", type=int, default=DEFAULT_CONCISENESS_LIMIT)
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
        data = collect(root, args.conciseness_limit, warnings)
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
