#!/usr/bin/env python3
"""The product rename FielDes -> FielDev over the tracked files (read and written as bytes, so every encoding is kept).

    FIELDES -> FIELDEV     FielDes -> FielDev     fielDes -> fieldev     fieldes -> fieldev

Left alone on purpose: CHANGELOG.md (FielDes's history), LICENSE-*, NOTICE.md and README.md (edited by hand afterwards: they say whose fork this is), and this file.
`--dry` only counts.  Afterwards the five paths that carry the name are moved with `git mv`, and the files that still carry the old name are listed.

It works on the repository this file is in, from wherever it is run:

    python scripts/rename_product.py --dry
    python scripts/rename_product.py

A one-time tool: `git rm scripts/rename_product.py` once the rename is made.  Everything it does is undone by `git checkout -- . && git reset --hard`
(the rename is made on a clean tree, so that the repository has nothing else in it to lose).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
dry = '--dry' in sys.argv
skip_names = {'CHANGELOG.md', 'NOTICE.md', 'README.md', 'rename_product.py'}
pairs = [(b'FIELDES', b'FIELDEV'), (b'FielDes', b'FielDev'), (b'fielDes', b'fieldev'), (b'fieldes', b'fieldev')]
files = [f for f in subprocess.run(['git', 'ls-files', '-z'], capture_output=True).stdout.split(b'\0') if f]
changed = {}
for raw in files:
    f = raw.decode()
    base = os.path.basename(f)
    if base in skip_names or base.startswith('LICENSE') or not os.path.isfile(f):
        continue
    data = open(f, 'rb').read()
    if b'\0' in data:
        continue
    new, n = data, 0
    for a, b in pairs:
        n += new.count(a)
        new = new.replace(a, b)
    if n:
        changed[f] = n
        if not dry:
            open(f, 'wb').write(new)
top = {}
for f, n in changed.items():
    top[f.split('/')[0]] = top.get(f.split('/')[0], 0) + n
print('%d files, %d replacements%s' % (len(changed), sum(changed.values()), ' (dry run)' if dry else ''))
print(sorted(top.items(), key=lambda x: -x[1]))
for a, b in [('app/deploy/icon/fieldes.png', 'app/deploy/icon/fieldev.png'),
             ('app/deploy/windows/fieldes.ico', 'app/deploy/windows/fieldev.ico'),
             ('app/include/fieldes', 'app/include/fieldev'),
             ('python/fieldes', 'python/fieldev'),
             ('scripts/fieldes.cmd', 'scripts/fieldev.cmd')]:
    print('git mv', a, b)
    if not dry:
        subprocess.run(['git', 'mv', a, b], check=True)
left = subprocess.run("grep -rIlE 'FielDes|fieldes|FIELDES' . --exclude-dir=.git", shell=True, capture_output=True, text=True).stdout.split()
print('files that still carry the old name:', left)
