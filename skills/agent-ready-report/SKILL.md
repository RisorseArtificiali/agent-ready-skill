---
name: agent-ready-report
description: "Render the v2 agentic readiness assessment as a single layered Markdown report in .agent-ready/. Includes an executive summary with ASCII bars, Portable-vs-Target layer analysis, per-dimension detail with explained findings (why / consequence / how-to-fix / effort) for every sub-criterion below 100, and a remediation roadmap. Generates a README badge and supports --format html. Use after a scan to produce a shareable readiness report."
argument-hint: "[refresh] [path] [--format md|html]"
allowed-tools: Bash(git:*) Bash(find:*) Bash(wc:*) Bash(mkdir:*) Bash(python3:*) Read Grep Glob Write
---

# Agent-Ready Report — Layered Readiness Document (v2)

Render the persisted v2 scores into a single, human-readable Markdown report. This skill **renders**, it does not re-score: scoring is owned by `agent-ready-scan`.

**Canonical rubric**: `.claude/skills/agent-ready/references/scoring.md` — dimensions, sub-criterion ids, weights, layer tags, levels, score math, the v2 JSON schema, and the ASCII-bar format. Read it; do not re-derive numbers here.

**Remediation registry**: `.claude/skills/agent-ready/references/remediation.md` — keyed by the same sub-criterion ids, supplies `why` / `consequence` / `fixable_by` / `fix_ref` / `effort` for every finding. The scan copies these fields into the JSON; if a finding is missing one, read it from here.

`$ARGUMENTS` may contain `refresh` (force a fresh scan), an optional target path, and `--format md|html` (default `md`).

## Step 1: Load or Generate Scores

1. Read `.agent-ready/agent-ready-scores.json` (the v2 scores written by the scan).
2. If the file is **missing**, or `$ARGUMENTS` contains `refresh`, or `schema_version != 2`: invoke `/agent-ready-scan` (passing through any target path) to (re)generate it, then read the result.
3. Validate `schema_version == 2`. Extract `project`, `overall_score`, `level`, `mode`, `declared_agents`, `layers`, `dimensions`, and `top_improvements`.

## Step 2: Write the Layered Markdown Report

Write a SINGLE file to `.agent-ready/agent-ready-report.md` (`mkdir -p .agent-ready` first). The report is layered top-to-bottom into four sections.

### Section 1 — Executive Summary

- Project name, generation date, **overall score + level emoji** (🔴/🟡/🟢/🏆 per scoring.md), `mode`, and `declared_agents` (or "not declared — portable posture").
- A **16-wide ASCII bar per dimension** using `█`/`░`, fill ratio = `weighted_score / dimension_weight`, labelled with `weighted/weight`. Format exactly as in scoring.md "ASCII bar chart format":

```
Agent Instructions & Context      ███████████░░░░░  12.6/18
Navigability & Code Intelligence  █████████░░░░░░░  10.2/18
Testing & Feedback                ██████████████░░  14.0/16
CI/CD, Automation & Governance    █████░░░░░░░░░░░   4.2/14
Agent Tooling & Capabilities      ████████░░░░░░░░   6.0/12
Security & Sandbox                ███░░░░░░░░░░░░░   2.4/12
Spec-Driven Workflow & Docs       ░░░░░░░░░░░░░░░░   0.0/10
```

- **Top gaps**: the top 3 `top_improvements` (dimension, `+potential_gain` pts, effort) as a one-line list.

### Section 2 — Layer Analysis (Portable vs Target)

Render the dynamic layer subscores from `layers`, citing **explicit maxes** (they are not fixed — see scoring.md "Layers"):

```
🌐 Portable layer:        <portable.score> / <portable.max>
🎯 Target-specific layer: <target_specific.score> / <target_specific.max>  (agents: <agents or "none declared">)
```

If no targets are declared, state that target sub-criteria are `n/a` and excluded from the achievable max (a portable repo is not penalized for vendor files it does not need). One short paragraph interpreting the split: is the gap in portable fundamentals or in target wiring?

### Section 3 — Per-Dimension Detail

For each of the 7 dimensions (in scoring.md order), emit:

