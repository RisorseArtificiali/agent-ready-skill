#!/usr/bin/env python3
"""secret_hygiene.py — secret-hygiene signals (NOT a secret scanner).

Feeds (PRD-1): Dim 6 ``secret_hygiene``.

Checks:
    - Does ``.gitignore`` cover common secret patterns (.env, *.pem, id_rsa,
      *credentials*, etc.)?
    - Is a ``.env.example`` (or similar template) present?
    - Lightweight regex scan for obviously committed secrets (known key prefixes
      / private-key headers) as a SIGNAL only — explicit false-positive and
      false-negative caveats. Report recommends a real scanner (gitleaks /
      trufflehog) for enforcement.

SAFETY: read-only. No writes, no network, no exec.

Usage:
    python3 secret_hygiene.py [TARGET_PATH] [--max-files N] [--max-findings N]

Output: one JSON object on stdout:
    {"script": "secret_hygiene", "version": 1, "ok": true, "data": {...}, "warnings": []}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

SCRIPT_NAME = "secret_hygiene"
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

DEFAULT_MAX_FILES = 8000
DEFAULT_MAX_FINDINGS = 50
MAX_FILE_BYTES = 1_000_000

# Secret-ish patterns we expect to see covered by .gitignore.
EXPECTED_IGNORE_PATTERNS = {
    ".env": [".env", "*.env", ".env.*"],
    "*.pem": ["*.pem"],
    "id_rsa": ["id_rsa", "*id_rsa*", "id_*"],
    "*credentials*": ["*credentials*", "credentials*", "*.credentials"],
    "*.key": ["*.key"],
    "*.p12 / *.pfx": ["*.p12", "*.pfx"],
}

ENV_EXAMPLE_NAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    "env.example",
    ".env.example.local",
}

# High-confidence committed-secret regexes (low false-positive set).
_COMMITTED_SECRET_PATTERNS = [
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("stripe_secret_key", re.compile(r"\bsk_live_[0-9A-Za-z]{16,}\b")),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}\b")),
    ("generic_assigned_secret", re.compile(
        r"""(?i)\b(?:api[_-]?key|secret|passwd|password|token)\b\s*[:=]\s*['"][^'"\s]{12,}['"]""")),
]

# Files/extensions that should NOT trigger committed-secret findings (examples,
# tests, docs, lockfiles) to reduce noise.
_SCAN_SKIP_NAME_SUBSTR = (".example", ".sample", ".template", ".dist", ".lock")
_SCAN_SKIP_EXTS = {".lock", ".min.js", ".map", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}
_SCAN_TEXT_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".rb",
    ".java", ".php", ".sh", ".bash", ".env", ".yml", ".yaml", ".toml", ".json",
    ".ini", ".cfg", ".conf", ".properties", ".txt", ".xml", ".tf", ".tfvars",
}


def _read_gitignore(root: str) -> list[str]:
    path = os.path.join(root, ".gitignore")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = []
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                lines.append(line)
            return lines
    except OSError:
        return []


def _gitignore_covers(entries: list[str], variants: list[str]) -> bool:
    norm = {e.lstrip("/").rstrip("/") for e in entries}
    raw = set(entries)
    for variant in variants:
        v = variant.lstrip("/").rstrip("/")
        if variant in raw or v in norm:
            return True
        # A directory-style or wildcard-broad ignore can also cover it.
        for e in norm:
            if e == variant or e == v:
                return True
    return False


def _find_env_example(root: str) -> list[str]:
    found: list[str] = []
    try:
        for name in os.listdir(root):
            if name in ENV_EXAMPLE_NAMES:
                found.append(name)
    except OSError:
        pass
    return sorted(found)


def _scan_committed_secrets(root: str, max_files: int, max_findings: int,
                            warnings: list[str]) -> tuple[list[dict], int]:
    findings: list[dict] = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".cache")]
        for name in filenames:
            lower = name.lower()
            ext = os.path.splitext(lower)[1]
            base = os.path.splitext(lower)[0]
            is_dotenv = lower == ".env" or lower.startswith(".env.")
            # Only scan reasonable text files; .env (real, not example) included.
            if not is_dotenv and ext not in _SCAN_TEXT_EXTS:
                continue
            if ext in _SCAN_SKIP_EXTS:
                continue
            if any(s in lower for s in _SCAN_SKIP_NAME_SUBSTR):
                continue
            if scanned >= max_files:
                warnings.append(f"scan cap {max_files} reached; secret scan is partial")
                return findings, scanned
            abs_path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(abs_path) > MAX_FILE_BYTES:
                    continue
                with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue
            scanned += 1
            rel = os.path.relpath(abs_path, root)
            for label, pat in _COMMITTED_SECRET_PATTERNS:
                m = pat.search(content)
                if m:
                    line_no = content.count("\n", 0, m.start()) + 1
                    findings.append({"file": rel, "type": label, "line": line_no})
                    if len(findings) >= max_findings:
                        warnings.append(f"finding cap {max_findings} reached")
                        return findings, scanned
    return findings, scanned


def collect(root: str, max_files: int, max_findings: int, warnings: list[str]) -> dict:
    gitignore_entries = _read_gitignore(root)
    has_gitignore = os.path.isfile(os.path.join(root, ".gitignore"))

    coverage = {}
    covered_count = 0
    for label, variants in EXPECTED_IGNORE_PATTERNS.items():
        covered = _gitignore_covers(gitignore_entries, variants) if has_gitignore else False
        coverage[label] = covered
        if covered:
            covered_count += 1

    env_examples = _find_env_example(root)
    findings, scanned = _scan_committed_secrets(root, max_files, max_findings, warnings)

    return {
        "has_gitignore": has_gitignore,
        "gitignore_secret_coverage": coverage,
        "gitignore_coverage_pct": round(100.0 * covered_count / len(EXPECTED_IGNORE_PATTERNS), 1),
        "env_example_present": bool(env_examples),
        "env_example_files": env_examples,
        "committed_secret_findings": findings,
        "committed_secret_count": len(findings),
        "files_scanned": scanned,
        "caveat": (
            "Signal only: regex-based, prone to false positives and negatives. "
            "Use a dedicated scanner (gitleaks/trufflehog) for enforcement."
        ),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Secret-hygiene signals (read-only).")
    parser.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-findings", type=int, default=DEFAULT_MAX_FINDINGS)
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
        data = collect(root, args.max_files, args.max_findings, warnings)
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
