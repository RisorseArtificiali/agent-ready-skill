# Agentic Readiness Remediation Registry (v2)

Canonical, machine-consumed remediation reference for agent-ready v2. Every entry is keyed by a sub-criterion `id` defined in [`scoring.md`](scoring.md) and stores `{ why, consequence, fixable_by, fix_ref, effort }`. This file is part of the **sync contract**: it must stay aligned with the sub-criteria ids in `scoring.md`, and both `agent-ready-report` (renders findings < 100) and `agent-ready-fix` (acts on `fixable_by: skill|partial`) read from it.

**Legend** — `fixable_by`: `skill` = our `agent-ready-fix`/`agent-ready-init` fully handles it · `manual` = not covered by our skills, follow the steps · `partial` = skill scaffolds, human completes the specifics. `effort`: Low / Med / High. Commands shown as `/agent-ready fix <dimension>` target the dimension that owns the sub-criterion.

---

## 1. Agent Instructions & Context (`agent_instructions_context`)

### `primary_instruction_file`
- **why**: `AGENTS.md` is the cross-vendor instruction standard (under the Linux Foundation Agentic AI Foundation since Dec 2025; read natively by 18-23+ tools across 60k+ repos). It is the single canonical place an agent looks first to learn how to build, test, and behave in the repo. Without it, every agent starts cold and reconstructs project knowledge from scratch each session.
- **consequence**: Agents guess build/test/lint commands and conventions, producing wrong scaffolding and wasted turns; with no portable file, switching or adding an agent means re-deriving everything. Claude Code in particular does not read `AGENTS.md` natively (issue #34235), so a missing canonical file plus an un-bridged vendor file means inconsistent guidance per tool.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix agent_instructions_context` — generates a project-specific `AGENTS.md` (and, when targets are declared, the vendor file or symlink) from detected stack, commands, and structure.
- **effort**: Low

### `instruction_quality`
- **why**: Evidence shows generic boilerplate context files do not help (and can slightly hurt) agent success — value comes only from project-specific facts: exact build/test/lint commands, real paths, naming and import conventions, gotchas. Specific instructions are what let an agent act correctly on the first attempt instead of probing.
- **consequence**: Boilerplate that restates obvious facts burns context tokens for no comprehension gain and gives agents false confidence; missing real commands forces trial-and-error that introduces errors and slows every task.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix agent_instructions_context` scaffolds sections (commands, structure, conventions) pre-filled from detection; a human must verify and add domain-specific gotchas and non-obvious rules the scan cannot infer.
- **effort**: Med

### `instruction_conciseness`
- **why**: Over-stuffed instruction files actively degrade performance — Anthropic guidance caps useful instruction files near 200 lines, and studies show bloat causes ~2.5x literal over-reliance and ~+22% token cost with no accuracy gain. Focused instructions keep the model on-signal.
- **consequence**: Long/duplicated instruction files inflate every prompt's token cost, crowd out actual code context, and make the agent over-fixate on stale or boilerplate directives instead of reasoning about the task.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix agent_instructions_context` flags bloat via `instruction_audit.py` and proposes a trimmed structure (move detail into scoped/`references/` files); a human decides which content is genuinely load-bearing.
- **effort**: Low

### `hierarchical_instructions`
- **why**: In large or multi-package repos, scoped per-package/per-subdir instruction files deliver locally-relevant context only when the agent is working in that area — far higher signal-to-token ratio than one giant root file. Scoped instructions are a documented real lever for navigation.
- **consequence**: A single root file either omits package-specific rules (agents miss local conventions) or grows unbounded to cover them all (bloat penalty, lost focus). Cross-cutting edits in monorepos go wrong because per-area context is absent.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix agent_instructions_context` — detects package/workspace boundaries and scaffolds nested `AGENTS.md` stubs seeded with each area's commands and structure.
- **effort**: Med

### `cross_agent_bridge`
- **why**: When multiple agents are targeted, the canonical `AGENTS.md` must be bridged (symlink or `@import`) to each vendor file (e.g. `CLAUDE.md`) so all tools read identical guidance from one source of truth. The top documented multi-agent pitfall is drift/contradiction across duplicated per-tool files.
- **consequence**: Duplicated, hand-maintained per-agent copies drift out of sync; different agents follow conflicting rules, producing inconsistent code and confusing review. A committed vendor file can also itself be an attack surface, so uncontrolled copies multiply risk.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix agent_instructions_context` — creates the bridge for declared targets (e.g. `ln -s AGENTS.md CLAUDE.md` or an `@AGENTS.md` import) and reports any contradictory duplicate copies to remove.
- **effort**: Low

---

## 2. Navigability & Code Intelligence (`navigability_code_intelligence`)

### `repo_map_availability`
- **why**: Repo maps (tree-sitter symbol extraction + graph/PageRank ranking, Aider-style) are the highest-evidence navigation lever — deterministic, ~70% token reduction, and they let an agent locate relevant code without reading the whole tree. Absence is fine *if* a clean map is easily generatable.
- **consequence**: Without a map (committed or cheaply generatable), agents fall back to broad file reads and grep, inflating token cost and missing relevant symbols, which raises error rates on cross-file changes.
- **fixable_by**: `partial`
- **fix_ref**: `repo_map.py` generates a symbol map artifact (run via `/agent-ready fix navigability_code_intelligence`); committing/refreshing it in a docs or `.agent-ready/` location and wiring it into instructions is a human step.
- **effort**: Low

### `semantic_nav_amenability`
- **why**: LSP-based semantic navigation (e.g. Serena across 40+ languages) gives exact symbol lookup, references, and rename — but only works if the code is typed/analyzable and a language server exists for the stack. Amenability is the precondition for the strongest comprehension tooling.
- **consequence**: Untyped, dynamically-constructed, or unanalyzable code defeats LSP/Serena, forcing agents into fuzzy text search; refactors miss call sites and introduce regressions because exact reference tracking is impossible.
- **fixable_by**: `manual`
- **fix_ref**: Add static types in active modules (e.g. type hints, `tsconfig` with `strict`), reduce dynamic metaprogramming at boundaries, and ensure a language server is available for the primary languages; this is real code work our skills do not perform.
- **effort**: High

### `dependency_structure_clarity`
- **why**: A derivable dependency/call graph with clear module boundaries lets agents reason about blast radius before editing — essential at scale and a documented high-evidence lever. Monorepo graph metadata (e.g. Nx) makes this explicit.
- **consequence**: Tangled or implicit dependencies mean an agent cannot predict the impact of a change; edits cause ripple breakage in unseen consumers, and large monorepos become un-navigable without graph metadata.
- **fixable_by**: `manual`
- **fix_ref**: Establish clear module boundaries and explicit dependency declarations; adopt monorepo graph tooling (Nx/Turborepo `project.json`/workspace config) and break cyclic dependencies — architectural work outside our skills' scope.
- **effort**: High

### `readme_overview`
- **why**: A root README giving project purpose, setup, and usage orients an agent (and human) before any deep work — it is the cheapest high-level map of intent and entry points.
- **consequence**: Without an overview, agents misinterpret the project's purpose and entry points, set up the environment incorrectly, and make changes that conflict with the project's actual goals.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix navigability_code_intelligence` scaffolds a README skeleton (purpose, setup, usage, structure) from detected stack; a human fills the project-specific narrative.
- **effort**: Low

### `machine_readable_contracts`
- **why**: Machine-readable contracts (OpenAPI/Protobuf/GraphQL) at service/module boundaries give agents an unambiguous, verifiable interface spec — far more reliable than inferring shapes from code, and they double as test/codegen sources.
- **consequence**: Without contracts, agents infer request/response shapes from scattered code and get them subtly wrong, producing integration bugs at boundaries that only surface at runtime; consumers and producers drift.
- **fixable_by**: `manual`
- **fix_ref**: Author real schemas at your boundaries (OpenAPI for HTTP APIs, `.proto` for RPC, GraphQL SDL) and keep them in version control next to the code they describe; requires domain knowledge our skills cannot supply.
- **effort**: High

### `file_size_sanity`
- **why**: File length is the one human code metric with a robust comprehension correlation — shorter files are understood better by LLMs. Few oversized files (>500 LOC without reason) keeps each unit within a comprehensible, low-token window.
- **consequence**: Oversized files force agents to load large contexts to make small edits, increasing token cost and the chance of misplaced or conflicting changes; large files also resist accurate semantic navigation.
- **fixable_by**: `manual`
- **fix_ref**: Split oversized modules (flagged by `file_metrics.py`) along cohesive responsibilities, prioritizing actively-changed files; safe decomposition requires understanding the code and is not automated by our skills.
- **effort**: Med

---

## 3. Testing & Feedback (`testing_feedback`)

### `test_suite_present`
- **why**: Test feedback is the single highest-impact comprehension signal for coding agents (per FeedbackEval) — a test suite is the verifiable oracle that lets an agent confirm its own changes instead of guessing correctness.
- **consequence**: With no tests, agents have no objective signal that a change works; they ship plausible-but-wrong code, and regressions go undetected until production.
- **fixable_by**: `manual`
- **fix_ref**: Write a real test suite (start with characterization/regression tests around actively-changed modules, per the brownfield path) in `tests/`, `__tests__/`, or `*_test.*`; authoring meaningful tests requires domain logic our skills do not generate.
- **effort**: High

### `test_commands_documented`
- **why**: Tests only provide feedback if the agent can find and run them — documented, discoverable commands (in `AGENTS.md`/Makefile/`package.json`/`pyproject.toml`) close the loop so the agent can self-verify without human prompting.
- **consequence**: Undiscoverable test commands mean agents either skip verification or invent wrong invocations, wasting turns on failed runs and shipping unverified changes despite tests existing.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix testing_feedback` — detects the test runner (via `test_commands.py`) and documents the exact commands in `AGENTS.md` (and a `Makefile` target where appropriate).
- **effort**: Low

### `fast_feedback_loop`
- **why**: A documented fast subset (smoke/affected tests) lets an agent iterate in seconds instead of minutes, dramatically increasing useful feedback cycles per task — slow loops discourage verification.
- **consequence**: If the only option is a slow full run, agents skip verification or burn large wall-clock/token budgets per iteration, reducing the number of corrective cycles and lowering final quality.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix testing_feedback` documents a quick-subset command convention; defining which tests form a meaningful fast subset (markers, affected-test selection) requires human judgment.
- **effort**: Med

### `feedback_quality`
- **why**: The quality of feedback matters as much as its presence — descriptive assertion messages and a configured type-checker (mypy/pyright/`tsconfig` strict) turn failures into precise, actionable signals the agent can fix directly, and catch whole error classes before runtime.
- **consequence**: Bare `assert` and absent type-checking yield opaque failures ("AssertionError" with no context); agents thrash trying to diagnose what broke, and type errors that a checker would flag instantly slip into edits.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix testing_feedback` can scaffold a type-checker config file; enabling strictness on real code (fixing the resulting errors) and improving assertion messages is manual code work.
- **effort**: Med

### `coverage_reasonable`
- **why**: A coverage config/target (or demonstrable test breadth) signals that the verifiable oracle actually exercises the code an agent will touch — coverage is what makes test feedback trustworthy rather than illusory.
- **consequence**: Low/unmeasured coverage means tests pass while real behavior is untested; agents gain false confidence from a green suite and merge changes whose effects were never validated.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix testing_feedback` scaffolds a coverage config (e.g. `coverage`/`pytest-cov`/`nyc`) and a target threshold; actually raising coverage by writing tests is manual.
- **effort**: Med

---

## 4. CI/CD, Automation & Governance (`cicd_automation_governance`)

### `ci_runs_tests_lint`
- **why**: CI that runs tests and lint on every change is the automated, trusted feedback gate that catches what an agent (or human) missed — it makes the test/lint signal mandatory rather than optional, which is critical when agents author many changes quickly.
- **consequence**: Without CI enforcement, broken or unlinted agent-authored changes merge and accumulate; defects are discovered late and the per-fix cost rises sharply.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix cicd_automation_governance` — generates a CI workflow (`.github/workflows/ci.yml` or equivalent) that runs the detected test and lint commands.
- **effort**: Low

### `lint_format_automated`
- **why**: A configured, runnable linter/formatter (ruff/eslint/prettier/rustfmt) enforces conventions mechanically, so agents produce style-consistent code and reviewers focus on substance — opinionated tooling beats prose style rules.
- **consequence**: Without automated lint/format, agents emit inconsistent style that triggers review churn or noisy diffs; style drift accumulates and obscures meaningful changes.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix cicd_automation_governance` — adds a baseline linter/formatter config for the detected stack and wires it into the Makefile/CI.
- **effort**: Low

### `pre_commit_hooks`
- **why**: Pre-commit hooks (`.pre-commit-config.yaml`, `.husky/`, `.lefthook.yml`) shift lint/format/secret checks left to the moment of commit, catching issues before they ever reach CI — fastest possible feedback for agent-authored commits.
- **consequence**: Without hooks, trivially-preventable issues (formatting, leaked secrets, lint errors) reach CI or the remote, wasting CI runs and review cycles and occasionally leaking sensitive data.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix cicd_automation_governance` — generates a pre-commit baseline config wired to the detected lint/format/secret tools.
- **effort**: Low

### `governance`
- **why**: CODEOWNERS plus an automated dependency updater (Dependabot/Renovate) provide review routing and continuous, low-effort supply-chain maintenance — governance that keeps an agent-active repo healthy without constant human attention.
- **consequence**: Missing CODEOWNERS means agent PRs lack clear reviewers and may merge without the right eyes; no dependency automation lets dependencies rot, accumulating known vulnerabilities and breaking-change debt.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix cicd_automation_governance` — generates a `CODEOWNERS` skeleton and a Dependabot/Renovate config for the detected ecosystems.
- **effort**: Low

---

## 5. Agent Tooling & Capabilities (`agent_tooling_capabilities`)

### `standard_skills`
- **why**: Agent Skills is an open standard (agentskills.io) read by Claude Code, Codex, Gemini, Copilot, Cursor, opencode and more; a valid `SKILL.md` (frontmatter, progressive disclosure, <500 lines) packages reusable, portable capabilities that any conformant agent can invoke.
- **consequence**: Without standard Skills, repeatable workflows live only in ad-hoc prompts that don't transfer across agents or sessions; each agent re-improvises, producing inconsistent results and no reusable capability layer.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix agent_tooling_capabilities` (or `/agent-ready init` greenfield) scaffolds a conformant `SKILL.md` skeleton in a standard path; authoring the actual capability content is human work.
- **effort**: Med

### `bundled_helper_scripts`
- **why**: Officially-blessed bundled `scripts/` keep deterministic logic out of the context window — only the output consumes tokens, and behavior is repeatable. Anthropic's own skills repo is ~84% Python for exactly this reason.
- **consequence**: Without helper scripts, deterministic operations are re-derived as model reasoning every time — costing tokens, varying run-to-run, and risking subtle inconsistency that scripts would eliminate.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix agent_tooling_capabilities` scaffolds a `scripts/` layout within a Skill; writing the specific deterministic helpers requires knowing the operation to encode.
- **effort**: Med

### `mcp_declaration`
- **why**: A committed project MCP config (`.mcp.json` or vendor equivalent) declares which tools/servers the project expects, so agents connect to the right capabilities reproducibly. MCP is mature and multi-vendor, though config paths still diverge.
- **consequence**: Without a declared MCP config, each user wires servers manually and inconsistently; agents lack expected tools (or get different ones), making capability-dependent workflows unreproducible across machines and teammates.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix agent_tooling_capabilities` — generates a baseline MCP declaration (`.mcp.json`) and honestly notes per-vendor path portability caveats.
- **effort**: Low

### `nav_comprehension_mcp_servers`
- **why**: Navigation/comprehension MCP servers (Serena for LSP semantic nav, Sourcegraph for code search, Context7 for docs) are the actually-wired-up form of the strongest comprehension levers — they give agents exact symbol/reference/search capability, weighted higher for large repos.
- **consequence**: Without these servers wired up, agents rely on fuzzy text search even when the codebase is amenable to semantic navigation; refactors miss references and large-repo navigation stays token-expensive and error-prone.
- **fixable_by**: `manual`
- **fix_ref**: Add the servers to your MCP config and install/run them: e.g. register Serena (`uvx --from git+https://github.com/oraios/serena serena start-mcp-server`) pointed at the project, plus Sourcegraph and/or Context7 endpoints. Wiring, auth, and per-agent path bridging require human setup our skills do not perform.
- **effort**: Med

### `custom_commands`
- **why**: Vendor custom commands / reusable prompts (e.g. `.claude/commands/`) capture repeatable workflows for a specific agent — legacy-positive signal (Skills are now preferred, but committed commands still help that target).
- **consequence**: Without them (and without Skills), recurring per-agent workflows are retyped each time, inviting inconsistency; this is the weakest of the tooling signals, so absence matters less than missing Skills/MCP.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix agent_tooling_capabilities` can scaffold a command/prompt stub for a declared target; prefer migrating recurring workflows to standard Skills. Authoring the command content is manual.
- **effort**: Low

---

## 6. Security & Sandbox (`security_sandbox`)

### `committed_isolation_config`
- **why**: True isolation (a `.devcontainer/` with default-deny egress allowlist, OS sandbox, or microVM) is the only reliable boundary for autonomous agent execution — denylists are not a security boundary (Claude Code's sandbox path-trick bypass, Mar 2026). Committed config makes isolation reproducible for every contributor.
- **consequence**: Without committed isolation, an agent running malicious or compromised code (e.g. via a rogue dependency or MCP server) can exfiltrate secrets or reach the network freely; SANDWORM_MODE-style attacks read `.env`/keys directly.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix security_sandbox` scaffolds a `.devcontainer/` note/template with a default-deny egress allowlist; hardening it to true isolation (real allowlist, resource limits, microVM choice) is a human security decision.
- **effort**: Med

### `documented_execution_policy`
- **why**: A committed doc/section declaring the recommended sandbox (devcontainer / OS-sandbox / hosted such as LINCE) plus a safe-to-run command list is how non-detectable runtime sandboxes earn credit — it tells every agent and contributor how to execute safely. Self-reports are unverifiable, so documentation is the evidence.
- **consequence**: Without a documented policy, contributors run agents with inconsistent (often no) isolation, and there's no agreed safe-command list — so risky operations get auto-approved and the repo's actual execution posture is unknowable.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix security_sandbox` — generates `docs/agent-execution.md` (or an `AGENTS.md` section) listing the recommended sandbox options vendor-neutrally (devcontainer / OS-sandbox / hosted incl. LINCE) and a safe-to-run command list.
- **effort**: Low

### `agent_permission_policy`
- **why**: A restrictive committed permission policy (Claude `.claude/settings.json` deny rules, Codex `sandbox_mode`+`approval_policy`, opencode `permission`) constrains what an agent may do without approval — credited only when genuinely restrictive, since a committed config is also an attack surface (CVE-2025-59536 RCE via `.claude/settings.json`).
- **consequence**: Permissive or absent policy lets agents run arbitrary commands/edits unprompted; a carelessly-committed config can itself be weaponized for RCE, and over-broad allowances turn one bad suggestion into real damage.
- **fixable_by**: `manual`
- **fix_ref**: Author restrictive deny rules / approval policy for each declared target by hand (e.g. deny destructive shell, network, and credential-path access; require approval for writes) — requires human judgment about your threat model, and the committed file must itself be reviewed as attack surface.
- **effort**: Med

### `secret_hygiene`
- **why**: AI-assisted commits leak secrets at ~2x baseline (3.2% vs 1.5%), so secret hygiene is acutely important for agent-active repos: `.gitignore` covering secret files, a values-free `.env.example`, and CI secret scanning + push protection together prevent leaks at multiple layers.
- **consequence**: A leaked credential is immediately exploitable and often irrecoverable (rotation, blast radius, audit cost); without `.env.example` agents also fabricate config shapes, and without scanning/push-protection a leaked secret reaches the remote before anyone notices.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix security_sandbox` adds secret patterns to `.gitignore` and generates a redacted `.env.example` (via `secret_hygiene.py` signals); enabling secret scanning + push protection on the git host (GitHub/GitLab) is a manual host-side configuration step.
- **effort**: Med

### `supply_chain_pinning`
- **why**: Committed lockfiles (not gitignored) plus Dependabot/Renovate and provenance where available pin the dependency surface agents and CI install — preventing silent drift into vulnerable or malicious versions (rogue npm packages spawning malicious MCP servers, Feb 2026).
- **consequence**: Without committed lockfiles, builds are non-reproducible and a compromised transitive dependency can be pulled in silently; without automated updates, known-vulnerable versions persist indefinitely.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix security_sandbox` generates Dependabot/Renovate config and flags gitignored lockfiles (via `lockfile_check.py`); committing the lockfiles and enabling provenance/attestation is a manual repo step.
- **effort**: Low

### `injection_hygiene`
- **why**: Prompt-injection defense for code agents means instructions live only in trusted files — agent-read docs (READMEs, data files, issue bodies) must not contain executable or instruction-like content that an agent might obey as a command (OWASP LLM prompt-injection guidance).
- **consequence**: Instruction-like content in untrusted/agent-read locations can hijack the agent into running unintended commands or exfiltrating data; even unintentional imperative text in docs causes the agent to follow stray directives.
- **fixable_by**: `manual`
- **fix_ref**: Audit agent-read content so instructions live only in designated trusted files (`AGENTS.md` and bridges); strip or neutralize instruction-like/executable content from READMEs, fixtures, and ingested data, and treat external/untrusted input as data, not commands — requires human review.
- **effort**: Med

---

## 7. Spec-Driven Workflow & Docs (`spec_driven_workflow_docs`)

### `spec_tasks_dir`
- **why**: A `specs/`/`tasks/`/`prd/` directory with real content gives agents an authoritative statement of *what* to build before *how* — spec-driven development is the proven workflow for steering agents, and delta-scoped specs are especially valuable in brownfield where whole-system docs are impractical.
- **consequence**: Without specs, agents infer intent from code and chat alone, drift from actual requirements, and produce work that misses the goal; large changes lack a shared contract, causing rework and scope disputes.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix spec_driven_workflow_docs` (or `/agent-ready init` greenfield) — scaffolds a `specs/`/`tasks/` structure with delta-scoped spec templates; populating real specs is then expected per change.
- **effort**: Low

### `acceptance_criteria`
- **why**: Explicit acceptance criteria in specs/issues give an agent a verifiable definition of done — concrete, checkable conditions that turn "build feature X" into something the agent can confirm it has actually satisfied.
- **consequence**: Without acceptance criteria, "done" is subjective; agents stop too early or gold-plate, and reviewers can't objectively verify completeness, multiplying review rounds.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix spec_driven_workflow_docs` scaffolds an acceptance-criteria section in spec/issue templates; writing the specific, testable criteria for each item requires human/domain input.
- **effort**: Med

### `issue_pr_templates`
- **why**: Issue/PR templates (`.github/ISSUE_TEMPLATE/`, PR template) standardize the context provided with each unit of work — ensuring agents and humans capture the problem statement, scope, and checks needed for consistent, reviewable contributions.
- **consequence**: Without templates, issues and PRs arrive with inconsistent or missing context; agents working from thin issue descriptions produce off-target changes, and PR review lacks a checklist for quality/security gates.
- **fixable_by**: `skill`
- **fix_ref**: `/agent-ready fix spec_driven_workflow_docs` — generates `.github/ISSUE_TEMPLATE/` entries and a PR template seeded with scope, testing, and checklist sections.
- **effort**: Low

### `adr_decisions`
- **why**: Architecture Decision Records (`docs/adr/`, decision logs) preserve the *why* behind design choices — context an agent cannot infer from code, preventing it from "fixing" deliberate decisions or re-litigating settled trade-offs.
- **consequence**: Without ADRs, agents (and new contributors) reverse intentional decisions, reintroduce previously-rejected approaches, and waste cycles rediscovering rationale that was never written down.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix spec_driven_workflow_docs` scaffolds a `docs/adr/` directory with an ADR template; capturing actual past and future decisions is human knowledge work.
- **effort**: Med

### `docs_comprehension_signals`
- **why**: An architecture doc plus measurable comprehension signals — type-annotation coverage, docstring coverage (per `coverage_signals.py`), and a changelog — give agents both high-level structure and machine-checkable code legibility, the levers that genuinely aid comprehension over decorative docs.
- **consequence**: Sparse types/docstrings and no architecture overview force agents to reverse-engineer structure and intent from raw code, raising token cost and error rate; a missing changelog hides what recently changed and why, complicating safe edits.
- **fixable_by**: `partial`
- **fix_ref**: `/agent-ready fix spec_driven_workflow_docs` scaffolds an architecture-doc skeleton and a changelog, and reports type/docstring coverage gaps from `coverage_signals.py`; writing the real architecture narrative and adding annotations/docstrings in code is manual.
- **effort**: Med
