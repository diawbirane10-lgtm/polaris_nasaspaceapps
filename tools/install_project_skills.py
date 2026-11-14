#!/usr/bin/env python3
"""Copy vetted project SKILL.md files into a local agent-specific skills directory."""
import argparse
from pathlib import Path
import shutil
p=argparse.ArgumentParser(); p.add_argument('--target',choices=['codex','claude'],required=True)
a=p.parse_args(); root=Path(__file__).resolve().parents[1]
src=root/'.agents'/'skills';dest=root/('.codex' if a.target=='codex' else '.claude')/'skills'
for s in src.iterdir():
    if s.is_dir() and (s/'SKILL.md').is_file():
        dst=dest/s.name;dst.mkdir(parents=True,exist_ok=True)
        shutil.copy2(s/'SKILL.md',dst/'SKILL.md')
print(f'Copied {len(list(src.glob("*/SKILL.md")))} reviewed project skills to {dest}')
