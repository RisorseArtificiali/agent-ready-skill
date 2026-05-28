#!/usr/bin/env python3
"""test_commands.py — extract (never run) test/build/lint commands.

Feeds (PRD-1): Dim 3 ``test_commands_documented``.

Extracts test / build / lint command definitions from:
    - Makefile (targets)
    - package.json (scripts)
    - pyproject.toml ([tool.poetry.scripts], [project.scripts], common tool cfg)
    - justfile / Justfile (recipes)
    - Taskfile.yml / Taskfile.yaml (tasks)

Reports whether a test command exists. **NEVER executes anything** — this is a
read-only extractor (safety requirement).

``tomllib`` is stdlib only on Python 3.11+. On older interpreters this script
degrades to a minimal regex reader for pyproject.toml (no hard failure).

SAFETY: read-only. No writes, no network, no exec of project commands.

Usage:
    python3 test_commands.py [TARGET_PATH]

Output: one JSON object on stdout:
    {"script": "test_commands", "version": 1, "ok": true, "data": {...}, "warnings": []}
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

SCRIPT_NAME = "test_commands"
VERSION = 1
MAX_FILE_BYTES = 2_000_000

try:
    import tomllib  # type: ignore

    _HAS_TOMLLIB = True
except ImportError:  # Python < 3.11
    tomllib = None  # type: ignore
    _HAS_TOMLLIB = False

# Keyword classification for command names.
_TEST_KEYS = ("test", "tests", "pytest", "spec", "check", "ci")
_BUILD_KEYS = ("build", "compile", "bundle", "dist", "package")
_LINT_KEYS = ("lint", "format", "fmt", "style", "ruff", "eslint", "flake8", "prettier", "black")


def _classify(name: str) -> str:
    low = name.lower()
    if any(k in low for k in _TEST_KEYS):
        return "test"
    if any(k in low for k in _LINT_KEYS):
        return "lint"
    if any(k in low for k in _BUILD_KEYS):
        return "build"
    return "other"


def _read_text(abs_path: str) -> str | None:
    try:
        if os.path.getsize(abs_path) > MAX_FILE_BYTES:
            return None
        with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _parse_makefile(text: str) -> list[dict]:
    """Extract Makefile target names (left of ':', not variable assignments)."""
    out: list[dict] = []
    target_re = re.compile(r"^([A-Za-z0-9_.\-/]+)\s*:(?!=)")
    for line in text.splitlines():
        if line.startswith("\t"):
            continue
        m = target_re.match(line)
        if not m:
            continue
        name = m.group(1)
        if name in (".PHONY", ".DEFAULT", ".SUFFIXES") or name.startswith("."):
            continue
        out.append({"name": name, "category": _classify(name)})
    return out


def _parse_package_json(text: str, warnings: list[str]) -> list[dict]:
    out: list[dict] = []
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        warnings.append("package.json is not valid JSON")
        return out
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if isinstance(scripts, dict):
        for name, cmd in scripts.items():
            out.append(
                {"name": name, "command": cmd if isinstance(cmd, str) else "", "category": _classify(name)}
            )
    return out


def _parse_pyproject(text: str, warnings: list[str]) -> dict:
    """Return discovered command-ish entries from pyproject.toml."""
    result = {"scripts": [], "configured_tools": [], "parser": "regex"}
    if _HAS_TOMLLIB:
        result["parser"] = "tomllib"
        try:
            data = tomllib.loads(text)
        except Exception:  # tomllib.TOMLDecodeError or others
            warnings.append("pyproject.toml parse failed; degrading to regex")
            return _parse_pyproject_regex(text)
        # [project.scripts] and [tool.poetry.scripts]
        proj_scripts = (data.get("project", {}) or {}).get("scripts", {})
        poetry_scripts = ((data.get("tool", {}) or {}).get("poetry", {}) or {}).get("scripts", {})
        for name in list(proj_scripts.keys()) + list(poetry_scripts.keys()):
            result["scripts"].append({"name": name, "category": _classify(name)})
        tools = (data.get("tool", {}) or {})
        for tool_name in tools.keys():
            if tool_name in ("pytest", "ruff", "black", "mypy", "isort", "flake8",
                             "coverage", "tox", "pyright", "poe"):
                result["configured_tools"].append(tool_name)
        return result
    return _parse_pyproject_regex(text)


def _parse_pyproject_regex(text: str) -> dict:
    """Minimal regex reader for pyproject.toml when tomllib is unavailable."""
    result = {"scripts": [], "configured_tools": [], "parser": "regex"}
    section = None
    script_section_re = re.compile(r"^\[(?:project\.scripts|tool\.poetry\.scripts)\]\s*$")
    tool_section_re = re.compile(r"^\[tool\.([A-Za-z0-9_\-]+)")
    key_re = re.compile(r"""^\s*["']?([A-Za-z0-9_.\-]+)["']?\s*=""")
    seen_tools: set[str] = set()
    known_tools = {"pytest", "ruff", "black", "mypy", "isort", "flake8",
                   "coverage", "tox", "pyright", "poe"}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            if script_section_re.match(stripped):
                section = "scripts"
            else:
                section = None
                tm = tool_section_re.match(stripped)
                if tm and tm.group(1) in known_tools and tm.group(1) not in seen_tools:
                    seen_tools.add(tm.group(1))
                    result["configured_tools"].append(tm.group(1))
            continue
        if section == "scripts":
            km = key_re.match(line)
            if km:
                name = km.group(1)
                result["scripts"].append({"name": name, "category": _classify(name)})
    return result


def _parse_justfile(text: str) -> list[dict]:
    """Extract just recipe names (``name:`` or ``name args:`` at col 0)."""
    out: list[dict] = []
    recipe_re = re.compile(r"^([a-zA-Z0-9_\-]+)(?:\s+[^:=]*)?:(?!=)")
    for line in text.splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        if line.lstrip().startswith(("set ", "export ")) or "=" in line.split(":")[0]:
            pass
        m = recipe_re.match(line)
        if m:
            name = m.group(1)
            out.append({"name": name, "category": _classify(name)})
    return out


def _parse_taskfile(text: str) -> list[dict]:
    """Extract Task task names under a top-level ``tasks:`` mapping (YAML, regex)."""
    out: list[dict] = []
    in_tasks = False
    task_re = re.compile(r"^  ([A-Za-z0-9_\-:]+):\s*$")
    for line in text.splitlines():
        if re.match(r"^tasks:\s*$", line):
            in_tasks = True
            continue
        if in_tasks:
            if line and not line.startswith(" ") and not line.startswith("\t"):
                in_tasks = False
                continue
            m = task_re.match(line)
            if m:
                name = m.group(1)
                out.append({"name": name, "category": _classify(name)})
    return out


def collect(root: str, warnings: list[str]) -> dict:
    sources: dict[str, dict] = {}

    # Makefile
    for mk in ("Makefile", "makefile", "GNUmakefile"):
        p = os.path.join(root, mk)
        if os.path.isfile(p):
            text = _read_text(p)
            if text is not None:
                sources["makefile"] = {"file": mk, "targets": _parse_makefile(text)}
            break

    # package.json
    p = os.path.join(root, "package.json")
    if os.path.isfile(p):
        text = _read_text(p)
        if text is not None:
            sources["package_json"] = {"file": "package.json", "scripts": _parse_package_json(text, warnings)}

    # pyproject.toml
    p = os.path.join(root, "pyproject.toml")
    if os.path.isfile(p):
        text = _read_text(p)
        if text is not None:
            sources["pyproject"] = {"file": "pyproject.toml", **_parse_pyproject(text, warnings)}

    # justfile
    for jf in ("justfile", "Justfile", ".justfile"):
        p = os.path.join(root, jf)
        if os.path.isfile(p):
            text = _read_text(p)
            if text is not None:
                sources["justfile"] = {"file": jf, "recipes": _parse_justfile(text)}
            break

    # Taskfile
    for tf in ("Taskfile.yml", "Taskfile.yaml", "taskfile.yml", "taskfile.yaml"):
        p = os.path.join(root, tf)
        if os.path.isfile(p):
            text = _read_text(p)
            if text is not None:
                sources["taskfile"] = {"file": tf, "tasks": _parse_taskfile(text)}
            break

    # Aggregate categories across all command-like entries.
    def _entries(src: dict) -> list[dict]:
        return src.get("targets") or src.get("scripts") or src.get("recipes") or src.get("tasks") or []

    has_test = False
    has_build = False
    has_lint = False
    configured_tools: list[str] = []
    for src in sources.values():
        for e in _entries(src):
            cat = e.get("category")
            if cat == "test":
                has_test = True
            elif cat == "build":
                has_build = True
            elif cat == "lint":
                has_lint = True
        configured_tools.extend(src.get("configured_tools", []))

    # A configured pytest/tox also implies a runnable test command exists.
    if any(t in ("pytest", "tox") for t in configured_tools):
        has_test = True
    if any(t in ("ruff", "black", "flake8", "isort", "mypy", "pyright") for t in configured_tools):
        has_lint = True

    return {
        "sources_found": sorted(sources.keys()),
        "details": sources,
        "configured_tools": sorted(set(configured_tools)),
        "has_test_command": has_test,
        "has_build_command": has_build,
        "has_lint_command": has_lint,
        "tomllib_available": _HAS_TOMLLIB,
        "note": "commands are extracted only, never executed",
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Extract (never run) test/build/lint commands.")
    parser.add_argument("target", nargs="?", default=".", help="target repo path (default: .)")
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

    if not _HAS_TOMLLIB:
        warnings.append("tomllib unavailable (Python < 3.11); pyproject.toml read via regex fallback")

    ok = True
    try:
        data = collect(root, warnings)
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
