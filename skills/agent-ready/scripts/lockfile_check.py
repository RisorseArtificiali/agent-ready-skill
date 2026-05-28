#!/usr/bin/env python3
"""lockfile_check.py — dependency lockfile detection + gitignore check.

Feeds (PRD-1): Dim 6 ``supply_chain_pinning``.

Detects lockfiles per ecosystem and checks whether any detected lockfile is
gitignored (a committed lockfile is the supply-chain-pinning signal; an ignored
lockfile defeats reproducible installs).

SAFETY: read-only. No writes, no network, no exec.

Usage:
    python3 lockfile_check.py [TARGET_PATH] [--max-depth N]

Output: one JSON object on stdout:
    {"script": "lockfile_check", "version": 1, "ok": true, "data": {...}, "warnings": []}
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys

SCRIPT_NAME = "lockfile_check"
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

DEFAULT_MAX_DEPTH = 4

# Lockfile filename -> ecosystem.
LOCKFILE_ECOSYSTEM = {
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "bun.lockb": "bun",
    "bun.lock": "bun",
    "poetry.lock": "poetry",
    "Pipfile.lock": "pipenv",
    "pdm.lock": "pdm",
    "uv.lock": "uv",
    "conda-lock.yml": "conda",
    "requirements.txt": "pip (requirements)",
    "Cargo.lock": "cargo",
    "Gemfile.lock": "bundler",
    "composer.lock": "composer",
    "go.sum": "go modules",
    "go.mod": "go modules",
    "gradle.lockfile": "gradle",
    "mix.lock": "mix",
    "packages.lock.json": "nuget",
    "flake.lock": "nix",
}

# requirements.txt is a weaker pin signal (not always fully pinned).
_WEAK_LOCK = {"requirements.txt", "go.mod"}


def _read_gitignore(root: str) -> list[str]:
    path = os.path.join(root, ".gitignore")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            out = []
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                out.append(line)
            return out
    except OSError:
        return []


def _is_gitignored(rel_path: str, patterns: list[str]) -> bool:
    """Best-effort .gitignore match (no negation/precedence semantics)."""
    rel = rel_path.replace("\\", "/")
    base = os.path.basename(rel)
    for raw in patterns:
        pat = raw
        if pat.startswith("!"):  # negation not modeled; treat as non-match
            continue
        anchored = pat.startswith("/")
        pat = pat.lstrip("/").rstrip("/")
        if not pat:
            continue
        if "/" in pat:
            if anchored:
                if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat + "/*"):
                    return True
            else:
                if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, "*/" + pat):
                    return True
        else:
            # Pattern matches a basename at any depth.
            if fnmatch.fnmatch(base, pat):
                return True
            # Or matches a path component (directory ignore).
            if any(fnmatch.fnmatch(part, pat) for part in rel.split("/")):
                return True
    return False


def _walk_depth(root: str, max_depth: int):
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        if depth >= max_depth:
            dirnames[:] = []
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for name in filenames:
            yield dirpath, name


def collect(root: str, max_depth: int, warnings: list[str]) -> dict:
    gitignore = _read_gitignore(root)
    has_gitignore = os.path.isfile(os.path.join(root, ".gitignore"))

    found: list[dict] = []
    ecosystems_seen: set[str] = set()
    any_ignored = False
    strong_committed = False

    for dirpath, name in _walk_depth(root, max_depth):
        eco = LOCKFILE_ECOSYSTEM.get(name)
        if not eco:
            continue
        abs_path = os.path.join(dirpath, name)
        rel = os.path.relpath(abs_path, root)
        ignored = _is_gitignored(rel, gitignore) if has_gitignore else False
        weak = name in _WEAK_LOCK
        found.append(
            {
                "file": rel,
                "ecosystem": eco,
                "gitignored": ignored,
                "strength": "weak" if weak else "strong",
            }
        )
        ecosystems_seen.add(eco)
        if ignored:
            any_ignored = True
        elif not weak:
            strong_committed = True

    found.sort(key=lambda x: x["file"])

    return {
        "has_gitignore": has_gitignore,
        "lockfiles_found": found,
        "lockfile_count": len(found),
        "ecosystems": sorted(ecosystems_seen),
        "any_lockfile_gitignored": any_ignored,
        "strong_lockfile_committed": strong_committed,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Lockfile detection + gitignore check (read-only).")
    parser.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH)
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
        data = collect(root, args.max_depth, warnings)
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
