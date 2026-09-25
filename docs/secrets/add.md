---
title: "Add a Secret"
---

# Add a secret

Give a stack a new credential: reference it in the compose file, put the value
in the encrypted store, create it in Swarm, and deploy.

Every step uses one made-up example from start to finish. Where you see the
example's names, use your own. Background and reasons are in
[BACKGROUND.md](background.md).

## The example

A Swarm stack called `example_app` logs in to another system, `example-portal`,
with a service account. You choose that account's password, set it in
`example-portal`'s web UI, and `example_app` reads it from a Swarm secret.

| Thing | Name in the example |
| --- | --- |
| stack directory | `stacks/swarm/example_app/` |
| compose file | `stacks/swarm/example_app/compose.yml` |
| service | `app` |
| secret, as you first write it | `example_app_portal_password` |
| secret, once `add` has versioned it | `example_app_portal_password_v1` |
| your PR branch | `stacks/example-app-portal-password` |
| the PR | `#123` |
| the branch Portainer deploys | `deploy/swarm/example_app` |

## Before you start

- **The `keyman` alias** is set up on your workstation. See
  [README.md, one-time setup](index.md#one-time-setup-the-keyman-alias).
  It runs the container on a Swarm manager because `provision` and `verify`
  need that node's Docker socket. **Nothing else in this guide does**, so for a
  stack outside `stacks/swarm/` the container can run anywhere Docker runs,
  including your workstation -- see
  [KEY-MANAGER.md, three ways to run it](key-manager.md#three-ways-to-run-it).
  Without a Swarm socket the wrapper warns that Swarm commands will fail, which
  is correct and harmless when you are not running any. The one exception is
  step 6b's second container, which runs on the host that holds the file.
- **Key operations run only in the key-manager container.** Never run `sops`,
  `age` or `secretstore.py` on a workstation, a VM or a node.
- **Most of this applies anywhere; step 6 does not.** `provision` and `verify`
  are Swarm-only, because `docker secret create` has no standalone equivalent.
  For a secret that nothing mounts as a Swarm secret, follow steps 1 to 5, then
  [step 6b](#6b-a-secret-that-is-not-a-swarm-secret-in-the-container) instead
  of step 6. That is every stack outside `stacks/swarm/`, and a Swarm stack
  that reads the value from a file it names. `add` says which at the end of
  step 5. Background on one value in several environments is in
  [BACKGROUND.md](background.md#one-secret-several-environments).

## How the branches fit together

```text
main                                       reviewed history. Nothing deploys from it.
 |
 +-- stacks/example-app-portal-password     your PR branch. It carries BOTH changes:
 |                                            compose.yml references the secret   (step 1, workstation)
 |                                            secrets.enc.yaml holds the value    (step 7, container)
 |
 +-> deploy/swarm/example_app               what Portainer polls. promote.yml moves it
                                              forward when the PR merges          (step 8)
```

You work on that one PR branch from **two copies of the repo**, and they meet on
GitHub:

| Copy | Where it is | Steps done there |
| --- | --- | --- |
| your clone | your workstation, `~/repos/homelab-stacks` | 1 and 8: edit `compose.yml`, open and merge the PR |
| `/repo` | inside the key-manager container, cloned fresh each session | 3 to 7: everything that touches the value |

The container's clone **starts on `main`**. Step 3 switches it to
`stacks/example-app-portal-password`. That is what makes step 7's push land on
your PR.

## 1. Prepare the PR branch (on your workstation)

**1.1** Start from an up-to-date `main` and create the branch:

```bash
cd ~/repos/homelab-stacks
git checkout main
git pull --ff-only
git checkout -b stacks/example-app-portal-password
```

**1.2** In `stacks/swarm/example_app/compose.yml`, reference the secret by its
base name, with no `_v1`:

```yaml
services:
  app:
    image: example/app:1.0
    environment:
      PORTAL_PASSWORD_FILE: /run/secrets/example_app_portal_password
    secrets:
      - example_app_portal_password

secrets:
  example_app_portal_password:
    external: true
```

**1.3** Commit and push:

```bash
git add stacks/swarm/example_app/compose.yml
git commit -m "example_app: read the example-portal password from a swarm secret"
git push -u origin stacks/example-app-portal-password
```

**1.4** Open a draft PR. It prints the PR's URL; the number at the end is the
one step 8 uses, `123` here:

```bash
gh pr create --draft --fill
```

**1.5** Only if you are reusing a branch created before the latest `main`, bring
it up to date:

```bash
gh pr update-branch 123 --rebase
```

> **Why compose first:** in step 5, `add` finds `example_app_portal_password` in
> this file and renames every mention to `example_app_portal_password_v1` itself.
>
> **Why 1.5:** the container runs `tools/secretstore.py` from the branch it has
> checked out, not from the image. An old branch runs the old tool.
> `--rebase` rebuilds the branch's commits on GitHub, so the copies in your
> clone no longer match them. That is why 8.1 pulls with `--rebase`.
>
> **Which way the container reads the secret** (the `_FILE` variable above, an
> entrypoint wrapper, and so on) depends on the image. Check it before writing
> 1.2: [BACKGROUND.md, delivering a secret](background.md#delivering-a-secret-to-the-container).
>
> **If a script reads the secret instead of the app,** mount it at a fixed file
> name and point the script there. `add` and `rotate` edit compose files, never
> scripts:
>
> ```yaml
>     secrets:
>       - source: example_app_portal_password
>         target: portal_password         # the script reads /run/secrets/portal_password
> ```
>
> Do not write that `/run/secrets/portal_password` path anywhere else in the
> compose file. key-manager reads every `/run/secrets/<x>` in a compose file as a
> secret name.

## 2. Start the container (on your workstation)

**2.1** Run:

```bash
keyman
```

**2.2** At `No repo in /repo. Sign in to GitHub and clone it now? [Y/n]`, press
**Enter**.

**2.3** At `Press Enter to open https://github.com/login/device`, open that URL
in your browser, enter the code it printed, and approve.

**2.4** Wait for the prompt `root@<container id>:/repo#`. Steps 3 to 7 are all
typed at that prompt.

> "Failed opening a web browser" and "Authentication credentials saved in plain
> text" are both expected in a container. The token is in memory and goes when
> the container exits.

## 3. Put the container on your branch (in the container)

**3.1** Check out the PR branch:

```
git checkout stacks/example-app-portal-password
```

It prints `branch 'stacks/example-app-portal-password' set up to track
'origin/stacks/example-app-portal-password'`.

**3.2** Pull, **every time**, even on a branch you checked out minutes ago:

```
git pull --rebase
```

> **Why this is a step and not an afterthought.** The branch moves under you.
> Someone else -- or an agent working the same PR -- pushes a review fix while
> you are partway through `add`, and the first you hear of it is
> `! [rejected] ... (fetch first)` **after** the value is already recorded and
> backed up. The store edit is then stranded on a local commit, which is
> recoverable but alarming at exactly the wrong moment.
>
> `--rebase` specifically: without it, a diverged branch stops with
> `fatal: Need to specify how to reconcile divergent branches`, because the
> container has no `pull.rebase` preference set.

**3.3** Confirm it has your commit from step 1.3:

```
git log --oneline -1
```

**3.4** Sign in to Key Vault. Open the URL it prints, enter the code, and sign
in with your account in the tenant it names:

```
az-login
```

> **Do this before any command that touches the store, not just before `add`.**
> The store is encrypted with an age identity that is not in the container: it
> is fetched from Key Vault on demand.
>
> **`check` is the only exception.** It compares compose references against
> secret *names*, which are plaintext in the store file, so it needs no key --
> which is why CI runs it with nothing. `clone` and `gh-login` do not read the
> store at all.
>
> Everything else needs this, including the ones that look read-only:
> `list`, `diff`, `status`, `verify`, `retire`, `feed`, `add`, `provision`,
> `rotate`, `backup`, `restore` and `akv-get`. Rather than trusting that list
> to stay current, the rule is: **if it reads or writes a value, sign in
> first.**
>
> **A command that appears to hang is usually this.** On 2026-09-20 a `feed`
> sat silent until Ctrl-C because the device-code prompt had been printed
> where nobody could see it: `akv-get` writes the age identity to stdout, so
> the prompt goes to stderr, and when sops runs `akv-get` as a subprocess that
> stderr does not reach the terminal. The prompt now goes to `/dev/tty` first,
> which redirection cannot swallow, so this should not recur -- but if a
> command ever goes quiet, run `az-login` and try again before assuming worse.

**3.5** Confirm the store decrypts. It prints names, lengths and digests, never
values:

```
list
```

> **If 3.4 loops** (an account picker, then the code prompt again), use a private
> browser window and type the account name in.

## 4. Get the value (in the container)

**4.1** Generate the password:

```
python3 - <<'GENPW'
import secrets, string
sym = "!#%*+-=?@^_~"
alphabet = string.ascii_letters + string.digits + sym
length = 32
while True:
    p = "".join(secrets.choice(alphabet) for _ in range(length))
    if (any(c.islower() for c in p) and any(c.isupper() for c in p)
            and any(c.isdigit() for c in p) and any(c in sym for c in p)):
        break
# Shown on the terminal's alternate screen, which is not kept in scrollback,
# and written to /dev/tty rather than stdout, so a pipe or redirect never gets it.
with open("/dev/tty", "w") as out, open("/dev/tty") as keys:
    out.write("\033[?1049h\033[H")
    out.write("Copy this value, then press Enter to clear it:\n\n" + p + "\n")
    out.flush()
    keys.readline()
    out.write("\033[?1049l")
    out.flush()
GENPW
```

**4.2** Copy the value shown on screen, then press **Enter**. The screen clears.

**4.3** In `example-portal`'s web UI, set it as the password of `example_app`'s
service account.

**4.4** Keep it on your clipboard for step 5.

> **If a provider issues the value** (a token from a vendor's console), skip 4.1
> to 4.3: create it there and copy it.
>
> **If nothing outside the stack uses the value,** do 4.1 and 4.2 and skip 4.3.
> `rotate` cannot create a brand-new secret, so the first value comes from here.
>
> **Why the screen clears:** the value is written to `/dev/tty` on the
> terminal's alternate screen, the one `less` uses, so it is not kept in
> scrollback and a pipe never receives it. A recorded session still captures it,
> and the clipboard holds it until you copy something else.
>
> **The value:** 32 characters from 74 possible, about 198 bits. It leaves out
> `"`, `\`, `'`, `` ` ``, `$` and space, which break JSON, shells or URL encoding.
> If the other system caps password length, change `length`.

## 5. Record it in the store (in the container)

**5.1** Run:

```
add example_app_portal_password --apply
```

**5.2** Answer the prompts, in the order they appear:

| Step | Prompt | Answer for the example |
| --- | --- | --- |
| 5.2.1 | `Record it as example_app_portal_password_v1 and repoint them? [Y/n]` | **Y** |
| 5.2.2 | `Paste the value, then press Ctrl-D. Each character shows as *.` | paste **once**, check you see 32 `*`, press **Ctrl-D** |
| 5.2.3 | `Can rotate replace it on its own? [Y/n]` | **n** |
| 5.2.4 | `why (one line):` | `set by hand in the example-portal web UI; change it there first` |
| 5.2.5 | `Longest value the consuming service accepts? [enter = no limit]` | **Enter** |
| 5.2.6 | `Does anything ELSE store this value -- a database, an appliance? [y/N]` | **n** |
| 5.2.7 | `Note (why this exists), or enter:` | `example_app service account on example-portal` |

After 5.2.2 it prints `received 32 characters`. Backspace works while pasting.

**5.3** Check the stored length is 32:

```
list | grep example_app_portal_password
```

> **Why n at 5.2.3:** `example-portal` also has to know the value. **n** records
> `generated: false`, so `rotate` never mints a password `example-portal` doesn't
> know.
> Answer **Y** only when nothing outside the stack holds the value.
>
> **Why n at 5.2.6:** that question is for a value a command can push to where
> it is stored, like a database `ALTER USER`. See
> [ROTATE.md, case C](rotate.md#case-c-a-database-holds-one-copy).

## 6. Create it in Swarm, verify it, back it up (in the container)

**6.1** Create the Swarm secret. It prints `created example_app_portal_password_v1`:

```
provision --only example_app_portal_password_v1 --apply
```

**6.2** Check Swarm and the store agree. It prints `MATCH`:

```
verify --only example_app_portal_password_v1
```

**6.3** Push the secret and the store to Key Vault. It prints
`pushed example-app-portal-password-v1` and `pushed sops-store`:

```
backup --apply
```

> Without `--apply` each command is a dry run. `--only` stops `provision`
> creating every other secret Swarm happens to lack.
>
> **`MATCH` does not mean the value is right,** only that Swarm and the store
> agree. A value pasted twice matches itself. Step 5.3's length check is what
> catches that.
>
> `backup` also prints `identity skipped: no local key file`. That is expected:
> the vault already holds the identity that decrypted the store.

## 6b. A secret that is not a Swarm secret (in the container)

Do this **instead of step 6** when `add` printed `No provision step`: nothing
mounts the secret as a Swarm secret. That is every stack outside
`stacks/swarm/` -- `stacks/truenas1/`, `stacks/syn02/`, `stacks/pi-zwave01/` --
and a Swarm stack that reads the value from a file it names, the way Homepage
reads its widget keys.

The commands below suppose `example_app` ran on truenas1 instead, with its
compose file binding `/mnt/fast/configs/example_app/portal_password` over the
path the app reads.

**6b.1** Push the secret and the store to Key Vault:

```
backup --apply
```

**6b.2** Confirm the vault matches the store. It ends `N/N match`:

```
backup --verify
```

**6b.3** Confirm the store can still rebuild production:

```
check
```

**6b.4** Leave this container open for step 7. In a second terminal on your
workstation, start another one on the host that holds the file, with the file's
directory bound in at `/out`:

```bash
ssh -t truenas1 'sudo docker pull -q ghcr.io/scyto/key-manager:latest && sudo docker run --rm -it -v /mnt/fast/configs/example_app:/out --dns-search mydomain.com -e AKV_VAULT=YourKeyVaultName -e AKV_TENANT=00000000-0000-0000-0000-000000000000 ghcr.io/scyto/key-manager:latest'
```

**6b.5** At `No repo in /repo. Sign in to GitHub and clone it now? [Y/n]`, type
**n**. Sign in to Key Vault, and fetch the store that 6b.1 pushed there:

```
az-login
restore
```

**6b.6** Write the value into the file. It prints `command exited 0`:

```
feed example_app_portal_password_v1 --template '{value}' --apply -- sh -c 'umask 077; cat > /out/portal_password'
```

**6b.7** Check the file without reading it. Expect `-rw-------`, owner `root`,
and a size of `32`, the length `add` reported:

```
ls -l /out/portal_password
```

**6b.8** Leave this container, and go back to the first one for step 7:

```
exit
```

> **There is no `provision` step and no `verify` step.** `docker secret create`
> is Swarm-only, so there is nothing to create and nothing for `verify` to
> compare against. `add` says so itself: with nothing on the Swarm it prints
> `Next: backup --apply` rather than `provision --apply`, and names the
> environments `provision` cannot reach.
>
> **Why a second container:** `feed` hands the value to a command inside its
> own container. The one from step 2 has no directory of that host mounted and
> no ssh credentials to reach it, so it cannot write the file. Started on the
> host with the directory bound in, `feed` writes the file directly.
>
> **Why `restore`:** the store change reaches git only in step 7, but 6b.1 has
> already put it in Key Vault, so this container needs no GitHub sign-in.
>
> - `--template '{value}'` writes the raw value, with no newline after it.
> - `umask 077` makes the file mode 600. If the app does not run as root,
>   `chown` the file to the uid it runs as, or it cannot read it.
> - `command exited 0` does not prove the file was written: a command that
>   ignores its input exits 0 too. The size in 6b.7 does.
> - The file must exist before the stack deploys. **A bind source that does not
>   exist becomes a directory**, and the app reads a directory as its secret.
>
> **A Portainer environment variable** (mechanism 5) has no file. Skip 6b.4 to
> 6b.8, and set the value as a stack variable in Portainer instead.
>
> **Mechanism 5 also needs an `x-secrets` block** in the compose file, added in
> step 1, or `check` cannot connect the `${VAR}` to a stored value. See
> [BACKGROUND.md, mechanism 5](background.md#5-portainer-environment-variable).
> `add` repoints that mapping to `_v1` along with everything else.
>
> **gitleaks may reject the mapping line.** `SOME_API_KEY: some_name_v1` reads
> as a credential assignment, and the `_v1` suffix is often what crosses its
> entropy threshold -- the unsuffixed name can pass while the versioned one
> fails. Exempt the single line with a trailing `# gitleaks:allow` rather than
> widening `.gitleaks.toml`. **CI scans commits, not the final tree,** so the
> marker has to be in the same commit that introduces the value; adding it
> afterwards does not clear the earlier commit.

## 7. Commit and push (in the container)

**7.1** Check what changed. You should see exactly two files:

```
git status --short
```

```text
 M secrets/secrets.enc.yaml
 M stacks/swarm/example_app/compose.yml
```

**7.2** Commit and push both. **Pull again first** -- step 3.2 was possibly a
while ago, and the whole point is that the branch moves:

```
git add -A
git commit -m "secrets: example_app example-portal password"
git pull --rebase
git push
```

> A rejected push here is not a lost value: the store edit is committed
> locally and `backup --apply` has already made it durable in Key Vault. Pull
> and push again. But the alarm it causes is avoidable, which is the point of
> pulling first.

**7.3** Leave the container:

```
exit
```

> `compose.yml` changed because 5.2.1 renamed the secret to
> `example_app_portal_password_v1`. The push lands on
> `stacks/example-app-portal-password` because 3.1 set it to track that branch.

## 8. Merge and deploy (on your workstation)

**8.1** Pull the container's commit into your clone and look at it:

```bash
cd ~/repos/homelab-stacks
git checkout stacks/example-app-portal-password
git pull --rebase
git show --stat HEAD
```

**8.2** Mark the PR ready:

```bash
gh pr ready 123
```

**8.3** Merge it:

```bash
gh pr merge 123 --rebase --delete-branch
```

**8.4** Deploy. Pick the one case that fits:

- **8.4.1 `example_app` already runs from Git:** nothing to do. Within five
  minutes Portainer redeploys it from `deploy/swarm/example_app`.
- **8.4.2 `example_app` is a brand-new stack:** in Portainer, create stack
  `example_app` from `refs/heads/deploy/swarm/example_app` with compose path
  `stacks/swarm/example_app/compose.yml`, as in
  [stacks in git](../docker/gitops-with-portainer.md). If it needs a host
  device (a USB radio, a disk), confirm the device is present first.
- **8.4.3 `example_app` already runs, but not from Git:** that is a cutover, not
  this procedure. Follow
  [stacks in git, step 6](../docker/gitops-with-portainer.md#6-cut-a-stack-over)
  before creating anything.

**8.5** Check `example_app` can log in to `example-portal`, for example in
`example_app`'s logs.

> **Why `--rebase` in 8.1:** if you used 1.5, GitHub rebuilt the branch's
> commits, and your clone still has the old ones. `git pull --ff-only` then
> stops with `Not possible to fast-forward`; `--rebase` moves your copy onto the
> rebuilt branch.
>
> **Why step 6 comes before 8.3:** when a running stack's deploy branch moves,
> Portainer redeploys within five minutes. If the Swarm secret did not exist
> yet, the stack would not start.
>
> **Why 8.4.2 checks the device first:** a failed create rolls back by deploying
> again, fails the same way, and leaves no stack record.

## If the value went in wrong

For a secret that no running service uses yet, for example before step 8.3.
Every step is in the container, on `stacks/example-app-portal-password`.

**1** Remove the Swarm secret:

```
docker secret rm example_app_portal_password_v1
```

**2** Remove it from the store:

```
sops unset /repo/secrets/secrets.enc.yaml '["secrets"]["example_app_portal_password_v1"]'
```

**3** Add it again, answering as in 5.2. There is no rename question this time,
because the name already ends in `_v1`:

```
add example_app_portal_password_v1 --apply
```

**4** Check the length, then create, verify, back up and push:

```
list | grep example_app_portal_password
provision --only example_app_portal_password_v1 --apply
verify --only example_app_portal_password_v1
backup --apply
git add -A
git commit -m "secrets: re-enter example_app_portal_password_v1"
git pull --rebase
git push
```

> If a running service already uses the secret, that is a rotation: see
> [ROTATE.md](rotate.md). Key Vault keeps the wrong value as an older version of
> the item. If the value was exposed, change it in `example-portal` as well.

## If you answered Y at 5.2.3 by mistake

In the container, on `stacks/example-app-portal-password`:

**1** Record the marker:

```
sops set /repo/secrets/secrets.enc.yaml '["secrets"]["example_app_portal_password_v1"]["constraints"]' '{"generated": false, "why": "set by hand in the example-portal web UI; change it there first"}'
```

**2** Back up, commit and push:

```
backup --apply
git commit -am "secrets: mark example_app_portal_password_v1 as set by hand"
git pull --rebase
git push
```
