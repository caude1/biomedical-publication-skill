#!/usr/bin/env python3
"""Maintainer check of resource integrity; does not evaluate manuscript quality."""
from __future__ import annotations
import ast
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
SKILL=ROOT/'skills/biomedical-publication-suite'
# Files every skill in the plugin carries an identical copy of, so each skill also works on its own.
SHARED=['scripts/check_update.py','references/updates.md','VERSION','LICENSE.txt']


def skill_dirs(root: Path) -> list[Path]:
    return sorted(p for p in (root/'skills').iterdir() if p.is_dir() and (p/'SKILL.md').is_file())


def check_skill(skill: Path, errors: list[str]) -> None:
    core=(skill/'SKILL.md').read_text()
    if not core.startswith('---\n') or len(core.split('---',2))!=3:
        errors.append(f'{skill.name}: invalid skill frontmatter framing')
        return
    front=core.split('---',2)[1]
    if not re.search(rf'^name: {re.escape(skill.name)}$',front,re.M): errors.append(f'{skill.name}: skill name differs from its folder')
    if not re.search(r'^description: .+',front,re.M): errors.append(f'{skill.name}: missing description')
    if len(core.splitlines())>500: errors.append(f'{skill.name}: entrypoint exceeds 500 lines; review disclosure structure')
    if not (skill/'agents/openai.yaml').is_file(): errors.append(f'Missing skills/{skill.name}/agents/openai.yaml')
    if 'scripts/check_update.py' not in core: errors.append(f'{skill.name}: SKILL.md does not run the update check')
    # Every reference must be reachable from the entry file or another reference, by link or by path.
    refs=set((skill/'references').glob('*.md'))
    texts=[core,*(r.read_text() for r in refs)]
    for ref in refs:
        others=[text for path, text in zip([skill/'SKILL.md',*refs],texts) if path!=ref]
        named=any(f'references/{ref.name}' in text or f']({ref.name}' in text for text in others)
        if not named: errors.append(f'Undiscoverable reference: {skill.name}/references/{ref.name}')


def validate(root: Path=ROOT) -> list[str]:
    errors=[]
    skill=root/'skills/biomedical-publication-suite'
    required=['.codex-plugin/plugin.json','skills/biomedical-publication-suite/SKILL.md','skills/biomedical-publication-suite/agents/openai.yaml','THIRD_PARTY_NOTICES.md','CHANGELOG.md']
    for rel in required:
        if not (root/rel).is_file(): errors.append('Missing '+rel)
    for p in sorted(root.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts: continue
        if p.suffix=='.py':
            try: ast.parse(p.read_text(),filename=str(p))
            except (SyntaxError,UnicodeError) as e: errors.append(str(e))
        elif p.suffix=='.json':
            try: json.loads(p.read_text())
            except (ValueError,UnicodeError) as e: errors.append(f'{p}: {e}')
        elif p.suffix=='.md':
            text=p.read_text()
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
                target=target.strip('<>').split('#')[0]
                if not target or re.match(r'[a-z][a-z+.-]*:',target,re.I) or target.startswith('/'): continue
                # Plain relative resource links only; URLs and explicit illustrative placeholders are excluded.
                if '<' in target or '>' in target: continue
                dest=(p.parent/unquote(target)).resolve()
                if not dest.exists(): errors.append(f'{p.relative_to(root)}: unresolved link {target}')
    if not (skill/'SKILL.md').is_file():
        return errors
    manifest=json.loads((root/'.codex-plugin/plugin.json').read_text())
    # Installed plugin roots may be named for their version. The skill directory has a stable name.
    if manifest.get('name') != skill.name:
        errors.append('Plugin name differs from the packaged skill name')
    if not (root/manifest.get('skills','missing')).is_dir(): errors.append('Missing declared skill directory')
    skills=skill_dirs(root)
    for each in skills:
        check_skill(each, errors)
    # Shared files are identical in every skill, and the version matches the manifest.
    for rel in SHARED:
        primary=skill/rel
        if not primary.is_file():
            errors.append(f'Missing skills/{skill.name}/{rel}')
            continue
        for each in skills:
            copy=each/rel
            if not copy.is_file(): errors.append(f'Missing skills/{each.name}/{rel}')
            elif copy.read_bytes()!=primary.read_bytes(): errors.append(f'skills/{each.name}/{rel} differs from the copy in skills/{skill.name}')
    version_file=skill/'VERSION'
    if version_file.is_file() and version_file.read_text().strip()!=manifest.get('version'):
        errors.append('skills/biomedical-publication-suite/VERSION differs from the plugin manifest version')
    claude=root/'.claude-plugin/plugin.json'
    if claude.exists() and json.loads(claude.read_text()).get('version')!=manifest.get('version'):
        errors.append('Plugin manifest versions differ between .codex-plugin and .claude-plugin')
    changelog=root/'CHANGELOG.md'
    if changelog.is_file() and not re.search(rf"^## {re.escape(str(manifest.get('version')))}\b",changelog.read_text(),re.M):
        errors.append(f"CHANGELOG.md has no '## {manifest.get('version')}' entry")
    evals=json.loads((root/'tests/behavioral-evals.json').read_text())['evals']
    ids=[x['id'] for x in evals]
    if len(ids)!=len(set(ids)): errors.append('Duplicate behavioral evaluation IDs')
    for e in evals:
        if not e.get('prompt') or not e.get('expectations'): errors.append('Incomplete evaluation '+str(e.get('id')))
    # Portability: shipped text must not carry a maintainer's home-directory path.
    for p in root.rglob('*'):
        if p.is_file() and p.suffix in {'.md','.py','.json','.yaml','.toml','.sh'} and '.git' not in p.parts and p.name!='validate_suite.py':
            if re.search(r'(?<![\w.])/(?:Users|home)/[A-Za-z0-9_.-]+/', p.read_text(errors='ignore')):
                errors.append(f'{p.relative_to(root)}: contains an absolute home-directory path')
    return errors

if __name__=='__main__':
    errors=validate()
    print(json.dumps({'scope':'maintainer_resource_integrity_only','errors':errors,'status':'pass' if not errors else 'fail'},indent=2))
    raise SystemExit(bool(errors))
