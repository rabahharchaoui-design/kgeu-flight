#!/usr/bin/env python3
"""Regenerate the precache list in sw.js (between // PRECACHE-START and // PRECACHE-END): the radio clips,
the region map and world files (with the ?v=1 the game asks for), the icons, the manifest and the music
playlist. Music tracks are not precached; they are cached as they are played. Run: python3 tools/gen_sw.py"""
import os, json, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def ls(d, ext, q=''):
    return sorted(f'{d}/{f}{q}' for f in os.listdir(os.path.join(ROOT, d)) if f.endswith(ext))
pre = ['./', 'index.html', 'manifest.json', 'assets/music/playlist.json'] + ls('icons', '.png') \
    + ls('assets/map', '.bin', '?v=1') + ls('assets/world', '.json', '?v=1') + ls('radio', '.m4a')
p = os.path.join(ROOT, 'sw.js'); s = open(p).read()
s = re.sub(r'// PRECACHE-START\n.*?// PRECACHE-END', '// PRECACHE-START\nconst PRE=' + json.dumps(pre, separators=(',', ':')) + ';\n// PRECACHE-END', s, flags=re.S)
open(p, 'w').write(s)
print(len(pre), 'files')
