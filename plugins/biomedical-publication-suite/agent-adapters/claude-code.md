# Claude Code adapter

Point the client's supported skills mechanism to the portable `skills/biomedical-publication-suite` directory under this plugin root. If user-level skill discovery is supported in the installed client, the optional installer can create `~/.claude/skills/biomedical-publication-suite` as an alias:

```bash
bash agent-adapters/scripts/install-agent-skill.sh --claude-user
```

Run from the plugin root. Verify actual client discovery. Follow the canonical SKILL.md and load only relevant references; do not paste the full reference library into a global instruction file.
