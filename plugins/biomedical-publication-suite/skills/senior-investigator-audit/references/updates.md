# Updates

The plugin's skills (biomedical-publication-suite, senior-investigator-audit, and readable-scientific-code) share one version number and one weekly update check. Run `scripts/check_update.py` from the skill in use once per session, as its SKILL.md says, and respond to what it prints.

- **`UPDATE AVAILABLE: …`** A newer version is published. Tell the user in one or two sentences and show the commands it printed, offering to run them. Run them only on the user's yes. When they finish, run the same script with `--whats-new` and give the user the after-update message described below. Then say that the new version takes effect after Claude Code restarts or in a new Codex session, and continue with the task.
- **`UPDATED: …`** The skills were updated since they were last used, whether by the user, by automatic updates, or by the steps above. Unless the output says the changes were already shown, give the user the after-update message. Then continue with the task.
- **Any other line** ("Up to date", "not due", "could not reach GitHub", "turned off"): mention it only if the user asks.

## The after-update message

Write it from the changelog entries the script printed, for the user to read in under a minute:

1. One line naming the old and new versions.
2. What changed, in a few plain sentences grouped by what the user will notice, most useful first. Combine several versions into one account when the user skipped some.
3. A brief tutorial: two to four example requests that use what is new, taken from the entries' "How to use it" notes and adapted to the user's current task when one is in progress. Use the invocation for the host: `$skill-name` in Codex; in Claude Code, the skill's name in a request, or `/biomedical-publication-suite:<skill-name>` when installed as a plugin.

Do not paste the changelog. If the script could not read it, give the release-page link it printed.
