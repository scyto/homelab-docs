"""Build the changelog page's two tables from changelog/.

changelog/publishes.yml is written by hand: one entry per publish, newest first,
listing what it added, changed, removed or fixed. changelog/history.json is
written by the private repo's tools/changelog.py: when each earlier publish went
live, and how many pull requests merged there each day.

The newest entry is `publish: next` until the publish after it is prepared. The
live build reads every publish from git, gives `next` to the first one without
an entry, and fills in its time and pull request, so the page is right the
moment it goes live. A publish with no entry at all still gets a row, saying so.
Anywhere else, `next` shows as pending.
"""
import collections
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import zoneinfo

import yaml
from mkdocs.exceptions import PluginError

PAGE = "changelog.md"
PUBLISHES, PACE = "<!-- changelog:publishes -->", "<!-- changelog:pace -->"
REPO = "scyto/homelab-docs"
PACIFIC = zoneinfo.ZoneInfo("America/Los_Angeles")
LABELS = [f"{verb} {thing}" for thing in ("doc", "feature") for verb in ("added", "changed", "removed")] + ["fix"]
WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def on_page_markdown(markdown, page, config, **kwargs):
    if page.file.src_uri != PAGE:
        return markdown
    site = pathlib.Path(config.config_file_path).parent
    entries = yaml.safe_load((site / "changelog/publishes.yml").read_text())
    history = json.loads((site / "changelog/history.json").read_text())
    published = live_publishes(site) or [(p["id"], pacific(p["time"]), p["link"]) for p in history["publishes"]]
    times = {key: (when, link) for key, when, link in published}
    described = {str(e["publish"]) for e in entries}
    # Oldest first: the `next` entry belongs to the first publish after the
    # ones already described, and anything after that has no entry yet.
    undescribed = [key for key, _, _ in reversed(published) if key not in described]
    rows = []
    for entry in entries:
        key = str(entry["publish"])
        if key == "next":
            if not undescribed:
                rows.append((None, "pending", "this publish", entry["changes"]))
                continue
            key = undescribed.pop(0)
        if key not in times:
            raise PluginError(f"changelog: publish {key} is not in history.json; run tools/changelog.py")
        rows.append(row(key, times[key], entry["changes"]))
    rows += [row(key, times[key], None) for key in undescribed]
    # newest first, with a pending `next` above them all
    rows.sort(key=lambda r: (r[0] is None, r[0] or dt.datetime.min.replace(tzinfo=PACIFIC)), reverse=True)
    for marker in (PUBLISHES, PACE):
        if markdown.count(marker) != 1:
            raise PluginError(f"changelog: {PAGE} needs {marker} exactly once")
    markdown = markdown.replace(PUBLISHES, publishes_table([r[1:] for r in rows]))
    return markdown.replace(PACE, pace([when for when, _ in times.values()], history["changes_by_day"]))


def row(key, time_and_link, changes):
    when, link = time_and_link
    label = f"#{key}" if key.isdigit() else key
    return when, f"{when:%Y-%m-%d %H:%M}", f"[{label}]({link})", changes


def live_publishes(site):
    """Every publish, newest first, from git, on the build that deploys the site; None anywhere else.

    Every commit on homelab-docs main is a publish, and the workflow checks out
    the whole history, so this is complete even if something merged there that
    did not come from staging.
    """
    if (os.environ.get("GITHUB_REPOSITORY") != REPO or os.environ.get("GITHUB_REF") != "refs/heads/main"
            or os.environ.get("GITHUB_EVENT_NAME") == "pull_request"):
        return None
    log = subprocess.run(["git", "log", "--first-parent", "--format=%H%x1f%cI%x1f%s"],
                         cwd=site, check=True, capture_output=True, text=True).stdout
    out = []
    for line in log.splitlines():
        sha, committed, subject = line.split("\x1f")
        number = re.search(r"\(#(\d+)\)$", subject)
        key = number.group(1) if number else sha[:7]
        link = f"https://github.com/{REPO}/pull/{key}" if number else f"https://github.com/{REPO}/commit/{key}"
        out.append((key, pacific(committed), link))
    return out


def publishes_table(rows):
    lines = ["| when | publish | kind | what changed |", "| --- | --- | --- | --- |"]
    for when, publish, changes in rows:
        if changes is None:
            lines.append(f"| {when} | {publish} | | <ul><li>no entry was written for this publish</li></ul> |")
            continue
        items = []
        kinds = set()
        for change in changes:
            (label, text), = change.items()
            if label not in LABELS:
                raise PluginError(f"changelog: unknown label {label!r}; use one of {', '.join(LABELS)}")
            kinds.add("fixes" if label == "fix" else "features" if label.endswith("feature") else "docs")
            items.append(f"<li>**{label}:** {text.replace('|', '&#124;')}</li>")
        kind = " + ".join(["docs"] + [k for k in ("features", "fixes") if k in kinds])
        lines.append(f"| {when} | {publish} | {kind} | <ul>{''.join(items)}</ul> |")
    return "\n".join(lines)


def pace(publishes, changes_by_day):
    publishes = sorted(publishes)
    first, latest = publishes[0], publishes[-1]
    days = (latest.date() - first.date()).days + 1
    by_day = collections.Counter(p.date() for p in publishes)
    busiest = by_day.most_common(1)[0]
    changes = {dt.date.fromisoformat(day): counts for day, counts in changes_by_day.items()}
    docs = sum(c["docs"] for c in changes.values())
    other = sum(c["other"] for c in changes.values())
    busiest_changes = max(changes.items(), key=lambda item: (item[1]["docs"] + item[1]["other"], item[0]))

    def monday(day):
        return day - dt.timedelta(days=day.weekday())

    weeks = collections.defaultdict(lambda: [0, 0, 0])
    for p in publishes:
        weeks[monday(p.date())][0] += 1
    for day, counts in changes.items():
        weeks[monday(day)][1] += counts["docs"]
        weeks[monday(day)][2] += counts["other"]
    lines = [
        f"- {len(publishes)} publishes in {days} days, from {first:%Y-%m-%d %H:%M} to {latest:%Y-%m-%d %H:%M}. "
        f"the busiest day was {busiest[0]}, with {count(busiest[1], 'publish', 'publishes')}",
        f"- {docs + other} pull requests merged in the private repo since the first publish: {docs} to the "
        f"docs, {other} to stacks, tools and CI. the busiest day was {busiest_changes[0]}, with "
        f"{sum(busiest_changes[1].values())}",
        "",
        "| week starting | publishes | docs changes | stack, tool and CI changes |",
        "| --- | --- | --- | --- |",
    ]
    week = max(weeks)
    while week >= min(weeks):
        p, d, c = weeks.get(week, (0, 0, 0))
        lines.append(f"| {week} | {p} | {d} | {c} |")
        week -= dt.timedelta(days=7)
    return "\n".join(lines)


def pacific(timestamp):
    return dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(PACIFIC)


def count(n, noun, plural):
    return f"{WORDS[n] if n < len(WORDS) else n} {noun if n == 1 else plural}"
