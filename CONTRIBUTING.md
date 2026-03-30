# Contributing to Agent Ready Skill

## Overview

Agent Ready Skill is an [agentskills.io](https://agentskills.io)-compliant skill that assesses and improves any project's readiness for agentic coding.

## How to Contribute

### Adding or Modifying Assessment Criteria

Assessment dimensions and sub-criteria are defined in the skill markdown files under `skills/`. Each skill follows the agentskills.io standard format.

1. Fork the repository
2. Edit the relevant skill file in `skills/`
3. If adding new sub-criteria, ensure the dimension weights still sum to 100
4. Submit a pull request with a clear description of why the criteria was added/changed

### Adding New Skills

1. Create a new directory under `skills/` with a `SKILL.md` file
2. Follow the agentskills.io format (see existing skills as reference)
3. Update `README.md` with the new skill description
4. Submit a pull request

### Skill Format

Each skill directory must contain at minimum a `SKILL.md` file following the [agentskills.io specification](https://agentskills.io).

## Installation for Development

```bash
git clone https://github.com/RisorseArtificiali/agent-ready-skill.git
cd agent-ready-skill
for skill in agent-ready agent-ready-scan agent-ready-fix agent-ready-report agent-ready-diff; do
  ln -sf "$(pwd)/skills/$skill" "$HOME/.claude/skills/$skill"
done
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
