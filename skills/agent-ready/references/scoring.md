# Agentic Readiness Scoring Reference (v2)

Canonical scoring model for agent-ready v2. This file is the **single source of truth**. The router Quick Reference, `agent-ready-scan`, and the top-level `README.md` duplicate parts of it and MUST stay in sync. Per-sub-criterion remediation guidance lives in the companion canonical file [`remediation.md`](remediation.md), keyed by the same sub-criterion ids.

## 7 Dimensions (total weight = 100)

| # | Dimension (id) | Weight | What it evaluates |
|---|----------------|--------|-------------------|
| 1 | Agent Instructions & Context (`agent_instructions_context`) | 18 | AGENTS.md-first instructions, quality over bloat, scoped/hierarchical files, cross-agent bridge |
| 2 | Navigability & Code Intelligence (`navigability_code_intelligence`) | 18 | Repo map, semantic-nav amenability, dependency/structure clarity, README, contracts, file-size sanity |
| 3 | Testing & Feedback (`testing_feedback`) | 16 | Test suite, documented + fast commands, feedback quality, coverage |
| 4 | CI/CD, Automation & Governance (`cicd_automation_governance`) | 14 | CI runs tests+lint, lint/format automation, pre-commit, governance |
| 5 | Agent Tooling & Capabilities (`agent_tooling_capabilities`) | 12 | Standard Skills, bundled scripts, MCP declaration + nav/comprehension servers, commands |
| 6 | Security & Sandbox (`security_sandbox`) | 12 | Committed isolation, documented execution policy, permission policy, secret hygiene, supply-chain, injection hygiene |
| 7 | Spec-Driven Workflow & Docs (`spec_driven_workflow_docs`) | 10 | Specs/tasks, acceptance criteria, templates, ADR, docs/comprehension signals |

## Layers (Portable vs Target-specific)

Every sub-criterion is tagged `portable` or `target`. Two subscores are computed dynamically:

```
portable_subscore = Σ contributions of portable sub-criteria
target_subscore   = Σ contributions of target sub-criteria  (depends on --agents)
overall           = portable_subscore + target_subscore     # 0-100
```

Layer maxes are **not fixed** — they depend on which sub-criteria are tagged and whether targets are declared. When no target is declared, `target` sub-criteria are marked `na` and excluded from both the numerator and the dimension's effective denominator (a portable repo is not penalized for vendor files it does not need). The report states both layer maxes explicitly.

## The `--agents` target parameter & posture

```
/agent-ready scan [path-or-url] [--agents claude,codex,opencode,pi] [--mode brownfield|greenfield] [--format md|html]
```

- **`--agents` provided** → evaluate `target` sub-criteria for each named agent (mapping below). Supported minimum set: `claude`, `codex`, `opencode`, `pi`. Unknown names → warn and ignore.
- **No `--agents`** → detect posture: `AGENTS.md` present → portable (target layer "not declared"); a single dominant vendor dir (e.g. only `.claude/`) and no `AGENTS.md` → infer that agent (note recommending `--agents`); otherwise portable-only + a note.
- **`--mode`** defaults to `brownfield`. Posture sources are auto-detection + `--agents` only (no committed declaration file).

**Agent → artifacts mapping** (target-specific signals):

| Agent | Instruction file | Tooling dir | Permission/sandbox artifact | Skills path |
|---|---|---|---|---|
| `claude` | `CLAUDE.md` (or symlink → AGENTS.md) | `.claude/` | `.claude/settings.json` deny rules, `/sandbox`, `.devcontainer/` | `.claude/skills/` |
| `codex` | `AGENTS.md` | `config.toml` | `config.toml` `sandbox_mode`/`approval_policy` | `.agents/skills/` |
| `opencode` | `AGENTS.md`, `opencode.json`, `.opencode/agent/*.md` | `.opencode/` | `permission` in `opencode.json` | — |
| `pi` | `AGENTS.md` or `CLAUDE.md`, `.pi/SYSTEM.md` | `.pi/` | (no native sandbox) | Agent Skills standard |

## Levels

