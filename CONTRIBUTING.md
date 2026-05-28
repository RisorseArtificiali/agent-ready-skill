# Contributing to Agent Ready Skill

## Overview

Agent Ready Skill is a set of [agentskills.io](https://agentskills.io)-compliant skills that assess and improve any project's readiness for agentic coding, and scaffold new projects to be agent-ready. The scoring model is v2: 7 evidence-based dimensions with a portable-vs-target layering.

## How to Contribute

### Adding or Modifying Assessment Criteria

The scoring model is defined canonically in `skills/agent-ready/references/scoring.md` (the 7 dimensions, their weights, each dimension's sub-criteria with internal weights, layer tags, calculation formulas, and the v2 JSON schema). The companion `skills/agent-ready/references/remediation.md` holds the per-sub-criterion *why / consequence / how-to-fix / effort*, keyed by the same sub-criterion ids.

1. Fork the repository.
2. Edit `references/scoring.md` **first** (it is canonical).
3. Keep the weights balanced: **dimension weights must sum to 100**, and **each dimension's sub-weights must sum to 100**.
4. Update `references/remediation.md` for any added/changed sub-criterion (ids must match `scoring.md`).
5. Propagate the change to every rubric-duplication site (see the **Sync contract** below).
6. Submit a pull request explaining why the criterion was added/changed.

### Adding New Skills

1. Create a new directory under `skills/` with a `SKILL.md` file.
2. Follow the agentskills.io format (see existing skills as reference).
3. Update `README.md` (skills table + directory structure) with the new skill.
4. Add the new skill to the install symlink loop in **both** `README.md` and this file.
5. Submit a pull request.

### Skill Format

Each skill directory must contain at minimum a `SKILL.md` file following the [agentskills.io specification](https://agentskills.io). Keep the YAML frontmatter intact; `allowed-tools` constrains what the skill may run, so any new `Bash(...)` invocation must have a matching pattern.

### The Script Layer

Objective, deterministic signals are produced by helper scripts under `skills/agent-ready/scripts/`:

- **stdlib-only / zero dependencies** — they must run with a bare `python3`, no `pip install`.
- **read-only** — they never execute project code and never write to the target repo (the scanner must itself be safe to run).
- **graceful degradation** — the scan consumes their output when `python3` is available and falls back to Glob/Grep heuristics otherwise (`script_signals.available = false`).

Each script feeds specific sub-criteria (e.g. `repo_map.py` → `repo_map_availability`/`docs_comprehension_signals`, `secret_hygiene.py` → `secret_hygiene`, `instruction_audit.py` → `instruction_conciseness`/`cross_agent_bridge`); see the helper-script signals table in `references/scoring.md`. Keep new scripts in the same style (stdlib-only, read-only, JSON to stdout).

### The Two Canonical References

| File | Role |
|------|------|
| `skills/agent-ready/references/scoring.md` | Canonical scoring model: 7 dimensions, weights, sub-criteria + layer tags, formulas, v2 JSON schema |
| `skills/agent-ready/references/remediation.md` | Canonical per-sub-criterion `why` / `consequence` / `fixable_by` / `fix_ref` / `effort`, keyed by sub-criterion id |

Both are read by the skills: `agent-ready-report` renders every sub-criterion < 100 from `remediation.md`, and `agent-ready-fix` acts on items tagged `fixable_by: skill|partial`. Their sub-criterion ids **must** stay aligned with `scoring.md`.

## Sync contract

The scoring rubric is duplicated across several files for usability. When you change **any** scoring detail (a weight, a sub-criterion, a layer tag, the JSON schema, a remediation entry), update **all** of these together so they stay aligned:

- `skills/agent-ready/references/scoring.md` (canonical — edit first)
- `skills/agent-ready/references/remediation.md` (per-sub-criterion remediation; ids must match)
- `skills/agent-ready/SKILL.md` (router Quick Reference — the 7-dimension table, layers, agent mapping, levels)
- `skills/agent-ready-scan/SKILL.md` (discovery batches, scoring, and JSON schema)
- `README.md` (Scoring Dimensions table + "Why These Dimensions?")

Invariants to verify before opening a PR:
- Dimension weights **sum to 100**.
- Each dimension's sub-weights **sum to 100**.
- The 7-dimension table is **identical** (ids, weights, descriptions) across `scoring.md`, the router Quick Reference, and `README.md`.
- Every sub-criterion id in `scoring.md` has a matching entry in `remediation.md`.

## Installation for Development

```bash
git clone https://github.com/RisorseArtificiali/agent-ready-skill.git
cd agent-ready-skill
for skill in agent-ready agent-ready-scan agent-ready-fix agent-ready-report agent-ready-diff agent-ready-init; do
  ln -sf "$(pwd)/skills/$skill" "$HOME/.claude/skills/$skill"
done
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
