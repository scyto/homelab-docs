#!/usr/bin/env python3
"""Check every hand-typed config fragment on a page against the published file.

    python3 tools/fragcheck.py [--site <dir holding mkdocs.yml>]

The published stack files are the copies in docs/files/<env>/<stack>/, the
same ones a reader downloads, so a fragment is compared with exactly what a
reader can open. It needs nothing else, so it runs in CI before the build.

A page shows a stack's files by including its generated blocks
(--8<-- "blocks/<env>/<stack>/<path>.md"). On such a page:

- every yaml, yml, css or ini fence must carry title="<path>", naming a
  published file of the page's own stack (compose.yml, config/services.yaml),
  or of another stack as <stack>/<path> (arrstack/compose.yml), or
  <env>/<stack>/<path> where two environments have a stack of that name,
  unless the line above it is <!-- fragment: illustrative -->
- a fence with a title that names no published file fails

On any page, a titled fence that names a published file is checked against it:

- YAML: parsed, and it must be a structural subset of some node of the file:
  keys it shows exist with the same value, list items it shows are present in
  the same order. Keys and items may be left out, flow style matches block
  style, <placeholder> in a value matches any text, and trailing spaces and
  final newlines, which a reader cannot see, are ignored
- CSS: comments and whitespace removed on both sides, then a substring
- anything else: its non-blank lines, whitespace collapsed, as one run of the
  file's lines
- a fragment never quotes an image digest: a Renovate bump would break it

Output and logs are `text` fences, and are not checked. It cannot catch an
addition: prose saying "all four devices" after a fifth is added still passes,
so re-read the prose around a fragment when its file changes.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import textwrap

import yaml

FENCE_OPEN = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>[^\n`]*)$")
TITLE = re.compile(r'''title=(["'])(?P<t>.*?)\1''')
# the language of a fence: `yaml title=...` or `{ .yaml .annotate ... }`
LANG = re.compile(r"^\s*(?:\{\s*\.(?P<braced>[\w+-]+)|(?P<bare>[\w+-]+)(?=\s|$))")
INCLUDE = re.compile(r'--8<--\s+"blocks/(?P<env>[^/"]+)/(?P<stack>[^/"]+)/[^"]+\.md"')
# <you>, <uuid>, or a spaced one like <server version>: starts with a letter,
# words of letters, digits and _ . / : - with single spaces between, up to 40
# characters, so an operator span such as `< 300 && echo ok >` is never one
PLACEHOLDER = re.compile(r"<(?=[^<>\n]{1,40}>)[A-Za-z][\w./:-]*(?: [\w./:-]+)*>")
ILLUSTRATIVE = "<!-- fragment: illustrative -->"
CONFIG_LANGS = {"yaml", "yml", "css", "ini"}


def fences(text: str):
    """Yield (line_no, info, body, line_above) for each fenced block."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        indent, fence, info = m.group("indent"), m.group("fence"), m.group("info")
        body, j = [], i + 1
        while j < len(lines) and lines[j].rstrip() != indent + fence:
            body.append(lines[j][len(indent):] if lines[j].startswith(indent) else lines[j])
            j += 1
        above = next((l.strip() for l in reversed(lines[:i]) if l.strip()), "")
        yield i + 1, info, "\n".join(body), above
        i = j + 1


def fence_lang(info: str) -> str:
    m = LANG.match(info)
    return ((m.group("braced") or m.group("bare")) if m else "").lower()


def invisible_trimmed(s: str) -> str:
    """Drop what a reader cannot see: trailing spaces on each line, and trailing newlines."""
    return "\n".join(line.rstrip() for line in s.rstrip("\n").split("\n"))


def scalar_matches(frag, target) -> bool:
    if isinstance(frag, str) and PLACEHOLDER.search(frag):
        rx = ".+?".join(re.escape(p) for p in PLACEHOLDER.split(invisible_trimmed(frag)))
        return (isinstance(target, (str, int, float))
                and re.fullmatch(rx, invisible_trimmed(str(target)), re.S) is not None)
    if isinstance(frag, str) and isinstance(target, str):
        return invisible_trimmed(frag) == invisible_trimmed(target)
    return frag == target


def matches(frag, target) -> bool:
    if isinstance(frag, dict):
        return isinstance(target, dict) and all(k in target and matches(v, target[k]) for k, v in frag.items())
    if isinstance(frag, list):
        if not isinstance(target, list):
            return False
        j = 0
        for item in frag:
            while j < len(target) and not matches(item, target[j]):
                j += 1
            if j == len(target):
                return False
            j += 1
        return True
    return scalar_matches(frag, target)


def nodes(tree):
    yield tree
    kids = tree.values() if isinstance(tree, dict) else tree if isinstance(tree, list) else []
    for k in kids:
        yield from nodes(k)


