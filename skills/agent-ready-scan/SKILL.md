---
name: agent-ready-scan
description: "Full diagnostic scan of a project's agentic coding readiness. Evaluates 7 evidence-weighted dimensions (agent instructions, navigability & code intelligence, testing & feedback, CI/CD & governance, agent tooling, security & sandbox, spec-driven workflow & docs) with portable-vs-target layering, an optional --agents target list, and helper-script signals, producing a 0-100 score plus explained findings. Use when you need to evaluate how AI-ready a codebase is."
argument-hint: "[path-or-url] [--agents claude,codex,opencode,pi] [--mode brownfield|greenfield] [--format md|html]"
allowed-tools: Bash(python3:*) Bash(git:*) Bash(find:*) Bash(wc:*) Bash(mkdir:*) Read Grep Glob Write
---

# Agent-Ready Scan — Full Diagnostic Analysis (v2)

Perform a comprehensive **7-dimension** agentic readiness scan on the target project. The model is evidence-weighted, vendor-neutral (AGENTS.md-first), and split into a **Portable** layer (counts for any agent) and a **Target-specific** layer (depends on declared agents).

**Canonical rubric**: `.claude/skills/agent-ready/references/scoring.md` is the single source of truth for dimensions, sub-criteria ids, weights, layer tags, the 0/25/50/75/100 rubric, score math, the v2 JSON schema, and the ASCII-bar format. Read it; do not re-derive numbers from this file.

**Remediation registry**: `.claude/skills/agent-ready/references/remediation.md` is keyed by the same sub-criterion ids and supplies `why` / `consequence` / `fixable_by` / `fix_ref` / `effort` for every finding. Read it once during the SCORE phase.

## Phase 0: ARGUMENTS & POSTURE

Parse `$ARGUMENTS` (order-independent flags):

1. **Target** — the first non-flag token: a local path, a GitHub/git URL, or empty (use cwd).
   - URL (`http…` or `git@…`): `git clone --depth 1 <url> /tmp/agent-ready-$(date +%s)`, use that dir as target, and remember to clean it up in PERSIST.
   - Local path: use directly. Empty: use cwd.
2. **`--agents`** — comma list from `{claude, codex, opencode, pi}`. Unknown names → warn and ignore. These activate the **target** sub-criteria and select the artifact mapping (see scoring.md "Agent → artifacts mapping").
3. **`--mode`** — `brownfield` (default) | `greenfield`. Greenfield only relaxes remediation framing; scoring is unchanged.
4. **`--format`** — `md` (default) | `html`. `html` additionally emits a self-contained HTML report in PERSIST.

**Posture detection** (only when `--agents` is absent), per scoring.md:
- `AGENTS.md` present → **portable** posture; target layer reported as "not declared" (target sub-criteria → `na`, excluded from denominators).
- No `AGENTS.md` but exactly one dominant vendor dir (e.g. only `.claude/`) → **infer** that single agent as the target, and note that the user should confirm with `--agents`.
- Otherwise → portable-only, with a note prompting the user to declare targets.

Record `declared_agents` (explicit or inferred; empty list when portable-only) and `mode` for the JSON output.

## Phase 1: DISCOVER

Resolve the target, then run these **seven discovery batches in parallel** (one batch per dimension) using simultaneous Glob/Grep/find/Read calls. Exclude `.git/`, `node_modules/`, `.venv/`, `venv/`, `dist/`, `build/`, `__pycache__/` from walks. Reward partial effort; cite exactly what is found or missing.

### Batch 1 — Agent Instructions & Context (`agent_instructions_context`, weight 18)
- Glob the **primary instruction file**: `AGENTS.md` (portable canonical). Also locate declared/vendor files: `CLAUDE.md`, `.opencode/agent/*.md`, `opencode.json`, `.pi/SYSTEM.md`, and legacy `**/.cursorrules`, `**/.github/copilot-instructions.md`.
- Read `AGENTS.md` (and the dominant vendor file) and assess **quality**: project-specific paths/conventions, documented build/test/lint commands, not generic boilerplate.
- Glob for **hierarchical/scoped** instruction files in subpackages (`*/AGENTS.md`, `*/CLAUDE.md` below root) — relevant for large/monorepos.
- Detect **cross-agent bridge** (target): is the canonical file bridged to declared targets via symlink/import (e.g. `CLAUDE.md` → `AGENTS.md`), without contradictory duplicated copies? (Use `find -L … -type l` / read file heads to spot symlinks or `@import` lines.)

