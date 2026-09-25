---
title: "BentoPDF"
---

# bentopdf

[bentopdf](https://github.com/alam00000/bentopdf) is a pdf toolkit: merge,
split, edit, sign, compress, convert, ocr. your browser processes the files, and
the container only serves the page. the browser needs internet access even
though your files don't leave it, because by default it loads the pdf engines
from the jsdelivr cdn. it runs as one replica, anywhere on the swarm.

--8<-- "blocks/swarm/bentopdf/compose.yml.md"

## the simple image, from upstream

i use the `bentopdf-simple` image. it's the self-hosting build: the same tools,
with the marketing pages taken out.

use the upstream repo and images linked here. the project has deprecated the
docker hub image `bentopdf/bentopdf` and no longer updates it, and some
articles link to an old copy of the repo under another account.

upstream tags a release most months, so this is a plain version pin, and
renovate opens a PR for each new one. a new major waits for approval on the
dependency dashboard first.

## no volumes

there is nothing to keep, so there are no volumes. upstream can hide tools with
a `config.json` mounted into the container at runtime. i don't use it.

## how it's reached

the container listens on 8080 (set `PORT` to change that), and i publish it
on 8091. reach it on port 8091 of any swarm node IP or the keepalived IP.

## checking it

the page it serves should carry bentopdf's title:

```
curl -s http://192.168.1.45:8091/ | grep -o '<title>[^<]*</title>'
```

```text
<title>PDF Tools</title>
```
