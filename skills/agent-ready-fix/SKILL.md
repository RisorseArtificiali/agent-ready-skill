---
name: agent-ready-fix
description: "Remediate a project's agentic-readiness gaps by generating missing, project-specific files: AGENTS.md (primary, vendor-neutral) + target bridges, .env.example, .gitignore secret coverage, docs/agent-execution.md, CI + pre-commit baselines, Dependabot/Renovate, specs/ADR/issue templates, Makefile targets, and a generated repo index. Reads prior scores, prioritizes by impact, acts only on skill/partial-fixable sub-criteria, surfaces manual ones, and shows a before/after delta. Use after /agent-ready scan to close identified gaps."
argument-hint: "[dimension-id] [path] [--agents claude,codex,opencode,pi]"
disable-model-invocation: true
allowed-tools: Bash(git:*) Bash(find:*) Bash(wc:*) Bash(mkdir:*) Bash(mv:*) Bash(ln:*) Bash(python3:*) Read Grep Glob Write
---

# Agent-Ready Fix — Remediate Readiness Gaps (v2)

Generate the missing, **project-specific** files that raise a codebase's agentic-readiness score. Brownfield by default: read prior scores, prioritize the highest-impact gaps, act only on what our skills can actually generate, and surface the rest as manual steps.

**Canonical rubric**: `.claude/skills/agent-ready/references/scoring.md` — the single source of truth for the 7 dimensions, sub-criterion ids, weights, layer tags, score math, and the v2 JSON schema. Do not re-derive numbers here.

**Remediation registry**: `.claude/skills/agent-ready/references/remediation.md` — keyed by the same ids; supplies `fixable_by` (`skill`|`partial`|`manual`), `fix_ref`, `why`, `consequence`, `effort`. **This file decides what fix touches**: act on `skill` and `partial` only; `manual` items are listed with their steps, never auto-generated.

## Phase 0: ARGUMENTS

Parse `$ARGUMENTS` (order-independent):
- **dimension-id** — an optional dimension or sub-criterion id (e.g. `security_sandbox`, `secret_hygiene`). If present, restrict remediation to that scope; else fix all impactful gaps.
- **path** — first non-flag, non-id token: target dir (default cwd).
- **`--agents`** — target list (`claude,codex,opencode,pi`). If absent, detect posture as scan does: `AGENTS.md` present → portable; a single dominant vendor dir (e.g. only `.claude/`) → infer that agent. Targets drive bridge generation only.

## Phase 1: LOAD PRIOR SCORES

1. Read `.agent-ready/agent-ready-scores.json` (v2 path; replaces v1 `claudedocs/`).
2. If missing or `schema_version != 2`, invoke `/agent-ready-scan <path> [--agents ...]` first, then re-read.
3. Parse each dimension's `raw_score` and per-sub-criterion `{ score, fixable_by, na }`.

## Phase 2: PRIORITIZE

Rank gaps by **impact** = `dimension_weight × (100 − raw_score) / 100` (highest first). Within a dimension, prioritize sub-criteria with the lowest score and `fixable_by: skill` over `partial`. If a dimension-id filter was given, keep only that scope. Skip any sub-criterion at 100 or `na: true`.

## Phase 3: UNDERSTAND THE PROJECT

