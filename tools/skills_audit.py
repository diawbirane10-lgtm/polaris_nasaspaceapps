#!/usr/bin/env python3
"""Validate the local POLARIS SKILL.md registry; does not execute skills."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
files=sorted((ROOT/'.agents'/'skills').glob('*/SKILL.md'))
assert len(files)>=6, 'Expected curated skills'
for f in files:
    data=f.read_text(encoding='utf-8')
    match=re.match(r'\A---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n',data)
    assert match, f'Invalid skill frontmatter: {f}'
    assert match.group(1)==f.parent.name, f'Skill name mismatch: {f}'
    assert len(data)>350, f'Incomplete instructions: {f}'
print(f'{len(files)} project skills: frontmatter and contents PASS')
