---
title: "Key-manager Reference"
---

# Key-manager reference

How to run the key-manager container, what it mounts, how it is built, and
what each command does. Why the store works the way it does is in
[BACKGROUND.md](background.md). The procedures are separate:
[ADD.md](add.md), [ROTATE.md](rotate.md), [RETIRE.md](retire.md) and
[RECOVER.md](recover.md).

---

## Everything runs in a container

Nothing is installed on the host except Docker. The container holds `sops`,
`age`, the Docker CLI and the Azure libraries. Getting that set onto every
machine you might work from is the problem it exists to solve, so **you get a
shell inside it and run every command from there.**
For starting it from a machine with nothing, see
[RECOVER.md](recover.md#1-read-the-store-from-anywhere).

### Swarm access

`/var/run/docker.sock`, mounted straight through:

```text
  -v /var/run/docker.sock:/var/run/docker.sock \
```

**This means you run the container on a Swarm manager.** A manager's local
socket is the Swarm API. On a worker it is not, and on a workstation there is
no Swarm socket to mount at all.

Because the socket is passed through unfiltered, the container talks to
whatever daemon owns it. The store records which Swarm it describes, and every
Swarm read checks against it, so pointing at the wrong daemon fails closed
rather than creating secrets somewhere nobody meant to touch:

```
error: WRONG SWARM. The store expects cluster cvuql7mtd3yh..., this socket
belongs to abc123...  Refusing to touch a Swarm this store does not describe.
```

Commands that need this: `status`, `verify`, `provision`, `rotate`, `retire`.
Commands that do not: `list`, `diff`, `check`, `clone`, `restore`, `backup`,
`gh-login`, `az-login`.

### Three ways to run it

All three run the same image with the same mounts. Pick whichever suits the
machine you are on.

**A `docker run` command.** Nothing to fetch first, works anywhere. It is in
[RECOVER.md, section 1](recover.md#1-read-the-store-from-anywhere).

**`ssh -t` to a manager from your workstation**, as one line, or the `keyman`
alias. Nothing installed on the workstation but ssh. See
[README.md, one-time setup](index.md#one-time-setup-the-keyman-alias).

**The wrapper script**, if you have a clone of this repo. It builds the same
`docker run` for you, and finds the swarm and the store without being told:

```bash
sudo install -m0755 tools/key-manager /usr/local/bin/key-manager
key-manager status          # from any directory
```

Without installing, `tools/key-manager` only works from inside the clone, which
is why running it from your home directory says "no such file or directory".
From elsewhere, point it at a clone:

```bash
export HOMELAB_REPO=~/repos/homelab-stacks
```

### Once you are in the container

The subcommands work on their own. `list` and `key-manager list` are the same
thing, and `help` prints them all:

```
key-manager -- read, provision and rotate this estate's secrets.

Inside this container the subcommands also work on their own, so `list` and
`key-manager list` are the same thing.

  Reading            list      names, notes and keyed digests. Never a value.
                     diff      store vs the local plaintext copies
                     status    store vs what the Swarm actually holds
                     check     can the store rebuild production? needs no key
                     verify    deployed values match the store (MATCH/MISMATCH)

  Getting set up     gh-login  sign in to GitHub. Required before any change.
                     clone     fetch this repo into /repo
                     az-login  sign in to Entra. Optional, for Key Vault.
                     restore   fetch the encrypted store from Key Vault
                     provision create Swarm secrets that are missing

  Changing a secret  add       record a secret the compose files already ask for
                     rotate    generate a new value and stage it everywhere
                     feed      pass a value to a command on stdin, never argv
                     retire    mark a superseded secret as not to be deployed

  Key Vault          backup    push the store, or --verify what is there
                     akv-get   one value to stdout, for SOPS_AGE_KEY_CMD

Every writing command is a dry run until given --apply.
`<command> --help` explains one of them. Full guide: secrets/README.md
```

### What each mount is for

| Mount | Why |
| --- | --- |
| `$PWD:/repo` | optional. **Where the store lives, or will live.** `secrets/secrets.enc.yaml` is the one file the image cannot carry, because it changes. A full clone works, so does a directory holding only that file, so does an empty one if you then run `restore`. Without this mount, `clone` puts the repo in `/repo` on the container's own filesystem, which is what the `keyman` alias does |
| *(no flag)* | The GitHub token, the Entra token and `/work` all default to `/dev/shm`, which Docker mounts as a tmpfs in every container. Memory is what you get by doing nothing; putting them on disk would take a deliberate flag. Only those three: a clone is not in `/dev/shm` |
| `/var/run/docker.sock` | the Swarm API. Only meaningful on a manager, and checked against the cluster the store describes |
| `$SOPS_AGE_KEY_FILE:/run/age-key:ro` | optional. Your age identity, if you are not fetching it from Key Vault |

Two absences are deliberate. **No private key is ever mounted** except the age
identity, and only when you ask for it. **Nothing on the host's disk is mounted
writable** except `/repo`, when you mount one. A clone made inside the
container is on its writable layer, which is disk, and `--rm` deletes it when
the container exits. That is safe because the store in it stays encrypted:
key-manager never writes a value there in plain text.

**The tokens are in memory, with one caveat.** `gh-login` warns
"Authentication credentials saved in plain text" because a container has no OS
keyring: the GitHub token goes to `hosts.yml` in cleartext, in `/dev/shm/km/gh`,
where the image points `GH_CONFIG_DIR`. That, and the Entra token cache, which
`~/.IdentityService` links into `/dev/shm`, stay off the container's writable
layer and go when it exits. **Memory-backed is not memory-only**: tmpfs pages
can be swapped under memory pressure, and all three managers run with swap
enabled. Docker 28 does not accept the `noswap` mount option, so closing that
gap means turning swap off on the managers or encrypting it. Both tokens are
short-lived and small, which is why this is a note rather than a blocker.

`gh` also becomes git's credential helper, so a push works without key-manager
handling a token.

### What `feed` can reach

`feed` hands a value to a command on stdin, and for a database that command has
to run against the container holding the database. With only the local socket
mounted, `docker exec` reaches containers **on this node**, and nothing else.

So run the key-manager container on the node where that database is. Find it
with:

```
status                                  # confirms you are on the right Swarm
docker service ps <stack>_db --format '{{.Node}}'
```

If the database is on another node, v1 has no route to it: ssh from inside the
container was removed along with the ssh transport. Run key-manager on that
node instead.

**That node may be a worker.** `feed` needs only `docker exec`, so it works
there. `rotate`, `provision`, `verify`, `status` and `retire` need a manager and
refuse on a worker, which is why [ROTATE.md](rotate.md) case C rotates in one
container and feeds from a second.

A file on a host is the same problem: `feed` can write one only where its
container runs, with the file's directory bound in. That is how
[ADD.md, step 6b](add.md#6b-a-secret-that-is-not-a-swarm-secret-in-the-container)
puts a value on a standalone host.

The wrapper still passes `--dns-search`, so names resolve inside the container
the way they do on the host. Docker writes a `resolv.conf` with a nameserver
and no `search` line, so without it a bare `docker01` does not resolve even
though the host resolves it fine.

### On other machines

Same command. The image is the reason it behaves identically on macOS, Linux
and WSL. On Windows the ssh agent is a named pipe rather than a socket, so
either run the wrapper from WSL or pass `-e SOPS_AGE_KEY_FILE` and skip the
swarm commands.

---

## How the image is built

Built and published by a workflow in my private repo
on any change to the tools, for `linux/amd64` and `linux/arm64`. Tagged
`latest` and with the commit SHA, so a rotation can be pinned to the exact
image it was run with.

`tools/key-manager` is a thin wrapper around `docker run`. Read it if you need to
know exactly what is mounted, or run the image directly for anything the
wrapper does not cover.

The image holds no secrets and no site configuration. `.sops.yaml` is
deliberately not baked in: sops resolves its config by walking up from the file
it is editing, so with the repo mounted it finds `/repo/.sops.yaml` and a baked
copy is never read. Leaving it out keeps the age recipient out of the image.

`SOPS_AGE_KEY_CMD` is set in the image, so the identity comes from the vault
with nothing pre-placed. Safe as a default because sops treats `KEY_CMD` and
`KEY_FILE` as *additive*:

| `KEY_CMD` | `KEY_FILE` | Result |
| --- | --- | --- |
| fails | valid | exit 0, the file is used |
| fails | absent | exit 128 |
| valid | absent | exit 0 |

The helper fast-fails when `SOPS_AGE_KEY_FILE` is readable or `AKV_VAULT` is
unset. Without that it would sit on a device-code prompt until timeout before
sops ever reached the file. That is correct eventually, but it looks like a
hang on the one path you take when everything else is broken.

`backup --apply` pushes each secret and the encrypted store without a key file.
Only the **identity upload** needs one: with no file it prints `identity
skipped: no local key file` and carries on, which is right when the vault's copy
is what decrypted the store. Uploading the identity is a bootstrap and recovery
step, not part of adding a secret.

---

## Command reference

Every writing command is a **dry run** unless given `--apply`.

| Command | Does | Also needs |
| --- | --- | --- |
| `list` | names, notes, keyed digests | |
| `add` | record a secret, repoint compose to `_v1`; shows `*` per character and the length ([ADD.md](add.md)) | a terminal |
| `diff` | store vs the local plaintext copies | |
| `status` | store vs what Swarm holds | |
| `check` | can the store rebuild production, and is anything a secret that is not one? | nothing at all, runs in CI |
| `verify` | deployed values match the store | |
| `provision` | create missing Swarm secrets | |
| `backup` | push to Key Vault, or `--verify` | `SOPS_AGE_KEY_FILE` only to upload the identity |
| `restore` | fetch the encrypted store back from Key Vault | |
| `akv-get` | one value to stdout, for `SOPS_AGE_KEY_CMD` | |
| `gh-login` | GitHub device code, and git identity for commits typed in the container. Required before any change | a terminal |
| `clone` | fetch this repo into `/repo`, every branch's tip | `gh-login` first |
| `az-login` | Entra device code, cache the token | |
| `rotate` | generate, store, create in Swarm, verify, repoint compose, push a `rotate/` branch ([ROTATE.md](rotate.md)) | `gh-login` first, on `main` |
| `feed` | plaintext into a command's stdin | whatever the command needs |
| `retire` | mark a superseded secret unprovisionable, push a `retire/` branch ([RETIRE.md](retire.md)) | `gh-login` first, on `main` |

The wrapper supplies the identity, the vault name and the docker connection, so
those are not listed. Uploading the identity with `backup --apply` is the one
exception: fetching it from the vault to upload it there would be circular, so
that part needs a real file and is skipped without one.

`check` needing nothing is deliberate: secret **names** are plaintext by design,
so CI can verify the store covers production without holding any key.