Before generating anything, read the project so output is contextual, never boilerplate:
- **Stack**: `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, etc.
- **Commands**: existing build/test/lint from Makefile, `package.json` scripts, `pyproject.toml` `[tool.*]`, `tox.ini`. Use `test_commands.py` when `python3` is available.
- **Tooling**: ruff/eslint/prettier/rustfmt/mypy/tsconfig config present.
- **Structure & conventions**: top-level dirs, naming style, workspace/monorepo boundaries.
- **Env vars**: grep for `os.environ`/`os.getenv`/`process.env`/`env::var`/`System.getenv` references.
- **Existing artifacts**: never plan to overwrite a file that exists.

## Phase 4: SELECT GENERATORS

For each prioritized gap, map its sub-criterion id to a generator below (`fixable_by: skill|partial` only). Each generator produces real, detected content. `manual` sub-criteria are collected for Phase 6 instead.

### Dim 1 — Agent Instructions & Context
- `primary_instruction_file` / `instruction_quality` (skill/partial): generate **`AGENTS.md`** as the PRIMARY instruction file — concise, **< 200 lines**, project-specific: overview, exact build/test/lint commands, structure pointers, naming/import conventions, a short safe-to-run/security note. No generic boilerplate; flag spots needing a human gotcha pass (partial).
- `instruction_conciseness` (partial): if an existing instruction file is bloated (per `instruction_audit.py`), propose moving detail into `references/` / scoped files; never delete content unasked.
- `hierarchical_instructions` (skill): for detected packages/workspaces, scaffold nested `AGENTS.md` stubs seeded with each area's commands and structure.
- `cross_agent_bridge` (skill): **target-aware bridges**. For a `claude` target: `ln -s AGENTS.md CLAUDE.md`. For `codex`/`opencode`/`pi`: do NOT duplicate — they read `AGENTS.md` natively; note this and report any contradictory pre-existing copies to remove.

### Dim 2 — Navigability & Code Intelligence
- `repo_map_availability` (partial): run `python3 .claude/skills/agent-ready/scripts/repo_map.py <path>` and write a generated repo index (top-N ranked files/symbols) to `.agent-ready/repo-index.md`; link it from `AGENTS.md`.
- `readme_overview` (partial): scaffold a README skeleton (purpose, setup, usage, structure) from the detected stack — only if README is absent or very sparse.

### Dim 3 — Testing & Feedback
- `test_commands_documented` (skill): document the detected test command(s) in `AGENTS.md` and add `Makefile` `test`/`lint` targets when no task runner exists.
- `fast_feedback_loop` (partial): document a quick-subset command convention.
- `feedback_quality` (partial): scaffold a type-checker config (`mypy.ini`/`[tool.mypy]` or `tsconfig` `strict`) for the stack.
- `coverage_reasonable` (partial): scaffold a coverage config + target (pytest-cov/coverage/nyc).

### Dim 4 — CI/CD, Automation & Governance
- `ci_runs_tests_lint` (skill): generate `.github/workflows/ci.yml` (or ecosystem equivalent) running the detected **test + lint** commands.
- `lint_format_automated` (skill): add a baseline linter/formatter config for the stack and wire it into Makefile/CI.
- `pre_commit_hooks` (skill): generate `.pre-commit-config.yaml` wired to the detected lint/format/secret tools.
- `governance` (skill): generate a `CODEOWNERS` skeleton and a **Dependabot (`.github/dependabot.yml`)** or **Renovate (`renovate.json`)** config for detected ecosystems.

### Dim 5 — Agent Tooling & Capabilities
- `standard_skills` / `bundled_helper_scripts` (partial): scaffold a conformant `SKILL.md` + `scripts/` skeleton in a standard path.
- `mcp_declaration` (skill): generate a baseline `.mcp.json` with an honest per-vendor portability note.

### Dim 6 — Security & Sandbox
- `documented_execution_policy` (skill): generate **`docs/agent-execution.md`** — vendor-neutral documented sandbox/execution policy listing **LINCE** among devcontainer / OS-sandbox / hosted options, plus a safe-to-run command list. This is where non-detectable runtime sandboxes earn credit.
- `secret_hygiene` (partial): add secret patterns to `.gitignore` (`.env`, `*.pem`, `id_rsa`, `*credentials*`, `*.key`) and generate a **redacted `.env.example`** from discovered env-var refs (no real values). Note: enabling host secret scanning + push protection is the manual half.
- `committed_isolation_config` (partial): scaffold a `.devcontainer/` note/template with a default-deny egress allowlist; hardening to true isolation is human work.
- `supply_chain_pinning` (partial): generate Dependabot/Renovate config and flag any gitignored lockfiles (`uv.lock`/`package-lock.json`/`Cargo.lock`/`go.sum`) to commit.

### Dim 7 — Spec-Driven Workflow & Docs
- `spec_tasks_dir` (skill): scaffold `specs/TEMPLATE.md` (delta-scoped task template with an acceptance-criteria section).
- `issue_pr_templates` (skill): generate `.github/ISSUE_TEMPLATE/feature.yml` + `bug.yml` and a PR template.
- `adr_decisions` (partial): scaffold `docs/adr/0001-record-architecture-decisions.md` (ADR template).
- `docs_comprehension_signals` (partial): scaffold an `ARCHITECTURE.md` skeleton and a `CHANGELOG.md`; report type/docstring coverage gaps from `coverage_signals.py`.

## Phase 5: CONFIRMATION GATE

List **every** file to be created or appended, then wait for explicit approval. Show what each does and mark files that already exist as skipped. Do not write anything before approval.

```
## Files to Generate (impact-ordered)

