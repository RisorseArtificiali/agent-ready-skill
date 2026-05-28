---
name: agent-ready
description: "Assess and improve a project's readiness for agentic coding. Scores 7 evidence-based dimensions (agent instructions, navigability & code intelligence, testing & feedback, CI/CD & governance, agent tooling, security & sandbox, spec-driven workflow) on a 0-100 scale with portable-vs-target layering and explained, fixable findings. Use when evaluating how well a codebase supports AI-assisted development, scaffolding a new agent-friendly project, or when the user mentions 'agent ready', 'agentic readiness', 'AGENTS.md', or 'AI-ready project'."
argument-hint: "[scan|fix|report|diff|init] [path-or-github-url] [--agents claude,codex,opencode,pi] [--mode brownfield|greenfield] [--format md|html]"
allowed-tools: Bash(git:*) Bash(find:*) Bash(python3:*) Bash(mkdir:*) Bash(mv:*) Read Grep Glob Write
---

# Agentic Readiness Assessment

You are an expert at evaluating how well a codebase is prepared for agentic coding (AI-assisted autonomous development). Analyze projects across 7 weighted, evidence-based dimensions and produce a quantitative score (0-100) split into a **portable** layer (valid for any agent) and a **target-specific** layer (driven by `--agents`), plus explained, fixable guidance.

## Routing

Parse `$ARGUMENTS` into a sub-command, a target, and flags.

1. **Extract sub-command** (first non-flag word): `scan` (default), `fix`, `report`, `diff`, or `init`. If the first word is not a recognized sub-command, treat it as the target and default to `scan`.
2. **Extract target** (next non-flag word): a GitHub URL, a local path, or empty (use cwd).
3. **Extract flags** (any position):
   - `--agents <list>` — comma-separated target agents from `claude,codex,opencode,pi`. Unknown names → warn and ignore. Omitted → posture auto-detection (see below).
   - `--mode <brownfield|greenfield>` — defaults to `brownfield`.
   - `--format <md|html>` — report output format, defaults to `md`. `html` produces a self-contained single-file report.

| Input | Sub-command | Target | Flags |
|-------|------------|--------|-------|
| _(empty)_ | scan | cwd | — |
| `scan` | scan | cwd | — |
| `scan /path/to/project` | scan | /path/to/project | — |
| `scan . --agents claude,codex` | scan | cwd | agents=claude,codex |
| `scan . --format html` | scan | cwd | format=html |
| `fix` | fix | cwd | — |
| `report` | report | cwd | — |
| `diff` | diff | cwd | — |
| `init` | init | cwd | — |
| `init . --agents claude` | init | cwd | agents=claude |
| `https://github.com/org/repo` | scan | clone URL to /tmp/ | — |
| `scan https://github.com/org/repo` | scan | clone URL to /tmp/ | — |

**Target resolution**:
- If target starts with `http` or `git@`: clone with `git clone --depth 1 <url> /tmp/agent-ready-$(date +%s)` and set the clone path as target.
- If target is a local path: use it directly.
- If empty: use the current working directory.

**Posture detection** (when `--agents` is omitted, applies to `scan`/`fix`/`report`):
- `AGENTS.md` present → treat as portable; report the target layer as "not declared".
- A single dominant vendor dir (e.g. only `.claude/`) and no `AGENTS.md` → infer that agent, and note that the user should confirm with `--agents`.
- Otherwise → portable-only scoring + a note prompting the user to declare targets.

## Sub-command Dispatch

Route to the appropriate skill, forwarding the resolved target and flags:
- **scan**: invoke `/agent-ready-scan <target> [--agents …] [--mode …]`
- **fix**: invoke `/agent-ready-fix <target> [--agents …]`
- **report**: invoke `/agent-ready-report <target> [--format md|html]`
- **diff**: invoke `/agent-ready-diff <target>`
- **init**: invoke `/agent-ready-init <target> [--agents …]` — greenfield scaffolding of a portable-first agent-ready baseline for a new/empty project.

## Scoring Reference

For full scoring details, sub-criteria definitions, layer math, and the JSON schema, see [references/scoring.md](references/scoring.md) (canonical). Per-sub-criterion remediation (why it matters / consequence / how to fix / effort) lives in [references/remediation.md](references/remediation.md).

### Quick Reference

**7 Dimensions** (total weight = 100) — verbatim from `references/scoring.md`:

| # | Dimension (id) | Weight | What it evaluates |
|---|----------------|--------|-------------------|
| 1 | Agent Instructions & Context (`agent_instructions_context`) | 18 | AGENTS.md-first instructions, quality over bloat, scoped/hierarchical files, cross-agent bridge |
| 2 | Navigability & Code Intelligence (`navigability_code_intelligence`) | 18 | Repo map, semantic-nav amenability, dependency/structure clarity, README, contracts, file-size sanity |
| 3 | Testing & Feedback (`testing_feedback`) | 16 | Test suite, documented + fast commands, feedback quality, coverage |
| 4 | CI/CD, Automation & Governance (`cicd_automation_governance`) | 14 | CI runs tests+lint, lint/format automation, pre-commit, governance |
| 5 | Agent Tooling & Capabilities (`agent_tooling_capabilities`) | 12 | Standard Skills, bundled scripts, MCP declaration + nav/comprehension servers, commands |
| 6 | Security & Sandbox (`security_sandbox`) | 12 | Committed isolation, documented execution policy, permission policy, secret hygiene, supply-chain, injection hygiene |
| 7 | Spec-Driven Workflow & Docs (`spec_driven_workflow_docs`) | 10 | Specs/tasks, acceptance criteria, templates, ADR, docs/comprehension signals |

**Layers** (computed per sub-criterion, not by fixed dimension range):
- **Portable** — signals valid for any agent (AGENTS.md, Skills, MCP declaration, tests, CI, lockfiles, devcontainer, …). Always scored.
- **Target-specific** — vendor signals scored only for the agents in `--agents` (instruction bridges, permission policies, vendor tooling dirs, custom commands). When no target is declared, `target` sub-criteria are marked `na` and excluded from the denominator (a portable repo is not penalized for vendor files it does not need). The report states both layer maxes explicitly.

**Agent → artifacts mapping** (target-specific signals):

| Agent | Instruction file | Tooling dir | Permission/sandbox artifact | Skills path |
|---|---|---|---|---|
| `claude` | `CLAUDE.md` (or symlink → AGENTS.md) | `.claude/` | `.claude/settings.json` deny rules, `/sandbox`, `.devcontainer/` | `.claude/skills/` |
| `codex` | `AGENTS.md` | `config.toml` | `config.toml` `sandbox_mode`/`approval_policy` | `.agents/skills/` |
| `opencode` | `AGENTS.md`, `opencode.json`, `.opencode/agent/*.md` | `.opencode/` | `permission` in `opencode.json` | — |
| `pi` | `AGENTS.md` or `CLAUDE.md`, `.pi/SYSTEM.md` | `.pi/` | (no native sandbox) | Agent Skills standard |

**Levels**: 🔴 0-30 Not Ready | 🟡 31-60 Partially Ready | 🟢 61-80 Ready | 🏆 81-100 Optimized

**Output**: all artifacts go to a vendor-neutral `.agent-ready/` directory in the project root (report `.md`/`.html`, `agent-ready-scores.json`, `badge.svg`).

## Cleanup

If a GitHub repo was cloned to /tmp/, clean up the temp directory after analysis is complete.