### Batch 2 — Navigability & Code Intelligence (`navigability_code_intelligence`, weight 18)
- Glob a **committed repo map / index**: `PROJECT_INDEX.md`, `repo-map*`, `INDEX.md`, `**/ARCHITECTURE.md`. Absence is not penalized if a map is cleanly generatable (the `repo_map.py` script decides this in SCRIPT phase).
- Assess **semantic-nav amenability**: typed languages / language-server configs (`tsconfig.json`, `pyrightconfig.json`, `mypy.ini`, `.editorconfig`, `*.gemspec`, `go.mod`) and analyzable structure.
- Assess **dependency & structure clarity**: manifests (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`) and monorepo metadata (`nx.json`, `pnpm-workspace.yaml`, `lerna.json`, `turbo.json`) → derivable dependency graph / clear module boundaries.
- Glob **README** at root; read to confirm overview + setup + usage.
- Glob **machine-readable contracts**: `**/openapi*.{yml,yaml,json}`, `**/swagger*`, `**/*.proto`, `**/*.graphql`, `**/schema.graphql`.
- **File-size sanity** is computed by `file_metrics.py` (SCRIPT phase); fallback heuristic: `find <target> \( -name '*.py' -o -name '*.ts' -o -name '*.js' -o -name '*.go' -o -name '*.rs' \) -not -path '*/node_modules/*' | xargs wc -l 2>/dev/null | awk '$1 > 500'`.

### Batch 3 — Testing & Feedback (`testing_feedback`, weight 16)
- Glob the **test suite**: `**/test*/**/*.{py,js,ts,go,rs}`, `**/*_test.{py,go}`, `**/*test*.{py,js,ts}`, `**/*spec*.{js,ts}`, `**/__tests__/**`.
- **Test commands documented** is computed by `test_commands.py`; fallback: Grep `AGENTS.md`/`CLAUDE.md`/`Makefile`/`package.json`/`pyproject.toml`/`justfile`/`Taskfile*` for `test`/`pytest`/`jest`/`vitest`/`cargo test`/`go test`.
- **Fast feedback loop**: look for a documented quick subset (markers, `-k`, watch mode, `make test-fast`) and runtime hints.
- **Feedback quality**: sample 3-5 test files for descriptive assertion messages (penalize bare `assert x` without message); detect a type-checker config (`mypy.ini`/`setup.cfg [mypy]`, `pyrightconfig.json`, `tsconfig.json` with `"strict": true`). Also fed by `coverage_signals.py`.
- **Coverage**: Glob `**/.coveragerc`, `pytest.ini`/`pyproject.toml` coverage sections, `**/jest.config*`/`**/vitest.config*` coverage thresholds, `**/codecov.yml`; or meaningful test breadth.

### Batch 4 — CI/CD, Automation & Governance (`cicd_automation_governance`, weight 14)
- Glob CI: `**/.github/workflows/*.{yml,yaml}`, `**/.gitlab-ci.yml`, `**/Jenkinsfile`, `**/.circleci/**`, `**/azure-pipelines.yml`. Grep workflow contents to confirm they **run tests and lint**.
- **Lint/format automated**: Glob/Grep `ruff`/`eslint`/`prettier`/`black`/`rustfmt`/`gofmt` configs (`ruff.toml`, `.eslintrc*`, `.prettierrc*`, `pyproject.toml` `[tool.ruff]`, `rustfmt.toml`).
- **Pre-commit hooks**: `**/.pre-commit-config.yaml`, `**/.husky/**`, `**/.lefthook.yml`.
- **Governance**: `**/CODEOWNERS` (root/.github/docs) + `**/.github/dependabot.yml`, `**/renovate.json`/`renovate.json5`/`.renovaterc*`.

### Batch 5 — Agent Tooling & Capabilities (`agent_tooling_capabilities`, weight 12)
- **Standard Skills**: Glob `**/.claude/skills/**/SKILL.md`, `**/.agents/skills/**/SKILL.md`, `**/skills/**/SKILL.md`. Read 1-2 `SKILL.md` files to validate frontmatter, progressive disclosure, and <500 lines.
- **Bundled helper scripts**: do the skills ship a `scripts/` dir for deterministic, context-efficient ops?
- **MCP declaration**: Glob `**/.mcp.json`, `**/.cursor/mcp.json`, `**/opencode.json` (mcp block), `**/.vscode/mcp.json`, and `.claude/settings*.json` for `mcpServers`. Note portability honestly.
- **Nav/comprehension MCP servers**: Grep MCP configs for `serena`, `sourcegraph`, `context7` (or equivalents) actually wired up — weight higher for large repos. (Dim 2 = codebase *supports* semantic nav; this = tooling is *wired up*.)
- **Custom commands** (target): `**/.claude/commands/**`, `**/.opencode/command/**` (legacy-positive; Skills preferred).

### Batch 6 — Security & Sandbox (`security_sandbox`, weight 12)
- **Committed isolation config**: `**/.devcontainer/**` (Dockerfile / `devcontainer.json` / compose) — inspect for default-deny **egress allowlist**; reward true isolation over denylists. Also other committed sandbox configs.
- **Documented execution policy**: Glob `**/docs/agent-execution.md`, `**/SECURITY.md`; Grep `AGENTS.md`/`CLAUDE.md` for a sandbox/execution-policy section naming a recommended sandbox (devcontainer / OS-sandbox / hosted, e.g. LINCE) + a safe-to-run command list. **This is where non-detectable runtime sandboxes earn credit — by being documented.**
- **Agent permission policy** (target): restrictive `.claude/settings.json` deny rules; Codex `config.toml` `sandbox_mode`/`approval_policy`; opencode `permission` block. Score only when restrictive; flag permissive configs as attack surface (CVE-2025-59536).
- **Secret hygiene**: computed by `secret_hygiene.py`; fallback: read `.gitignore` for `.env`/`*.pem`/`id_rsa`/`*credentials*` coverage, Glob `**/.env.example`/`**/.env.template` (must hold no real values), Grep CI for secret-scanning + push protection.
- **Supply-chain pinning**: computed by `lockfile_check.py`; fallback: Glob `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`, `**/uv.lock`, `**/poetry.lock`, `**/Pipfile.lock`, `**/Cargo.lock`, `**/go.sum`, `**/Gemfile.lock`, `**/composer.lock` and confirm they are **not** gitignored; plus Dependabot/Renovate.
- **Injection hygiene**: confirm instructions live only in trusted files; Grep agent-read docs (`AGENTS.md`, README, `docs/**`) for executable/instruction-like injected content (e.g. hidden "ignore previous instructions", fenced shell told to auto-run).

### Batch 7 — Spec-Driven Workflow & Docs (`spec_driven_workflow_docs`, weight 10)
- **Spec/tasks dir**: `**/specs/**`, `**/spec/**`, `**/tasks/**`, `**/prd/**`, `**/PRD/**` with real content (delta-scoped specs are valued for brownfield).
- **Acceptance criteria**: Grep specs/issues for acceptance-criteria / "Definition of Done" sections.
- **Issue/PR templates**: `**/.github/ISSUE_TEMPLATE/**`, `**/.github/pull_request_template*`, `**/.gitlab/**`.
- **ADR / decision records**: `**/docs/adr/**`, `**/adr/**`, `**/ADR/**`, decision logs.
- **Docs & comprehension signals**: `**/docs/**`, `**/ARCHITECTURE.md`, `**/CHANGELOG*`/`**/HISTORY*`; type-annotation & docstring coverage via `coverage_signals.py`/`repo_map.py`.

## Phase 2: SCRIPT (helper-script signals)

Probe availability once: `python3 --version`.

- **If available** — run each PRD-2 script and parse its JSON (`{ "script", "version", "ok", "data", "warnings" }`). Each script is read-only and never executes project code:
  ```
  python3 .claude/skills/agent-ready/scripts/repo_map.py <target>
  python3 .claude/skills/agent-ready/scripts/file_metrics.py <target>
  python3 .claude/skills/agent-ready/scripts/coverage_signals.py <target>
  python3 .claude/skills/agent-ready/scripts/secret_hygiene.py <target>
  python3 .claude/skills/agent-ready/scripts/lockfile_check.py <target>
  python3 .claude/skills/agent-ready/scripts/test_commands.py <target>
  python3 .claude/skills/agent-ready/scripts/instruction_audit.py <target>
  ```
  Fold each `data` into the sub-criteria it feeds (scoring.md "Helper-script signals" table):
  | Script | Feeds sub-criteria |
  |--------|--------------------|
  | `repo_map.py` | `repo_map_availability`, `docs_comprehension_signals` |
  | `file_metrics.py` | `file_size_sanity` |
  | `coverage_signals.py` | `feedback_quality`, `docs_comprehension_signals` |
  | `secret_hygiene.py` | `secret_hygiene` |
  | `lockfile_check.py` | `supply_chain_pinning` |
  | `test_commands.py` | `test_commands_documented` |
  | `instruction_audit.py` | `instruction_conciseness`, `cross_agent_bridge` |
  Set `script_signals.available = true`. **Only compact JSON enters context** — summarize large maps (top-N ranked files/symbols, counts), do not paste full output. If a script returns `ok:false`, fall back to the Batch-N heuristic for its sub-criteria and record its `warnings`.
- **If `python3` is unavailable** — skip all scripts, set `script_signals.available = false`, and score the affected sub-criteria from the DISCOVER-phase Glob/Grep heuristics (reduced precision, never a hard failure). Note this degradation in the report.

## Phase 3: SCORE

For each dimension, score every **evaluated, non-`na`** sub-criterion on the canonical 0/25/50/75/100 rubric (scoring.md "Scoring rubric"), folding in DISCOVER evidence and SCRIPT signals. Then compute, per scoring.md "Score calculation":

```
raw_score_d       = Σ(sub_score_i × sub_weight_i) / Σ(sub_weight_i over evaluated, non-na sub-criteria)   # 0-100
weighted_score_d  = raw_score_d × dimension_weight_d / 100                                                 # 0-weight
overall           = Σ weighted_score_d                                                                     # 0-100
portable_subscore = Σ contributions of portable sub-criteria
target_subscore   = Σ contributions of target sub-criteria
```

**Layering rules**:
- Tag each sub-criterion `portable` or `target` exactly as in scoring.md.
- When **no target is declared**, mark every `target` sub-criterion `na: true` and **exclude it from both numerator and the dimension's effective denominator** — a portable repo is not penalized for vendor files it does not need.
- Report both layer maxes explicitly (they are dynamic, not the v1 fixed 76/24).

Map `overall` to a level: 🔴 0-30 Not Ready · 🟡 31-60 Partially Ready · 🟢 61-80 Ready · 🏆 81-100 Optimized.

**Explained findings** — for **every sub-criterion scoring < 100** (skip `na`), pull `why`, `consequence`, `fixable_by` (`skill`|`manual`|`partial`), `fix_ref`, and `effort` from `references/remediation.md` (keyed by sub-criterion id) and attach them to the finding alongside the concrete `evidence` you observed. Sub-criteria at 100 get a one-line affirmation.

**Impact prioritization**: `impact = dimension_weight × (100 − raw_score) / 100`. Rank dimensions/findings by impact for the roadmap and top-N.

## Phase 4: OUTPUT (terminal summary)

Concise conversation output — ASCII bars + top-N gaps with a one-line *why* / *fix* and a pointer to the persisted report:

```
## 🎯 Agentic Readiness Assessment

**Project**: <name>
**Mode**: <brownfield|greenfield>   **Agents**: <declared or "portable (none declared)">
**Overall Score**: <X>/100 <emoji> <level>

### Score Breakdown
Agent Instructions & Context      <bar>  <weighted>/18
Navigability & Code Intelligence  <bar>  <weighted>/18
Testing & Feedback                <bar>  <weighted>/16
CI/CD, Automation & Governance    <bar>  <weighted>/14
Agent Tooling & Capabilities      <bar>  <weighted>/12
Security & Sandbox                <bar>  <weighted>/12
Spec-Driven Workflow & Docs       <bar>  <weighted>/10

### Layers
Portable:        <X>/<max>
Target-specific: <X>/<max>  (<agents> | not declared)

### Top <N> Gaps (by impact)
1. <emoji> <dimension › sub-criterion> (+<N> pts) — why: <one line>. fix: <one line, note skill|manual>.
2. ...

Script signals: <available | unavailable (heuristic fallback)>
Full report: .agent-ready/agent-ready-report.md
Run `/agent-ready fix` to auto-generate the skill-fixable items.
```

**Bar format** (scoring.md "ASCII bar chart format"): 16 chars wide, `█` filled + `░` empty, fill ratio = `weighted_score / dimension_weight`. Example: 12.6/18 = 70% → `███████████░░░░░`.

## Phase 5: PERSIST

`mkdir -p .agent-ready` in the **project root** (vendor-neutral; replaces v1 `claudedocs/`), then write:

### `.agent-ready/agent-ready-scores.json`
The full **v2 schema** from scoring.md ("JSON schema v2"): `schema_version: 2`, `project`, `timestamp` (ISO-8601), `mode`, `declared_agents`, `overall_score`, `level`, `layers.{portable, target_specific}` with `score`/`max` (+ `agents`), the seven `dimensions` (each `weight`/`raw_score`/`weighted_score`/`subcriteria`), `script_signals` (with `available` and summarized raw outputs), and `top_improvements`. Each sub-criterion entry carries `score`, `weight`, `layer`, `evidence`, `na`, `why`, `consequence`, `fixable_by`, `fix_ref`, `effort`.

### `.agent-ready/agent-ready-report.md`
A **single layered Markdown** report, top-to-bottom:
1. **Executive summary** — project, overall score + level, the ASCII-bar breakdown, declared agents + mode, top gaps.
2. **Layer analysis** — Portable vs Target subscores with explicit maxes; note any `na` target sub-criteria.
3. **Per-dimension detail** — score table per dimension followed by an **explained-findings block** for every sub-criterion < 100 (status & evidence, why it matters, consequence, how to fix with `fixable_by` + command/steps, effort), ordered by impact; one-line affirmations for 100s.
4. **Remediation roadmap** — quick-wins (`fixable_by: skill`/`partial`, routed to `/agent-ready fix`) vs `manual` items (with concrete steps), ordered by impact. For `brownfield`, frame the path map-first → delta-specs → characterization tests → incremental sanitization.

### `.agent-ready/badge.svg`
Generate a **self-contained SVG** badge (inline, no external assets) reading `agent-ready: <score>/100`, colored by level (🔴 red `#e05d44` / 🟡 yellow `#dfb317` / 🟢 green `#97ca00` / 🏆 brightgreen `#4c1`). Then print a **paste-ready README snippet**:
```
![Agent Ready](.agent-ready/badge.svg)
```
Offer a shields.io static-URL variant as an alternative for users who prefer external rendering.

### `.agent-ready/agent-ready-report.html` — only when `--format html`
A **self-contained single HTML file** with inline CSS (real colored bars, collapsible findings) generated from the same scores — no external assets, works offline. Markdown remains primary.

### Cleanup
If a remote repo was cloned to `/tmp/`, remove that temp directory after all artifacts are written.

## Important Guidelines

- **Read the canonical files** (`scoring.md`, `remediation.md`) — reference ids/weights from them; never invent numbers.
- **Parallelize** DISCOVER Glob/Grep/Read calls; speed matters.
- **Evidence-based**: only score what file existence/content verifies; cite exact findings in `evidence`.
- **Fair**: reward partial effort (a basic AGENTS.md beats none).
- **Honest layering**: never penalize a portable repo for undeclared-target artifacts.
- **Context discipline**: only compact script JSON enters context; summarize large maps.
- **Safe scanner**: scripts are read-only and never execute project code, even on untrusted repos.
- **Explained, not bare**: every sub-criterion < 100 carries why / consequence / fix / effort from the remediation registry.
