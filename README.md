# agent-ready-skill

**Agentic Readiness Assessment** — a set of [Agent Skills](https://agentskills.io) that evaluate how well a codebase is prepared for agentic coding (AI-assisted autonomous development), and scaffold new projects to be agent-ready from day one.

Produces a quantitative score (0-100) across 7 evidence-based weighted dimensions, split into a **portable** layer (valid for any agent) and a **target-specific** layer (driven by `--agents`), plus explained, fixable guidance.

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| **agent-ready** | `/agent-ready` | Main entry point — routes to sub-commands, defaults to scan |
| **agent-ready-scan** | `/agent-ready-scan` | Full diagnostic analysis across the 7 dimensions (+ stdlib script signals) |
| **agent-ready-fix** | `/agent-ready-fix` | Auto-generate missing files (AGENTS.md, security baseline, CI, …) to improve score |
| **agent-ready-report** | `/agent-ready-report` | Layered report in `.agent-ready/` with explained findings + roadmap |
| **agent-ready-diff** | `/agent-ready-diff` | Delta comparison with previous assessment |
| **agent-ready-init** | `/agent-ready-init` | Greenfield scaffolding of a portable-first agent-ready baseline for a new/empty project |

## Scoring Dimensions

| # | Dimension (id) | Weight | What it evaluates |
|---|----------------|--------|-------------------|
| 1 | Agent Instructions & Context (`agent_instructions_context`) | 18 | AGENTS.md-first instructions, quality over bloat, scoped/hierarchical files, cross-agent bridge |
| 2 | Navigability & Code Intelligence (`navigability_code_intelligence`) | 18 | Repo map, semantic-nav amenability, dependency/structure clarity, README, contracts, file-size sanity |
| 3 | Testing & Feedback (`testing_feedback`) | 16 | Test suite, documented + fast commands, feedback quality, coverage |
| 4 | CI/CD, Automation & Governance (`cicd_automation_governance`) | 14 | CI runs tests+lint, lint/format automation, pre-commit, governance |
| 5 | Agent Tooling & Capabilities (`agent_tooling_capabilities`) | 12 | Standard Skills, bundled scripts, MCP declaration + nav/comprehension servers, commands |
| 6 | Security & Sandbox (`security_sandbox`) | 12 | Committed isolation, documented execution policy, permission policy, secret hygiene, supply-chain, injection hygiene |
| 7 | Spec-Driven Workflow & Docs (`spec_driven_workflow_docs`) | 10 | Specs/tasks, acceptance criteria, templates, ADR, docs/comprehension signals |

Dimension weights sum to 100; within each dimension the sub-criterion weights sum to 100. See [`skills/agent-ready/references/scoring.md`](skills/agent-ready/references/scoring.md) for the canonical model and the full sub-criteria.

**Two analysis layers** (computed per sub-criterion, not by fixed dimension range):
- **Portable** — signals valid for any AI coding agent (AGENTS.md, standard Skills, MCP declaration, tests, CI, lockfiles, devcontainer, …). Always scored.
- **Target-specific** — vendor signals (instruction bridges, permission policies, vendor tooling dirs, custom commands) scored only for the agents you pass via `--agents`. When no target is declared, target sub-criteria are marked `na` and excluded from the denominator — a portable repo is not penalized for vendor files it does not need. The report states both layer maxes explicitly.

**Score levels**: 🔴 0-30 Not Ready | 🟡 31-60 Partially Ready | 🟢 61-80 Ready | 🏆 81-100 Optimized

## Why These Dimensions?

The dimension set is grounded in the state-of-the-art on what actually makes agents effective, not in static-doc folklore:

- **`AGENTS.md` is the cross-vendor standard.** Instructions are weighted first (18) and scored portable-first: a single `AGENTS.md` with bridges to vendor files beats duplicated, drift-prone copies. The score *penalizes instruction bloat* rather than rewarding mere file presence.
- **Static-doc heuristics are weak predictors.** Directory-depth scoring and naming-consistency were retired; mere presence of `PROJECT_INDEX`/`ARCHITECTURE` is no longer rewarded. The real levers — repo maps, semantic-nav amenability, wired-up MCP servers (Serena/Sourcegraph), and **test feedback quality** — are weighted up (Navigability & Code Intelligence 18, Testing & Feedback 16).
- **Security is a real, growing threat surface.** A dedicated **Security & Sandbox** dimension (12) scores committed isolation config, a documented execution policy, secret hygiene, supply-chain pinning, and injection hygiene. It rewards only evidence in the repo — there is no unverifiable self-report and no `--sandbox` flag in the score; host-level sandboxes (e.g. [LINCE](https://lince.sh)) earn credit by being *documented* (one option among devcontainer / OS-sandbox / hosted).
- **Agent tooling is open and multi-vendor.** Standard Skills, bundled helper scripts, and MCP declarations are portable signals; only genuinely vendor-specific artifacts (permission policies, custom commands) are target-specific.

Per-sub-criterion *why it matters / consequence / how to fix / effort* lives in [`skills/agent-ready/references/remediation.md`](skills/agent-ready/references/remediation.md), and the report explains every sub-criterion scoring below 100.

## Usage

```
/agent-ready                                  # scan current project (default)
/agent-ready scan                             # same as above
/agent-ready scan https://github.com/o/r      # scan a GitHub repo
/agent-ready scan . --agents claude,codex     # score target-specific signals for Claude + Codex
/agent-ready scan . --mode greenfield         # relax remediation framing (default: brownfield)
/agent-ready fix                              # generate missing files (AGENTS.md, security baseline, …)
/agent-ready report                           # layered report in .agent-ready/
/agent-ready report --format html             # self-contained single-file HTML report
/agent-ready diff                             # compare with previous scan
/agent-ready init . --agents claude           # scaffold a new project to be agent-ready
```

Flags:
- `--agents <list>` — comma-separated target agents from `claude,codex,opencode,pi`. Omit for portable-only + posture auto-detection. Unknown names are warned and ignored.
- `--mode <brownfield|greenfield>` — defaults to `brownfield` (assessment + remediation of existing codebases). Greenfield is primarily served by `agent-ready-init`.
- `--format <md|html>` — report output, defaults to `md`.

## Output

All artifacts are written to a vendor-neutral **`.agent-ready/`** directory in the project root (replacing v1's `claudedocs/`):

- `.agent-ready/agent-ready-report.md` — human report (executive summary → portable/target layer analysis → per-dimension detail with explained findings → remediation roadmap).
- `.agent-ready/agent-ready-scores.json` — machine-readable scores (`schema_version: 2`); the contract shared by scan/fix/report/diff.
- `.agent-ready/agent-ready-scores.prev.json` — previous baseline (written by `diff`).
- `.agent-ready/badge.svg` — generated score badge, plus a paste-ready README snippet:

  ```markdown
  ![Agent Ready](.agent-ready/badge.svg)
  ```

- `.agent-ready/agent-ready-report.html` — only with `--format html` (self-contained, inline CSS, works offline).

Committing vs gitignoring `.agent-ready/` is your choice (the report and badge are commit-friendly for sharing).

## Installation

The skills follow the [Agent Skills](https://agentskills.io) open standard. They live in `skills/` and are symlinked into `~/.claude/skills/` for Claude Code discovery.

Clone and create symlinks to make the skills available:

```bash
git clone https://github.com/RisorseArtificiali/agent-ready-skill.git
cd agent-ready-skill
for skill in agent-ready agent-ready-scan agent-ready-fix agent-ready-report agent-ready-diff agent-ready-init; do
  ln -sf "$(pwd)/skills/$skill" "$HOME/.claude/skills/$skill"
done
```

## Directory Structure

```
agent-ready-skill/
├── README.md
├── CONTRIBUTING.md
├── CLAUDE.md
└── skills/
    ├── agent-ready/                 # Main router skill
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── scoring.md           # Canonical scoring rubric & v2 JSON schema
    │   │   └── remediation.md       # Canonical per-sub-criterion why/consequence/fix/effort
    │   └── scripts/                 # Optional stdlib-only, read-only signal scripts
    │       ├── repo_map.py
    │       ├── file_metrics.py
    │       ├── coverage_signals.py
    │       ├── secret_hygiene.py
    │       ├── lockfile_check.py
    │       ├── test_commands.py
    │       └── instruction_audit.py
    ├── agent-ready-scan/            # Full diagnostic scan (consumes scripts, with fallback)
    │   └── SKILL.md
    ├── agent-ready-fix/             # Auto-generate missing files
    │   └── SKILL.md
    ├── agent-ready-report/          # Layered report generation
    │   └── SKILL.md
    ├── agent-ready-diff/            # Delta comparison
    │   └── SKILL.md
    └── agent-ready-init/            # Greenfield scaffolding
        └── SKILL.md
```

The helper scripts are **stdlib-only and read-only** — they never execute project code, and the scan degrades gracefully to Glob/Grep heuristics when `python3` is unavailable.

## Compatibility

These skills run in [Claude Code](https://claude.ai/code) but follow the open Agent Skills format and score `AGENTS.md`-first. The portable layer is valid for any AI coding agent; the target-specific layer is scored only for the agents you declare via `--agents` (minimum set: `claude`, `codex`, `opencode`, `pi`).

## Output Example

```
## 🎯 Agentic Readiness Assessment

Project: my-project
Mode: brownfield | Agents: portable (none declared)
Overall Score: 54/100 🟡 Partially Ready
Layers: Portable 54/88 · Target n/a (no agents declared)

Score Breakdown

Agent Instructions & Context  ███████████░░░░░  12.6/18
Navigability & Code Intel.    ██████████░░░░░░  11.2/18
Testing & Feedback            ██████████████░░  14.0/16
CI/CD & Governance            ██████░░░░░░░░░░   5.6/14
Agent Tooling & Capabilities  ████░░░░░░░░░░░░   3.6/12
Security & Sandbox            ████░░░░░░░░░░░░   3.0/12
Spec-Driven Workflow & Docs   ░░░░░░░░░░░░░░░░   0.0/10
```