1. A heading with raw + weighted score: `### N. <Dimension> (raw <raw_score>/100 · weighted <weighted_score>/<weight>)`.
2. A **sub-criteria table**: `| Sub-criterion | Score | Layer | Evidence |`. Mark `na` rows as `n/a`.
3. **Explained findings** — for **every sub-criterion scoring < 100** (and not `na`), ordered by sub-weight × (100 − score) descending, render this block from the JSON finding (fields sourced from remediation.md):

```markdown
#### ⚠️ <sub_criterion_id> — <score>/100  ·  layer: <portable|target>  ·  effort: <Low|Med|High>
- **Status & evidence**: <evidence>
- **Why it matters**: <why>
- **Consequence**: <consequence>
- **How to fix** — `fixable_by: <skill|partial|manual>`:
  - if `skill`: ✅ run `<fix_ref>` (our skills generate it).
  - if `partial`: 🔧 `<fix_ref>` scaffolds the structure; finish the project-specific content by hand (state the split from `fix_ref`).
  - if `manual`: 🛠️ not covered by our skills — follow these steps: <the concrete steps in `fix_ref`>.
```

   Make the `skill` vs `manual` distinction unmistakable: `skill`/`partial` items name the exact `/agent-ready fix <dimension>` (or `/agent-ready init`) command; `manual` items spell out the hands-on steps verbatim from `fix_ref`.
4. Sub-criteria scoring **100** get a single affirmation line: `- ✅ <id>: <evidence>` (no remediation block).

### Section 4 — Remediation Roadmap

Aggregate every finding < 100 across all dimensions into two ordered lists, sorted by impact (`dimension_weight × (100 − raw_score)/100`, then sub-weight):

- **Quick wins (`fixable_by: skill`)** — a checklist routed to `/agent-ready fix <dimension>` (and `/agent-ready init` for greenfield scaffolding), each with its `+pts` potential and effort. These are what one command can fix.
- **Manual / partial work** — `manual` and `partial` items listed separately with their concrete steps and effort, so they are surfaced, never silently dropped.

Close with the brownfield-first ordering from scoring.md / PRD §10: (1) repo map + dependency signals, (2) delta-scoped specs, (3) characterization tests on active modules, (4) split oversized files + add types incrementally, (5) formalize boundary contracts. End with the methodology footer (7 dimensions, level bands) and `*Generated by /agent-ready report on <date>*`.

## Step 3: README Badge

1. `mkdir -p .agent-ready`, then write `.agent-ready/badge.svg`: a self-contained SVG showing `agent-ready: <score>/100`, colored by level (🔴 `#e05d44` · 🟡 `#dfb317` · 🟢 `#97ca00` · 🏆 `#4c1`). Use a two-segment shields-style layout (gray label + colored value) with inline `<rect>`/`<text>`; no external assets.
2. Print a **paste-ready snippet** in the conversation: `![Agent Ready](.agent-ready/badge.svg)`. Offer a shields.io static-URL alternative (`https://img.shields.io/badge/agent--ready-<score>%2F100-<color>`) for users who prefer external rendering.

## Step 4: HTML Format (`--format html`)

When `$ARGUMENTS` contains `--format html`, additionally write `.agent-ready/agent-ready-report.html`: a **self-contained single HTML file** with **inline CSS** (no external assets, works offline) carrying the same four-section content — real colored bars (`<div>` widths from the fill ratio), the layer split, collapsible (`<details>`) per-criterion explained findings, and the roadmap. Markdown remains the default and is always written.

## Step 5: Conversation Summary

After writing, display concisely in the conversation:
- **Overall score + level** (with emoji).
- **Report path**: `.agent-ready/agent-ready-report.md` (and `.html` if generated).
- **Top 3 improvements** (from `top_improvements`): dimension, `+pts`, effort, one-line action.

## Guidelines

- **Render, don't re-derive** — all numbers come from the JSON; never recompute scores in this skill.
- **Cite evidence** — every finding shows the exact `evidence` string (files found or missing).
- **Distinguish fix paths** — `skill`/`partial` (our commands) vs `manual` (hands-on steps) must be visually unambiguous.
- **Honest & specific** — no marketing language; explain the agent-effectiveness rationale grounded in the registry.
- **Stay in sync** — this file references scoring.md / remediation.md by path; it does not duplicate the rubric.