| Emoji | Range | Level |
|-------|-------|-------|
| 🔴 | 0-30 | Not Ready |
| 🟡 | 31-60 | Partially Ready |
| 🟢 | 61-80 | Ready |
| 🏆 | 81-100 | Optimized |

## Scoring rubric (per sub-criterion, 0-100)

- **0**: Completely absent
- **25**: Minimal/placeholder (exists but not useful)
- **50**: Adequate (functional but improvable)
- **75**: Good (well-structured and useful)
- **100**: Excellent (comprehensive, contextual, well-maintained)

## Sub-criteria detail

Each row: `id` — internal weight — layer — what to check. Sub-weights sum to 100 within each dimension.

### 1. Agent Instructions & Context (weight 18)
| id | Wt | Layer | Check |
|----|----|-------|-------|
| `primary_instruction_file` | 25 | portable (AGENTS.md) / target (vendor file) | `AGENTS.md` present; or declared target's file (CLAUDE.md, etc.) |
| `instruction_quality` | 25 | portable | Project-specific (paths, conventions); build/test/lint commands documented; not generic boilerplate |
| `instruction_conciseness` | 20 | portable | Penalize >~200-300 lines or boilerplate/duplication; reward focused content (`instruction_audit.py`) |
| `hierarchical_instructions` | 15 | portable | Per-package/subdir instruction files in large repos |
| `cross_agent_bridge` | 15 | target | Canonical file bridged to declared targets (symlink/import); no contradictory duplicated copies |

### 2. Navigability & Code Intelligence (weight 18)
| id | Wt | Layer | Check |
|----|----|-------|-------|
| `repo_map_availability` | 20 | portable | A committed index OR a cleanly generatable symbol map (`repo_map.py`); absence not penalized if generation is easy |
| `semantic_nav_amenability` | 18 | portable | Language servers exist / typed code / analyzable structure (precondition for LSP/Serena) |
| `dependency_structure_clarity` | 17 | portable | Derivable dependency graph, clear module boundaries, monorepo metadata (Nx) |
| `readme_overview` | 15 | portable | Root overview, setup, usage |
| `machine_readable_contracts` | 15 | portable | OpenAPI/Protobuf/GraphQL schemas at boundaries (when applicable) |
| `file_size_sanity` | 15 | portable | Few oversized files (>500 LOC) without reason (`file_metrics.py`) |

### 3. Testing & Feedback (weight 16)
| id | Wt | Layer | Check |
|----|----|-------|-------|
| `test_suite_present` | 20 | portable | Tests in tests/, __tests__/, *_test.* |
| `test_commands_documented` | 20 | portable | In AGENTS.md/Makefile/package.json/pyproject (`test_commands.py`) |
| `fast_feedback_loop` | 15 | portable | Documented quick subset; reasonable runtime |
| `feedback_quality` | 25 | portable | Descriptive assertion messages (not bare assert); type-checker config (mypy/pyright/tsconfig strict) |
| `coverage_reasonable` | 20 | portable | Coverage config/target or meaningful test breadth |

### 4. CI/CD, Automation & Governance (weight 14)
| id | Wt | Layer | Check |
|----|----|-------|-------|
| `ci_runs_tests_lint` | 30 | portable | CI executing tests and lint (`.github/workflows`, `.gitlab-ci.yml`, etc.) |
| `lint_format_automated` | 25 | portable | ruff/eslint/prettier/rustfmt configured and runnable |
| `pre_commit_hooks` | 20 | portable | `.pre-commit-config.yaml`, `.husky/`, `.lefthook.yml` |
| `governance` | 25 | portable | CODEOWNERS + Dependabot/Renovate |

### 5. Agent Tooling & Capabilities (weight 12)
| id | Wt | Layer | Check |
|----|----|-------|-------|
| `standard_skills` | 30 | portable | Valid `SKILL.md` (frontmatter, progressive disclosure, <500 lines) in any standard path |
| `bundled_helper_scripts` | 15 | portable | Skills ship `scripts/` for deterministic, context-efficient ops |
| `mcp_declaration` | 25 | portable | Project MCP config present (`.mcp.json` or vendor equivalent); portability noted honestly |
| `nav_comprehension_mcp_servers` | 20 | portable | Serena / Sourcegraph / Context7 (or equivalents) wired up — weighted higher for large repos |
| `custom_commands` | 10 | target | `.claude/commands/` etc. (legacy-positive; Skills preferred) |

