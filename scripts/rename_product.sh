#!/bin/bash
# The product rename FielDes -> FielDev over the tracked text files, for a machine that has Git Bash and no Python (scripts/rename_product.py does the same):
#
#     FIELDES -> FIELDEV     FielDes -> FielDev     fielDes -> fieldev     fieldes -> fieldev
#
# Left alone on purpose: CHANGELOG.md (FielDes's history), LICENSE-*, NOTICE.md and README.md (they say whose fork this is, and are edited by hand), and the two rename
# scripts.  A file with a NUL byte is binary and left alone.  Afterwards the five paths that carry the name are moved with `git mv`, and the files that still carry the
# old name are listed.
#
#     bash scripts/rename_product.sh --dry      only counts
#     bash scripts/rename_product.sh
#
# A one-time tool: `git rm scripts/rename_product.py scripts/rename_product.sh` once the rename is made.  Undone by `git reset --hard` before it is committed.
set -e
cd "$(dirname "$0")/.."
export LC_ALL=C
skip='(^|/)(CHANGELOG\.md|NOTICE\.md|README\.md|rename_product\.py|rename_product\.sh|LICENSE[^/]*)$'
names='FIELDES|FielDes|fielDes|fieldes'
list=$(mktemp)
git ls-files -z | grep -zEv "$skip" | xargs -0 -r grep -IlZE "$names" > "$list" || true
echo "$(tr -cd '\0' < "$list" | wc -c) files carry the name"
if [ "$1" != "--dry" ]; then
    xargs -0 -r sed -i -e 's/FIELDES/FIELDEV/g' -e 's/FielDes/FielDev/g' -e 's/fielDes/fieldev/g' -e 's/fieldes/fieldev/g' < "$list"
    git mv app/deploy/icon/fieldes.png app/deploy/icon/fieldev.png
    git mv app/deploy/windows/fieldes.ico app/deploy/windows/fieldev.ico
    git mv app/include/fieldes app/include/fieldev
    git mv python/fieldes python/fieldev
    git mv scripts/fieldes.cmd scripts/fieldev.cmd
    echo "rewritten, and the five paths moved"
fi
rm -f "$list"
echo "files that still carry the old name:"
git grep -lIE "$names" || true
