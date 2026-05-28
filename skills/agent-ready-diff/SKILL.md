---
name: agent-ready-diff
description: "Compare the current agentic readiness state against a previous v2 assessment. Shows per-dimension deltas (📈/📉/➡️), overall delta, and Portable/Target layer deltas, citing the files that drove each change. v2-schema only: if no comparable v2 baseline exists, runs a fresh scan instead of diffing. Use after making changes to measure progress."
argument-hint: "[path-to-previous-scores-json] [path]"
allowed-tools: Bash(git:*) Bash(find:*) Bash(wc:*) Bash(mkdir:*) Bash(mv:*) Bash(python3:*) Read Grep Glob Write
---

# Agent-Ready Diff — v2 Delta Comparison

Compare the current project against a previous **v2** agentic readiness assessment and report what changed.

**Canonical rubric**: `.claude/skills/agent-ready/references/scoring.md` — dimensions, sub-criterion ids, weights, layer tags, levels, score math, and the v2 JSON schema (`schema_version: 2`). Read it; do not re-derive numbers here.

`$ARGUMENTS` may contain a path to a previous scores JSON (defaults to `.agent-ready/agent-ready-scores.json`) and an optional target path passed through to the scan.

## Step 1: Load Previous Baseline (v2-only gate)

1. Read `.agent-ready/agent-ready-scores.json` (or the path in `$ARGUMENTS`) as the **previous** baseline.
2. **Gate — comparable v2 baseline required**:
   - If the file is **missing**, OR it parses but `schema_version != 2` (e.g. a v1 file or unversioned):
     - Report: **"No comparable v2 baseline found"** — explain that v2 changed the dimensions, so v1/missing scores cannot be diffed (per scoring.md migration / PRD §11).
     - Run a **fresh v2 scan** instead (invoke `/agent-ready-scan`, passing any target path) so the user gets a current baseline for next time.
     - **Stop here** — do not attempt a delta.
3. Otherwise, capture the previous `project`, `timestamp`, `overall_score`, `level`, `layers`, and per-dimension `weighted_score`/`raw_score` as the baseline.

## Step 2: Archive & Rescan

1. Archive the baseline so it is not overwritten: `mv .agent-ready/agent-ready-scores.json .agent-ready/agent-ready-scores.prev.json`.
2. Run a fresh full scan (invoke `/agent-ready-scan`, passing any target path) to write the **current** `.agent-ready/agent-ready-scores.json`.
3. Read the new file and confirm `schema_version == 2`.

## Step 3: Compute Deltas

For each of the 7 dimensions:
- `delta = current.weighted_score − previous.weighted_score`
- Direction: 📈 improved (`> 0`), 📉 regressed (`< 0`), ➡️ unchanged (`= 0`).

Also compute:
- **Overall delta** = `current.overall_score − previous.overall_score`.
- **Layer deltas** from `layers`: Portable (`portable.score`) and Target-specific (`target_specific.score`). Note if a layer's `max` changed (e.g. targets newly declared) — a layer max shift, not just the score, can move the overall, and the report must say so.

## Step 4: Display Results

```
## 📊 Agentic Readiness Delta (v2)

**Project**: <name>
**Previous**: <prev date> — <prev overall>/100 <emoji> <level>
**Current**:  <cur date>  — <cur overall>/100 <emoji> <level>
**Change**:   <+/-N> points <emoji>

### Dimension Changes
                                   Previous  Current  Delta
Agent Instructions & Context        12.6     16.2    +3.6 📈
Navigability & Code Intelligence    10.2     10.2     0.0 ➡️
Testing & Feedback                  14.0     14.0     0.0 ➡️
CI/CD, Automation & Governance       4.2     10.5    +6.3 📈
Agent Tooling & Capabilities         6.0      6.0     0.0 ➡️
Security & Sandbox                   2.4      7.2    +4.8 📈
Spec-Driven Workflow & Docs          0.0      5.0    +5.0 📈
──────────────────────────────────────────────────────────
Overall                             49.4     69.1   +19.7 📈

### Layer Changes
                          Previous  Current  Delta
🌐 Portable (max <P>)        41.4     58.1   +16.7 📈
🎯 Target-specific (max <T>)  8.0     11.0    +3.0 📈
(note any change in a layer's max, e.g. targets newly declared)

### 📈 Improvements
<For each dimension that rose, name the sub-criteria that moved up and the specific files added/changed that caused it (cite from the current evidence vs the previous evidence). Use git to corroborate when useful, e.g. `git diff --stat <prev-commit>..HEAD` or `git log --oneline`.>

### 📉 Regressions
<List any dimension/sub-criteria that fell and the likely cause (e.g. an instruction file that grew past the conciseness threshold, a lockfile newly gitignored). If none: "No regressions detected.">

### ➡️ Unchanged Areas
<One line per dimension that did not move; group the flat ones.>

### 🎯 Recommended Next Steps
<Top 3 actions by impact = dimension_weight × (100 − raw_score)/100, drawn from the current scan's top_improvements; for each give the dimension, +pts potential, effort, and whether it is a /agent-ready fix quick-win or manual work.>
```

## Step 5: Persist

- Current scores were already written by the scan (`.agent-ready/agent-ready-scores.json`).
- The previous baseline is retained at `.agent-ready/agent-ready-scores.prev.json` for history.
- The layered report at `.agent-ready/agent-ready-report.md` is regenerated by the scan step (and the badge, if scan emits it).

## Guidelines

- **v2-only by design** — never attempt to translate v1 scores; a missing or `schema_version != 2` baseline means scan-and-stop, not a forced comparison (PRD §11).
- **Be specific** — explain *what files* moved each number, not just the magnitude; cite evidence from both runs.
- **Track both directions** — surface regressions as carefully as improvements, including layer-max shifts.
- **Stay in sync** — this file references scoring.md by path; it does not duplicate the rubric.
