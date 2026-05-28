# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> This repo could itself dogfood an `AGENTS.md` (the portable standard it scores for). One isn't committed yet — if you add it, bridge it (symlink `CLAUDE.md → AGENTS.md`) rather than duplicating content.

## What this repo is

A set of [Agent Skills](https://agentskills.io) (mostly Markdown, plus a small stdlib-only Python script layer) that assess how ready a *target* codebase is for agentic coding, and scaffold new projects to be agent-ready. It is a meta-tool: the skills here analyze (or bootstrap) *other* projects, producing a weighted 0-100 score across **7 evidence-based dimensions** with a **portable-vs-target** layering, plus explained remediation guidance.

There is **no build/test/lint pipeline** for the Markdown skills — the "source" is the `SKILL.md` files and the two canonical references. The Python scripts are stdlib-only and read-only. Validation means keeping the scoring rubric internally consistent (see the sync contract below).

## Architecture

Six skills under `skills/`, each a directory with a `SKILL.md` (agentskills.io frontmatter: `name`, `description`, `argument-hint`, `allowed-tools`):

- **agent-ready** — router. Parses `$ARGUMENTS` into a sub-command (defaults to `scan`), a target, and flags `--agents` / `--mode` (default `brownfield`) / `--format` (md|html). Handles GitHub-URL targets (clones to `/tmp/`), performs posture auto-detection when `--agents` is omitted, and routes `init` → `/agent-ready-init`. Holds the only `references/` and `scripts/` subdirs.
- **agent-ready-scan** — the engine. Discovery batches mapped to the 7 dimensions (Glob/Grep/find) + invocation of the `scripts/` signal layer (with graceful fallback) → score (portable + target subscores) → output → persist v2 JSON.
- **agent-ready-fix** — reads prior scores + `references/remediation.md`, generates missing files (AGENTS.md as the primary instruction file with vendor bridges, security baseline, CI, etc.) for sub-criteria tagged `fixable_by: skill|partial`. Confirmation gate; never overwrites.
- **agent-ready-report** — renders a single layered Markdown report (or self-contained HTML with `--format html`) with explained findings for every sub-criterion < 100; generates the README badge.
- **agent-ready-diff** — archives prior scores to `*.prev.json`, rescans, shows deltas; handles v1/missing baselines gracefully.
- **agent-ready-init** — greenfield scaffolding. Generates a portable-first baseline (AGENTS.md canonical + target bridges, secret-hygiene `.gitignore`, `.env.example`, `docs/agent-execution.md`, CI/pre-commit baseline) for a new/empty project; defers to `fix` on a non-empty repo.

### The two canonical references

`skills/agent-ready/references/` holds the single sources of truth:
- **scoring.md** — the 7 dimensions, weights, sub-criteria + layer tags, formulas, and the v2 JSON schema.
- **remediation.md** — per-sub-criterion `why` / `consequence` / `fixable_by` / `fix_ref` / `effort`, keyed by the same sub-criterion ids.

### The script layer

`skills/agent-ready/scripts/` holds **stdlib-only, read-only** Python helpers that produce objective signals: `repo_map.py`, `file_metrics.py`, `coverage_signals.py`, `secret_hygiene.py`, `lockfile_check.py`, `test_commands.py`, `instruction_audit.py`. They never execute project code. The scan consumes them when `python3` is present and degrades to Glob/Grep heuristics otherwise (`script_signals.available = false`). The script→sub-criterion mapping is in `scoring.md`.

### Data flow between skills

Via files in the *target* project's vendor-neutral **`.agent-ready/`** directory (replaces the v1 `claudedocs/` convention):
- `.agent-ready/agent-ready-scores.json` — machine-readable scores (`schema_version: 2`); the contract shared by scan/fix/report/diff.
- `.agent-ready/agent-ready-report.md` (or `.html`) — human-readable report.
- `.agent-ready/agent-ready-scores.prev.json` — previous baseline (written by `diff`).
- `.agent-ready/badge.svg` — generated score badge.

`fix`, `report`, and `diff` all depend on `scan` having produced `agent-ready-scores.json` first; they invoke `/agent-ready-scan` themselves if it's missing.

## The scoring rubric is the single source of truth — and it's duplicated

`skills/agent-ready/references/scoring.md` is canonical: it defines the **7 dimensions** and their weights (must total **100**), each dimension's sub-criteria with internal weights (each dimension's sub-weights must total **100**) and a `portable`/`target` layer tag, the 0-100 rubric, the calculation formulas, and the v2 JSON schema. `references/remediation.md` is the second canonical file, keyed by the same sub-criterion ids.

The same rubric facts are **restated** in several places. When you change any scoring detail (a weight, a sub-criterion, a layer tag, the JSON schema, a remediation entry), update **all** of these to match:

- `skills/agent-ready/references/scoring.md` (canonical — edit first)
- `skills/agent-ready/references/remediation.md` (per-sub-criterion remediation; ids must match)
- `skills/agent-ready/SKILL.md` (router Quick Reference: 7-dimension table, layers, agent mapping, levels)
- `skills/agent-ready-scan/SKILL.md` (discovery batches, scoring, JSON schema)
- `README.md` (Scoring Dimensions table + "Why These Dimensions?")

Score math (in `scoring.md`):
```
raw_score_d      = Σ(sub_score_i × sub_weight_i) / Σ(sub_weight_i over evaluated, non-na)   # 0-100
weighted_score_d = raw_score_d × dimension_weight_d / 100                                    # 0-weight
overall_score    = Σ weighted_score_d                                                        # 0-100
portable_subscore = Σ contributions of portable sub-criteria
target_subscore   = Σ contributions of target sub-criteria
```

**Layers** are computed **per sub-criterion** (not by fixed dimension range as in v1): each sub-criterion is tagged `portable` or `target`. The `target` layer is scored only for the agents in `--agents`; when no target is declared, `target` sub-criteria are `na` and excluded from the denominator. Layer maxes are dynamic and stated explicitly in the report.

## Conventions when editing skills

- **agentskills.io format**: keep the YAML frontmatter intact. `allowed-tools` constrains what the skill may run — if you add a Bash invocation (e.g. `python3` for the script layer), the matching `Bash(...)` pattern must be present.
- **Adding a sub-criterion**: rebalance internal weights so the dimension still sums to 100, add a `remediation.md` entry with a matching id, then propagate to all five sync-contract sites above.
- **Adding a new skill**: create `skills/<name>/SKILL.md`, add it to the README skills table + directory structure, and add it to the install symlink loop in both `README.md` and `CONTRIBUTING.md`.
- **Editing scripts**: keep them stdlib-only and read-only; emit JSON to stdout; never execute target project code.
- ASCII bars in output are **16 chars wide**, `█` filled / `░` empty, fill ratio = `weighted_score / dimension_weight`.
- `agent-ready-scan` emphasizes **parallel** Glob/Grep/Read calls in its discovery phase — preserve that when editing.
- Posture sources are auto-detection + the `--agents` flag only — there is no committed posture-declaration file.

## Installation (how the skills become active)

Skills live in `skills/` and are symlinked into `~/.claude/skills/` for Claude Code discovery:
```bash
for skill in agent-ready agent-ready-scan agent-ready-fix agent-ready-report agent-ready-diff agent-ready-init; do
  ln -sf "$(pwd)/skills/$skill" "$HOME/.claude/skills/$skill"
done
```
Note the runtime reference path: skills point to `.claude/skills/agent-ready/references/scoring.md` (and `remediation.md`, and `scripts/`) at the symlinked location, not the repo-relative path.
