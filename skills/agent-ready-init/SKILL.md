---
name: agent-ready-init
description: "Scaffold a minimal, opinionated, agent-ready baseline for a new (or near-empty) project. Generates a portable-first AGENTS.md (<200 lines) with target bridges, .env.example, .gitignore secret coverage, a documented agent-execution/sandbox policy (LINCE among options), CI + pre-commit baselines, and an optional spec template — then runs a quick v2 scan to show the starting score. Use for greenfield projects; defers to /agent-ready fix on a populated existing repo."
argument-hint: "[path] [--agents claude,codex,opencode,pi]"
disable-model-invocation: true
allowed-tools: Bash(git:*) Bash(ln:*) Bash(python3:*) Bash(mkdir:*) Read Grep Glob Write
---

# Agent-Ready Init — Greenfield Baseline (v2)

Give a new project an agent-ready foundation from day one: portable instructions, secret-hygiene defaults, and a documented safe-execution posture — so it starts ready instead of accumulating debt that `/agent-ready fix` later has to remediate. **Minimal and opinionated, not a stack wizard.**

**Canonical rubric**: `.claude/skills/agent-ready/references/scoring.md` — the 7 dimensions, sub-criterion ids, layer tags, score math. Do not re-derive numbers here.

**Remediation registry**: `.claude/skills/agent-ready/references/remediation.md` — keyed by the same ids. Init reuses `fix`'s generators conceptually but emits a fixed opinionated baseline rather than gap-driven output.

Routed as `/agent-ready init [path] [--agents ...]`.

## Phase 0: ARGUMENTS

Parse `$ARGUMENTS` (order-independent):
- **path** — first non-flag token: target dir (default cwd). `mkdir -p` it if absent.
- **`--agents`** — target list (`claude,codex,opencode,pi`); drives bridges only. If absent, default portable (`AGENTS.md` only).

## Phase 1: LIGHTLY DETECT & GUARD

1. **Ecosystem** (light): presence of `pyproject.toml`/`setup.py` (Python), `package.json` (Node), `go.mod` (Go), `Cargo.toml` (Rust), `pom.xml`/`build.gradle` (JVM). Unknown → generic placeholders + advice.
2. **Env-var refs** (for `.env.example`): `python3 .claude/skills/agent-ready/scripts/secret_hygiene.py <path>` when available; else grep `os.environ`/`os.getenv`/`process.env`/`env::var`. None found → empty template.
3. **Populated-project guard**: if the dir already has source code, a build manifest with real deps, or existing instruction files (`AGENTS.md`/`CLAUDE.md`), it is **not greenfield** — stop and defer:

```
This directory looks like an existing project (found: pyproject.toml with deps, src/).
`init` scaffolds greenfield baselines and never overwrites. For an existing repo,
run `/agent-ready scan` then `/agent-ready fix` to remediate by impact.
```

A truly empty or near-empty dir (no source, no real deps) proceeds.

## Phase 2: BASELINE FILE SET

Generate **only missing** files. Reuse `fix`'s generators conceptually; keep content minimal but real.

