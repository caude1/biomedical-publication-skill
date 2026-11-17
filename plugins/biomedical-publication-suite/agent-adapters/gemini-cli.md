# Gemini CLI adapter

The optional installer can link the same portable skill to `~/.gemini/skills/biomedical-publication-suite`:

```bash
bash agent-adapters/scripts/install-agent-skill.sh --gemini-user
```

Run from the plugin root and verify the installed client's current skill-discovery support. The [command template](gemini-cli/commands/biomed-pub.toml) is an optional invocation aid; installing the skill alias does not install that command. Use the client's documented configuration location if the command is desired. No separate scientific workflow lives in this adapter.