Disambiguation: Dim 2 measures whether the codebase **supports** semantic nav (amenability); Dim 5 (`nav_comprehension_mcp_servers`) measures whether agent tooling is **actually wired up**.

### 6. Security & Sandbox (weight 12)
| id | Wt | Layer | Check |
|----|----|-------|-------|
| `committed_isolation_config` | 20 | portable | `.devcontainer/` with default-deny egress allowlist, or other committed sandbox config. Reward **true isolation** over denylists |
| `documented_execution_policy` | 15 | portable | Committed doc/section declaring the recommended sandbox + how to use it (LINCE, devcontainer, OS-sandbox, hosted) + safe-to-run command list. **Where non-detectable runtime sandboxes earn credit** |
| `agent_permission_policy` | 15 | target | Restrictive `.claude/settings.json` deny rules / Codex `sandbox_mode`+`approval_policy` / opencode permissions. Scored only when restrictive; flagged as attack surface (CVE-2025-59536) |
| `secret_hygiene` | 25 | portable | `.gitignore` covers secrets, `.env.example` present (no real values), secret scanning in CI + push protection (`secret_hygiene.py`) |
| `supply_chain_pinning` | 15 | portable | Lockfiles committed (not gitignored), Dependabot/Renovate, provenance where available (`lockfile_check.py`) |
| `injection_hygiene` | 10 | portable | Instructions only in trusted files; no executable/instruction-like content in agent-read docs |

