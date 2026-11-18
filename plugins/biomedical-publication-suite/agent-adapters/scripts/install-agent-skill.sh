#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Install or link the Biomedical Publication Suite skills for other local agents.
Each skill folder in the plugin (the publication suite, the senior
investigator audit, and readable scientific code) gets its own link.

Usage:
  install-agent-skill.sh --claude-user
  install-agent-skill.sh --gemini-user
  install-agent-skill.sh --agents-user
  install-agent-skill.sh --all-user
  install-agent-skill.sh --print

This script creates symlinks only when the destination does not already exist.
It refuses to overwrite existing files or directories.
USAGE
}

script_dir="$(cd "$(dirname "$0")" && pwd)"
plugin_root="$(cd "$script_dir/../.." && pwd)"
skill_names=()
for dir in "$plugin_root"/skills/*/; do
  [ -f "$dir/SKILL.md" ] && skill_names+=("$(basename "$dir")")
done

link_one() {
  local dest_root="$1"
  local label="$2"
  local skill_name="$3"
  local skill_src="$plugin_root/skills/$skill_name"
  local dest="$dest_root/$skill_name"

  if [ ! -f "$skill_src/SKILL.md" ]; then
    echo "Missing source skill: $skill_src/SKILL.md" >&2
    return 1
  fi

  mkdir -p "$dest_root"

  if [ -L "$dest" ]; then
    local target
    target="$(readlink "$dest")"
    if [ "$target" = "$skill_src" ]; then
      echo "$label: already linked to $skill_src"
      return 0
    fi
    echo "$label: destination is already a symlink to $target; refusing to overwrite." >&2
    return 1
  fi

  if [ -e "$dest" ]; then
    echo "$label: destination already exists at $dest; refusing to overwrite." >&2
    return 1
  fi

  ln -s "$skill_src" "$dest"
  echo "$label: linked $dest -> $skill_src"
}

link_skill() {
  local status=0
  for name in "${skill_names[@]}"; do
    link_one "$1" "$2" "$name" || status=1
  done
  return $status
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

case "$1" in
  --claude-user)
    link_skill "$HOME/.claude/skills" "Claude Code"
    ;;
  --gemini-user)
    link_skill "$HOME/.gemini/skills" "Gemini CLI"
    ;;
  --agents-user)
    link_skill "$HOME/.agents/skills" "Agent Skills alias"
    ;;
  --all-user)
    link_skill "$HOME/.claude/skills" "Claude Code"
    link_skill "$HOME/.gemini/skills" "Gemini CLI"
    link_skill "$HOME/.agents/skills" "Agent Skills alias"
    ;;
  --print)
    for name in "${skill_names[@]}"; do
      echo "Source skill: $plugin_root/skills/$name"
      echo "  Claude user destination: $HOME/.claude/skills/$name"
      echo "  Gemini user destination: $HOME/.gemini/skills/$name"
      echo "  Agent Skills alias destination: $HOME/.agents/skills/$name"
    done
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage
    exit 2
    ;;
esac

