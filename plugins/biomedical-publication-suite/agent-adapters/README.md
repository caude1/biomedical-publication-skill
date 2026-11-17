# Portable agent adapters

The portable payload is `skills/biomedical-publication-suite` relative to this plugin root. Use the client's supported skill loader or point it at that directory. Keep one canonical source and aliases where practical; do not maintain competing copies.

[Claude Code](claude-code.md), [Gemini CLI](gemini-cli.md), and [other clients](other-agents.md) describe the local adapters. These are compatibility entrypoints, not separate scientific implementations. Client discovery behavior may differ by installed version; verify the skill is visible before claiming integration.

`scripts/install-agent-skill.sh --print` prints the source and destinations. The opt-in --claude-user, --gemini-user and --agents-user modes create symlinks only when absent and refuse to overwrite other files/links. --all-user applies them sequentially; if a later destination conflicts, earlier successful links remain. It does not delete existing content.
