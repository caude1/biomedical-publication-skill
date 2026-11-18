# Maintaining this repository

These notes are for anyone, person or coding agent, who changes this repository.

## Every change to the skill is a release

People install this skill as a plugin, and Claude Code delivers an update only when the version number changes. So whenever a change touches `plugins/biomedical-publication-suite/skills/` or either `plugin.json`:

1. Raise `"version"` in both `plugins/biomedical-publication-suite/.claude-plugin/plugin.json` and `plugins/biomedical-publication-suite/.codex-plugin/plugin.json`. They must match. Use the third number for fixes and wording (1.3.4 → 1.3.5), the second for new guidance or workflows (1.3.5 → 1.4.0).
2. Add a `## <version> (<date>)` entry at the top of `plugins/biomedical-publication-suite/CHANGELOG.md`. Its first paragraph becomes the release note, so write it for the people who installed the skill.
3. Run the checks from `plugins/biomedical-publication-suite`:

   ```bash
   python3 -m unittest discover -s tests
   python3 scripts/validate_suite.py
   ```

The `tests` workflow fails a pull request whose skill changes keep the old version or lack a changelog entry.

## Content rules

- Every example study, number and name in the skill is synthetic. Never add text, numbers or topics from a real unpublished manuscript.
- No personal email addresses or home-folder paths in any file. Use relative paths.
- Prose guidance is written for an agent to apply by judgment; scripts check only facts a machine can settle.
