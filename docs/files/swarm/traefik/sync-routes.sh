#!/bin/sh
set -eu

src="./stacks/swarm/traefik/dynamic"
dst="/dynamic"

[ -d "$src" ] || { echo "config-sync: $src not found under $(pwd)" >&2; exit 1; }
[ -d "$dst" ] || { echo "config-sync: $dst is not mounted" >&2; exit 1; }

if ! ls "$src"/*.yml >/dev/null 2>&1; then
	echo "config-sync: no *.yml under $src, refusing to reconcile" >&2
	exit 1
fi

delivered=0
for f in "$src"/*.yml; do
	name="${f##*/}"
	tmp="$dst/.${name}.tmp"
	cp "$f" "$tmp"
	chmod 0644 "$tmp"
	mv "$tmp" "$dst/$name"
	delivered=$((delivered + 1))
done

removed=0
for g in "$dst"/*.yml; do
	[ -f "$g" ] || continue
	name="${g##*/}"
	[ -f "$src/$name" ] && continue
	rm -f "$g"
	removed=$((removed + 1))
	echo "config-sync: removed $name, no longer in git"
done

echo "config-sync: delivered $delivered, removed $removed, at ${GITSYNC_HASH:-unknown}"