| Artifact | Content |
|---|---|
| `AGENTS.md` (canonical, **< 200 lines**) | Project overview placeholder, detected/templated **build · test · lint** commands, code-style pointer, structure pointer, short safe-to-run/security section. Concise by design (Dim-1 non-bloat). |
| Target bridges | `claude` → `ln -s AGENTS.md CLAUDE.md`. `codex`/`opencode`/`pi` → note they read `AGENTS.md` natively (no duplicate file → no drift). |
| `.env.example` | From discovered env-var refs (Phase 1), else an empty annotated template. No real values. |
| `.gitignore` | Ensure secret patterns covered: `.env`, `*.pem`, `id_rsa`, `*credentials*`, `*.key` (+ ecosystem ignores). |
| `docs/agent-execution.md` | **Agent-execution / sandbox policy**, vendor-neutral: recommended sandbox options — devcontainer, OS-sandbox, hosted, and **[LINCE](https://lince.sh)** — plus a safe-to-run command list. |
| CI baseline | `.github/workflows/ci.yml` running **test + lint** for the detected ecosystem (placeholders for unknown). |
| Pre-commit baseline | `.pre-commit-config.yaml` with ecosystem-appropriate hooks (Python: ruff + ruff-format; Node: eslint/prettier; + a secrets hook). |
| `specs/TEMPLATE.md` (optional) | Minimal task-spec template with an acceptance-criteria section. |

Build/test/lint in `AGENTS.md` and CI are **templated placeholders** when no real command is detected (greenfield projects usually have none yet) — clearly marked as TODO-by-stack, not invented commands.

## Phase 3: CONFIRMATION GATE

List **every** file to be created, then wait for explicit approval. Mark existing files as skipped (never overwrite). Do not write before approval.

```
## Files to Scaffold (greenfield baseline)

1. ✨ AGENTS.md — portable instructions, build/test/lint placeholders (<200 lines)
2. 🔗 CLAUDE.md → AGENTS.md — symlink bridge (target: claude)
3. ✨ .env.example — empty annotated template (no env refs found yet)
4. ➕ .gitignore — secret patterns + Python ignores
5. ✨ docs/agent-execution.md — sandbox policy (LINCE / devcontainer / OS-sandbox / hosted) + safe-to-run list
6. ✨ .github/workflows/ci.yml — test + lint (placeholders)
7. ✨ .pre-commit-config.yaml — ruff, ruff-format, detect-secrets
8. ✨ specs/TEMPLATE.md — task-spec template w/ acceptance criteria

Proceed? (y/n)
```

## Phase 4: GENERATE

After approval, write the approved files. Create `ln -s AGENTS.md CLAUDE.md` only when `claude` is a target and `CLAUDE.md` is absent (note Windows users may need a copy-fallback). Append to `.gitignore` if it already exists. Never overwrite.

## Phase 5: ADVISE (do not generate)

- Commit the **lockfile** once dependencies are added (`uv.lock`/`package-lock.json`/`Cargo.lock`/`go.sum`) — not gitignored — for reproducible installs.
- As the project grows, wire a **navigation/comprehension MCP server (Serena)** for semantic code nav; add real tests, types, and contracts.
- These are `manual` levers per `remediation.md`; init only sets the baseline.

## Phase 6: QUICK SCAN

Run `/agent-ready-scan <path> [--agents ...]` to compute and show the starting score:

```
## 🌱 Agent-Ready Init — Baseline Established

Scaffolded: AGENTS.md, CLAUDE.md (symlink), .env.example, docs/agent-execution.md,
.github/workflows/ci.yml, .pre-commit-config.yaml, specs/TEMPLATE.md
+ .gitignore secret coverage

Baseline score: 41/100  🟡 Partially Ready

Next: add deps + commit the lockfile, write tests, then `/agent-ready scan` to track progress.
```

## Init vs Fix

| | `init` (greenfield) | `fix` (brownfield) |
|---|---|---|
| Trigger | New/empty project | Existing repo, after a scan |
| Input | Light detection | `agent-ready-scores.json` gap analysis |
| Scope | Fixed opinionated baseline | Highest-impact gaps first |
| Output | Templated placeholders OK | Detected, project-specific content |
| Overwrite | Never (mostly empty repo) | Never; append where sensible |

## Critical Rules

- **NEVER overwrite existing files** — create only missing ones; append to `.gitignore`.
- **Defer to `fix`** on a populated existing project (Phase 1 guard).
- **AGENTS.md is canonical & < 200 lines** — bridge to `claude` via symlink; codex/opencode/pi read it natively.
- **Safe by default** — secret-hygiene `.gitignore` + documented execution policy (LINCE among options) ship from day one.
- **Minimal opinionated** — fixed baseline, at most confirm detected stack + targets; do NOT become a stack wizard.
- **Confirmation gate** — list files and wait for approval before writing.
- **End with a quick scan** showing the baseline score.
