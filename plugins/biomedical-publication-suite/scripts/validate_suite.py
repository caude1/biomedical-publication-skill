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

def validate(root: Path=ROOT) -> list[str]:
    errors=[]
    skill=root/'skills/biomedical-publication-suite'
    required=['.codex-plugin/plugin.json','skills/biomedical-publication-suite/SKILL.md','skills/biomedical-publication-suite/agents/openai.yaml','THIRD_PARTY_NOTICES.md']
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
    core=(skill/'SKILL.md').read_text()
    if not core.startswith('---\n') or len(core.split('---',2))!=3: errors.append('Invalid skill frontmatter framing')
    else:
        front=core.split('---',2)[1]
        if not re.search(r'^name: biomedical-publication-suite$',front,re.M): errors.append('Skill name mismatch')
        if not re.search(r'^description: .+',front,re.M): errors.append('Missing description')
    if len(core.splitlines())>500: errors.append('Entrypoint exceeds 500 lines; review disclosure structure')
    manifest=json.loads((root/'.codex-plugin/plugin.json').read_text())
    # Installed plugin roots may be named for their version. The skill directory has a stable name.
    if manifest.get('name') != skill.name:
        errors.append('Plugin name differs from the packaged skill name')
    if not (root/manifest.get('skills','missing')).is_dir(): errors.append('Missing declared skill directory')
    refs=set((skill/'references').glob('*.md'))
    linked=set()
    for p in [skill/'SKILL.md', *refs]:
        for target in re.findall(r'\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)',p.read_text()):
            linked.add((p.parent/target).resolve())
    for ref in refs:
        if ref.resolve() not in linked: errors.append(f'Undiscoverable reference: {ref.name}')
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
    claude=root/'.claude-plugin/plugin.json'
    if claude.exists() and json.loads(claude.read_text()).get('version')!=manifest.get('version'):
        errors.append('Plugin manifest versions differ between .codex-plugin and .claude-plugin')
    return errors

if __name__=='__main__':
    errors=validate()
    print(json.dumps({'scope':'maintainer_resource_integrity_only','errors':errors,'status':'pass' if not errors else 'fail'},indent=2))
    raise SystemExit(bool(errors))
