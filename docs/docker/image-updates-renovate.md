---
title: "image updates with renovate"
comments: true
---

# image updates with renovate

## what it is

[renovate](https://docs.renovatebot.com/) reads the compose files in git, finds images with a newer version, and opens a pull request that changes the tag and digest. it never touches a running container.

## why

- watchtower and shepherd updated running containers with nothing to review, and both are abandoned upstream now
- a tag like `latest` means any restart can change what runs
- with renovate every update is a PR: a diff and a changelog link before anything moves, and i can refuse one or revert it
- swarm services and standalone containers are handled the same way, and nothing needs the docker socket

the cost: updates are no longer automatic, i read and merge the PRs.

## how an update flows

```mermaid
flowchart LR
    A[renovate<br>weekly github action] -->|opens a PR| B[new tag and digest<br>in one compose file]
    B -->|ci passes, i merge| C[main]
    C -->|promote workflow| D[deploy/env/stack<br>moves forward]
    D -->|portainer polls, 5 min| E[that one stack<br>redeploys]
```

one PR touches one stack, so a merge redeploys that stack and nothing else, see [stacks in git](gitops-with-portainer.md).

## pin images by digest

```yaml
    image: mysql:8.0@sha256:968e12b1fde035655c7a940db808b47372b70128293a38a3914e0b291c306e5e
```

- with the digest, a restart or a node failover pulls exactly what ran before. the version only changes when a renovate PR changes this line
- renovate updates the tag and the digest together
- `pinDigests` is off in my config, so renovate won't add digests by itself. i pin a stack when i adopt it, and renovate keeps the pins current from then on
- images tracking `latest` still get a digest; their updates arrive as digest-only PRs

## set it up

your stacks need to be [in git](gitops-with-portainer.md) first.

### pre-reqs

1. compose files in a github repo
2. admin on that repo (you are adding secrets and a workflow)
3. a github account you can create an app under

i run it as a scheduled github action, **not** the mend-hosted app, because the
repo is private and i want the credentials to be mine.

### create a github app

use an app, not a PAT. a PAT carries all your own permissions everywhere, and a
fine grained one expires within a year, after which renovate stops opening PRs
with nothing failing to tell you. an app install doesn't expire.

1. github > settings > developer settings > **GitHub Apps** > New GitHub App
2. name it whatever, homepage url can be your repo
3. **uncheck webhook active**, you don't need it
4. set the repository permissions per the table below
5. create it, then **Generate a private key**, it downloads a `.pem`
6. note the **App ID** from the top of the app page
7. Install App > install it on just the one repo, not all repos

| permission | access | why |
| --- | --- | --- |
| Contents | read & write | it pushes the branch |
| Pull requests | read & write | it opens the PR |
| Issues | read & write | the dependency dashboard *is* an issue |
| Workflows | read & write | only needed if it bumps `.github/workflows` versions |

the list in the UI is alphabetical so Contents is nowhere near Pull requests, and
Workflows is right at the bottom. easy to miss one.

![the installed app, showing read and write to code, issues, pull requests and workflows, scoped to one repository](../assets/img/renovate-app-permissions.png)

### add the two secrets

repo > settings > secrets and variables > actions > New repository secret

| name | value |
| --- | --- |
| `RENOVATE_APP_ID` | the app id number |
| `RENOVATE_APP_PRIVATE_KEY` | whole contents of the `.pem`, including the BEGIN/END lines |

### add the workflow

`.github/workflows/renovate.yml`

```yaml
name: renovate

on:
  schedule:
    - cron: "23 14 * * *"       # daily
  issues:
    types: [edited]             # someone ticked a box on the dashboard
  workflow_dispatch:

concurrency:
  group: renovate
  cancel-in-progress: false

jobs:
  renovate:
    if: >-
      github.event_name != 'issues' ||
      (github.event.issue.title == 'Dependency Dashboard' &&
       github.event.sender.type == 'User')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: mint an installation token
        id: app-token
        uses: actions/create-github-app-token@v3.2.0
        with:
          app-id: ${{ secrets.RENOVATE_APP_ID }}
          private-key: ${{ secrets.RENOVATE_APP_PRIVATE_KEY }}

      - uses: renovatebot/github-action@v46.2.3
        with:
          token: ${{ steps.app-token.outputs.token }}
        env:
          RENOVATE_REPOSITORIES: ${{ github.repository }}
          RENOVATE_PLATFORM: github
          RENOVATE_BASE_BRANCHES: main
```

do **not** use the built in `GITHUB_TOKEN` here. PRs opened with it don't trigger
`pull_request` workflows, so your own validation never runs, and if main requires
those checks the renovate PRs can never be merged.

- **it runs when you tick a box.** ticking a checkbox on the dashboard edits the
  issue, and that starts a run, so the PR turns up in a couple of minutes rather
  than at the next scheduled run
- **the `if:` stops a loop.** renovate rewrites the dashboard at the end of every
  run with the app's token, and events from an app token do trigger workflows. the
  app is a `Bot` sender and you are a `User`, so only your edits start a run
- **the daily run is a safety net**, for a tick whose event got missed and to keep
  open PRs current. `renovate.json`'s schedule still decides when new update PRs
  open

### add renovate.json

in the repo root. this is a cut down version of mine.

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "timezone": "America/Los_Angeles",
  "schedule": ["* * * * 1"],
  "prConcurrentLimit": 5,
  "dependencyDashboard": true,
  "ignorePaths": ["_attic/**"],
  "commitMessageSuffix": " [{{packageFileDir}}]",
  "packageRules": [
    {
      "matchCategories": ["docker"],
      "pinDigests": false
    },
    {
      "matchUpdateTypes": ["patch"],
      "groupName": "patch updates {{packageFileDir}}"
    },
    {
      "matchUpdateTypes": ["major"],
      "dependencyDashboardApproval": true
    },
    {
      "matchPackageNames": ["adguard/adguardhome", "jc21/nginx-proxy-manager"],
      "dependencyDashboardApproval": true
    },
    {
      "matchPackageNames": ["portainer/portainer-ee", "portainer/agent"],
      "enabled": false
    }
  ]
}
```

with the layout from the [gitops page](gitops-with-portainer.md) that gives PR
titles like:

```
Update jc21/nginx-proxy-manager Docker tag to v2.12.6 [stacks/swarm/npm]
patch updates stacks/pi-zwave01/zwave-js-ui
```

which is what you want, because merging the first one moves `deploy/swarm/npm`
and nothing else.

![the open pull request list, each title carrying its stack directory](../assets/img/renovate-pr-titles.png)

what each bit is doing:

- `commitMessageSuffix` puts the stack directory in the commit subject. with
  twenty odd stacks this is the difference between a readable git log and mush
- `groupName` with `{{packageFileDir}}` gives you one PR per stack instead of one
  per image, which is a lot less noise
- `dependencyDashboardApproval` = don't open a PR, put it on the dashboard with a
  checkbox and wait for me. i use it for major bumps, anything with a database in
  it, anything home assistant has to stay compatible with, and anything thats
  bitten me before
- `enabled: false` for images you never want it to touch. portainer can't safely
  redeploy itself so it stays manual
- `ignorePaths` for junk drawers, otherwise it raises PRs for stacks you aren't
  running
- if you want a whole stack left alone rather than an image, match the directory
  instead:

  ```json
  {
    "matchFileNames": ["stacks/pi-zwave01/zigbee2mqtt/**"],
    "enabled": false
  }
  ```

### run it

don't wait until monday, run it by hand first

repo > Actions > renovate > Run workflow

first run it opens an issue called **Dependency Dashboard** listing everything it
found, plus whatever PRs it is allowed to open.

![the dependency dashboard issue, pending approval items with two ticked](../assets/img/renovate-dependency-dashboard.png)

![a renovate pull request, release notes, the config it used, and a green check](../assets/img/renovate-pull-request.png)

tick a checkbox on the dashboard and a run starts, and the PR appears a couple of
minutes later. a tick overrides the schedule, so this works any day of the week.

thats it. merge a PR and your normal deploy path does the rest.

### lock the branches down, last

do this **after** renovate has opened its first PR, not before. you cannot
require a status check until a run has reported one, and the name has to match
exactly.

on `main`:

| rule | why |
| --- | --- |
| require a pull request before merging | otherwise renovate's whole point is optional |
| require status checks, tick your validate job | this is the gate |
| block force pushes | keeps history honest |

the check name in the ruleset is the **job `name:`** from your workflow, not the
file name and not the workflow name. rename the job later and every PR sits there
forever waiting on a check that never reports, with nothing failing to tell you
why. change both together or not at all.

on `deploy/*`, block force pushes so a deploy branch can only move forward. mind
the `**` trap covered on the [gitops page](gitops-with-portainer.md), a ruleset
targeting `refs/heads/deploy/**` matches nothing and shows as active while
enforcing nothing.

do not add renovate's app to any bypass list. the point is that its PRs go
through the same gate as yours.

rolling one back once its merged is a revert on `main`, promoted forward, see
[rolling back a compose](gitops-with-portainer.md#7-rolling-back-a-compose).

## notes

- if renovate dies with `FORBIDDEN` mentioning `["repository","issues"]` you
  missed the Issues permission, the dashboard is an issue
- if it does all your compose files fine and then fails only on a
  `.github/workflows` bump, thats the Workflows permission
- the dashboard issue regenerates, closing it does nothing, don't bother tidying it
- **give the schedule a whole day, not an hour.** github starts scheduled workflows
  late, often by hours, so a monday cron meant for 5am ran at 10 or 11 and missed a
  `before 6am on monday` window every week. nothing fails, new updates just sit in
  **Awaiting Schedule**. `* * * * 1` is all of monday in your `timezone`. use cron
  syntax, renovate's text syntax is deprecated
- the dashboard doesn't say which host a stack is on, only the directory, so name
  your directories usefully
- **check your actions minutes.** my validation workflow was burning ~300 minutes
  a day which on a private repo is real money. billing rounds **each job** up to
  a whole minute, so five jobs finishing in nine seconds each bill as five
  minutes not one. i collapsed mine into a single job and it went from ~5 billed
  minutes a run to 1. the actual work takes under twenty seconds