def check_yaml(body: str, file_text: str) -> str | None:
    try:
        # the fence body has no final newline, and without one a block scalar
        # that ends the fragment loses the newline its copy in the file keeps
        frag = yaml.safe_load(textwrap.dedent(body) + "\n")
    except yaml.YAMLError as e:
        return f"does not parse as YAML: {getattr(e, 'problem', e)}"
    tree = yaml.safe_load(file_text)
    if any(matches(frag, n) for n in nodes(tree)):
        return None
    if isinstance(frag, dict):
        missing = [k for k in frag if not any(isinstance(n, dict) and k in n for n in nodes(tree))]
        if missing:
            return "not in the file: " + ", ".join(f"`{k}`" for k in missing)
    return "no node of the file holds these keys and values, with list items in this order"


def norm_lines(text: str) -> list[str]:
    return [" ".join(l.split()) for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]


def check_text(body: str, file_text: str) -> str | None:
    frag, file = norm_lines(body), norm_lines(file_text)
    n = len(frag)
    if any(file[i:i + n] == frag for i in range(len(file) - n + 1)):
        return None
    missing = [l for l in frag if l not in file]
    return f"line not in the file: `{missing[0]}`" if missing else "lines are in the file but not together, in this order"


def check_css(body: str, file_text: str) -> str | None:
    def squash(s):
        return re.sub(r"\s+", "", re.sub(r"/\*.*?\*/", "", s, flags=re.S))
    return None if squash(body) in squash(file_text) else "rule text not in the file"


def published_files(files_root: pathlib.Path) -> dict[str, set[str]]:
    """env/stack -> the paths published for it, as a page's title= names them."""
    out: dict[str, set[str]] = {}
    if files_root.is_dir():
        for p in files_root.rglob("*"):
            if p.is_file():
                parts = p.relative_to(files_root).parts
                if len(parts) >= 3:
                    out.setdefault("/".join(parts[:2]), set()).add("/".join(parts[2:]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--site", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent.parent,
                    help="the directory holding mkdocs.yml and docs/ (default: this script's parent's)")
    args = ap.parse_args()
    docs = args.site / "docs"
    files_root = docs / "files"
    published = published_files(files_root)
    by_name: dict[str, list[str]] = {}
    for env_stack in published:
        by_name.setdefault(env_stack.split("/")[1], []).append(env_stack)

    def resolve(title: str, own: set[str]) -> tuple[pathlib.Path | None, str]:
        """(file, why not): the file a title names, from the page's own stacks first."""
        hits = [s for s in sorted(own) if title in published.get(s, set())]
        if len(hits) == 1:
            return files_root / hits[0] / title, ""
        if len(hits) > 1:
            return None, f"is in {' and '.join(hits)}; name one as <stack>/{title}"
        parts = title.split("/")
        if len(parts) >= 3:                                   # <env>/<stack>/<path>
            env_stack, rest = "/".join(parts[:2]), "/".join(parts[2:])
            if rest in published.get(env_stack, set()):
                return files_root / env_stack / rest, ""
        if len(parts) >= 2:                                   # <stack>/<path>
            head, rest = parts[0], "/".join(parts[1:])
            stacks = [s for s in by_name.get(head, []) if rest in published[s]]
            if len(stacks) == 1:
                return files_root / stacks[0] / rest, ""
            if len(stacks) > 1:
                return None, f"{head} is a stack in {len(stacks)} environments; write <env>/{title}"
        return None, "names no published file"

    failures = checked = 0
    for page in sorted(docs.rglob("*.md")):
        text = page.read_text()
        own = {f"{m.group('env')}/{m.group('stack')}" for m in INCLUDE.finditer(text)}
        shown = False
        for line_no, info, body, above in fences(text):
            if above == ILLUSTRATIVE or "--8<--" in body:
                continue
            lang = fence_lang(info)
            t = TITLE.search(info)
            if not t:
                if own and lang in CONFIG_LANGS:
                    if not shown:
                        print(page.relative_to(docs))
                        shown = True
                    print(f"  FAIL line {line_no}: a {lang} fragment with no title=; name its file,"
                          f" or mark it {ILLUSTRATIVE}")
                    failures += 1
                continue
            title = t.group("t")
            target, why_not = resolve(title, own)
            if target is None and not own:
                continue            # a titled fence on a page that shows no stack's files
            if not shown:
                print(page.relative_to(docs))
                shown = True
            checked += 1
            if target is None:
                print(f"  FAIL line {line_no}: title=\"{title}\" {why_not}")
                failures += 1
                continue
            if "@sha256:" in body:
                print(f"  FAIL line {line_no}: quotes an image digest; write <tag>")
                failures += 1
                continue
            file_text = target.read_text()
            if lang in ("yaml", "yml") or target.suffix in (".yml", ".yaml"):
                why = check_yaml(body, file_text)
            elif lang == "css" or target.suffix == ".css":
                why = check_css(body, file_text)
            else:
                why = check_text(body, file_text)
            rel = target.relative_to(files_root)
            if why:
                print(f"  FAIL line {line_no}: {title} -> {rel}: {why}")
                failures += 1
            else:
                print(f"  ok   line {line_no}: {title} -> {rel}")
    print(f"\n{checked} titled fragment(s) checked, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