1. ✨ AGENTS.md — primary instructions: build/test/lint, structure, conventions (<200 lines)
2. 🔗 CLAUDE.md → AGENTS.md — symlink bridge (target: claude)
3. ✨ docs/agent-execution.md — documented sandbox policy (LINCE / devcontainer / OS-sandbox / hosted) + safe-to-run list
4. ✨ .env.example — redacted, from 4 discovered env-var refs
5. ➕ .gitignore — append secret patterns (.env, *.pem, id_rsa, *credentials*)
6. ✨ .github/workflows/ci.yml — runs `pytest` + `ruff check`
7. ✨ .pre-commit-config.yaml — ruff, ruff-format, detect-secrets
8. ✨ specs/TEMPLATE.md — delta-scoped spec template w/ acceptance criteria
9. ⏭️ tests/ — already exists, skipping

Manual (surfaced, NOT generated): semantic_nav_amenability, test_suite_present, nav_comprehension_mcp_servers, agent_permission_policy — see Phase 6.

Proceed? (y/n)
```

## Phase 6: SURFACE MANUAL ITEMS

For every prioritized gap whose `fixable_by` is `manual`, print the sub-criterion, its `why`/`consequence`, and the concrete `fix_ref` steps from `remediation.md` (e.g. add static types for `semantic_nav_amenability`; wire Serena/Sourcegraph for `nav_comprehension_mcp_servers`; author restrictive deny rules for `agent_permission_policy`; write characterization tests for `test_suite_present`). Never silently drop these.

## Phase 7: GENERATE

After approval, write the approved files. Append (never overwrite) where sensible (`.gitignore`, existing `AGENTS.md` sections, Makefile targets). Respect `.gitignore` — do not create files inside ignored dirs. Create `ln -s AGENTS.md CLAUDE.md` only when `claude` is a target and `CLAUDE.md` does not already exist.

## Phase 8: RE-SCAN & DELTA

Re-run the scan logic (`/agent-ready-scan <path> [--agents ...]`) to recompute scores, then show a before/after delta:

```
## 🔧 Agent-Ready Fix Results

### Files Generated
- ✅ AGENTS.md, CLAUDE.md (symlink), docs/agent-execution.md, .env.example, .pre-commit-config.yaml, specs/TEMPLATE.md
- ➕ .gitignore (secret patterns appended)

### Score Delta
                                Before  After  Change
Agent Instructions & Context      9.0   14.4   +5.4 📈
Security & Sandbox                3.6    8.4   +4.8 📈
CI/CD, Automation & Governance    4.2    9.8   +5.6 📈
Spec-Driven Workflow & Docs       2.5    6.0   +3.5 📈
──────────────────────────────────────────────────────
Overall                            48     67    +19 📈
Level                       🟡 Partial  🟢 Ready

### Still Manual
- semantic_nav_amenability (High) · test_suite_present (High) · nav_comprehension_mcp_servers (Med)
```

## Critical Rules

- **NEVER overwrite existing files** — create new, or append to existing where sensible.
- **`remediation.md` is authoritative** — act only on `fixable_by: skill|partial`; surface `manual` with steps.
- **AGENTS.md is primary** — vendor-neutral, < 200 lines; bridge to `claude` via symlink; codex/opencode/pi read it natively (no drift-prone copies).
- **Contextualize everything** — read the project first; real, detected content only, no boilerplate or placeholders.
- **Confirmation gate** — always list files and wait for approval before writing.
- **Respect `.gitignore`** and match existing naming/formatting/structure conventions.
- **Always show the before/after delta** by re-running the scan logic.
