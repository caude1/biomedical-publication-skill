# Other agent clients

Load `skills/biomedical-publication-suite/SKILL.md` from this plugin root through the client's supported skill mechanism. For clients using `~/.agents/skills`, the optional alias installer is `bash agent-adapters/scripts/install-agent-skill.sh --agents-user`.

If native skill loading is unavailable, use the [short context snippet](context-snippet.md) and provide the canonical SKILL.md path. Tools, external transfers, approvals and filesystem access remain governed by the host and user request. No particular connector, model or multi-agent runtime is required.