> **Sandbox scoring principle**: runtime sandbox usage is largely invisible to a repo scan and self-reports are unverifiable. The score rewards only (a) committed isolation config and (b) a committed documented execution policy. There is **no interactive self-report and no `--sandbox` flag in the score**. Host-level sandboxes (e.g. [LINCE](https://lince.sh)) are credited via `documented_execution_policy`; generated docs cite LINCE as one option among devcontainer / OS-sandbox / hosted (vendor-neutral).

### 7. Spec-Driven Workflow & Docs (weight 10)
| id | Wt | Layer | Check |
|----|----|-------|-------|
| `spec_tasks_dir` | 25 | portable | `specs/`, `tasks/`, `prd/` with content; delta-scoped specs valued for brownfield |
| `acceptance_criteria` | 20 | portable | Defined criteria in specs/issues |
| `issue_pr_templates` | 15 | portable | `.github/ISSUE_TEMPLATE/`, PR template |
| `adr_decisions` | 15 | portable | `docs/adr/`, decision logs |
| `docs_comprehension_signals` | 25 | portable | Architecture doc; type-annotation & docstring coverage (`coverage_signals.py`); changelog |

**Weight check**: dimensions 18+18+16+14+12+12+10 = 100. Each dimension's sub-weights sum to 100.

## Helper-script signals (optional, stdlib-only)

Scripts under `scripts/` produce objective signals when `python3` is available; otherwise scan degrades to Glob/Grep heuristics and marks `script_signals.available=false`.

| Script | Feeds |
|--------|-------|
| `repo_map.py` | `repo_map_availability`, `docs_comprehension_signals` |
| `file_metrics.py` | `file_size_sanity` |
| `coverage_signals.py` | `feedback_quality`, `docs_comprehension_signals` |
| `secret_hygiene.py` | `secret_hygiene` |
| `lockfile_check.py` | `supply_chain_pinning` |
| `test_commands.py` | `test_commands_documented` |
| `instruction_audit.py` | `instruction_conciseness`, `cross_agent_bridge` |

Scripts are read-only and never execute project code (the scanner must itself be safe).

## Score calculation

```
raw_score_d      = Σ(sub_score_i × sub_weight_i) / Σ(sub_weight_i over evaluated, non-na sub-criteria)   # 0-100
weighted_score_d = raw_score_d × dimension_weight_d / 100                                                # 0-weight
overall          = Σ weighted_score_d                                                                    # 0-100
portable_subscore= Σ contributions of portable sub-criteria
target_subscore  = Σ contributions of target sub-criteria
```

## Impact prioritization

```
impact = dimension_weight × (100 − raw_score) / 100
```
Higher impact = more potential points gained from fixing that dimension.

## Output artifacts & location

All artifacts go to a vendor-neutral **`.agent-ready/`** directory in the project root (replaces v1 `claudedocs/`):
- `.agent-ready/agent-ready-report.md` — human report (single layered Markdown).
- `.agent-ready/agent-ready-scores.json` — machine-readable scores (schema below).
- `.agent-ready/agent-ready-scores.prev.json` — previous baseline (written by `diff`).
- `.agent-ready/badge.svg` — generated score badge (+ paste-ready README snippet).
- `.agent-ready/agent-ready-report.html` — only with `--format html` (self-contained, inline CSS).

Human report structure: (1) executive summary + ASCII bars; (2) layer analysis Portable vs Target; (3) per-dimension detail with explained-findings; (4) remediation roadmap.

## Explained findings

For **every sub-criterion scoring < 100**, the report explains: status & evidence, **why it matters**, **consequence** of not having it, **how to fix** (`fixable_by: skill|manual|partial` with command or manual steps), and **effort**. Source of these explanations: [`remediation.md`](remediation.md). Sub-criteria at 100 get a one-line affirmation.

## JSON schema v2 (`.agent-ready/agent-ready-scores.json`)

```json
{
  "schema_version": 2,
  "project": "string",
  "timestamp": "ISO-8601",
  "mode": "brownfield|greenfield",
  "declared_agents": ["claude", "codex"],
  "overall_score": 0,
  "level": "Not Ready|Partially Ready|Ready|Optimized",
  "layers": {
    "portable":        { "score": 0, "max": 0 },
    "target_specific": { "score": 0, "max": 0, "agents": ["claude", "codex"] }
  },
  "dimensions": {
    "agent_instructions_context":     { "weight": 18, "raw_score": 0, "weighted_score": 0, "subcriteria": {} },
    "navigability_code_intelligence": { "weight": 18, "raw_score": 0, "weighted_score": 0, "subcriteria": {} },
    "testing_feedback":               { "weight": 16, "raw_score": 0, "weighted_score": 0, "subcriteria": {} },
    "cicd_automation_governance":     { "weight": 14, "raw_score": 0, "weighted_score": 0, "subcriteria": {} },
    "agent_tooling_capabilities":     { "weight": 12, "raw_score": 0, "weighted_score": 0, "subcriteria": {} },
    "security_sandbox":               { "weight": 12, "raw_score": 0, "weighted_score": 0, "subcriteria": {} },
    "spec_driven_workflow_docs":      { "weight": 10, "raw_score": 0, "weighted_score": 0, "subcriteria": {} }
  },
  "script_signals": { "available": true },
  "top_improvements": [
    { "dimension": "string", "potential_gain": 0, "effort": "Low|Med|High", "description": "string" }
  ]
}
```

Each sub-criterion entry:
```json
{ "score": 0, "weight": 0, "layer": "portable|target", "evidence": "string",
  "na": false, "why": "string", "consequence": "string",
  "fixable_by": "skill|manual|partial", "fix_ref": "string", "effort": "Low|Med|High" }
```

## ASCII bar chart format

Use `█` (filled) and `░` (empty). Bar width = 16 chars. Fill ratio = `weighted_score / dimension_weight`.

Example: Agent Instructions & Context 12.6/18 = 70% → 11 filled + 5 empty:
```
Agent Instructions & Context  ███████████░░░░░  12.6/18
```

## Sync contract

When any scoring detail changes, update all of: this file (canonical), [`remediation.md`](remediation.md), the router Quick Reference (`../SKILL.md`), `agent-ready-scan/SKILL.md`, and the top-level `README.md`.
