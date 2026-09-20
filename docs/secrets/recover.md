---
title: "Recover"
---

# Recover, rebuild or bootstrap

Getting the secrets back when something is gone: your workstation, GitHub, the
Swarm, or everything. Also how the store was first created. Background is in
[BACKGROUND.md](background.md).

## Pick your situation

| You have | Section |
| --- | --- |
| a Swarm manager and GitHub access, just not your workstation | [1. Read the store from anywhere](#1-read-the-store-from-anywhere) |
| a Swarm manager and an Entra login, but no GitHub | [2. Restore the store from Key Vault](#2-restore-the-store-from-key-vault) |
| GitHub, but no Key Vault, and the age key on paper | [3. Without Key Vault](#3-without-key-vault) |
| a brand-new Swarm to put the secrets back into | [4. Rebuild a Swarm](#4-rebuild-a-swarm) |
| no store at all yet | [5. Bootstrap a new store](#5-bootstrap-a-new-store) |

The container carries the tools. The one thing it can't carry is
`secrets/secrets.enc.yaml`, the encrypted store, because that file changes. So
recovery is always two questions: where the store comes from, and where the key
to decrypt it comes from.

---

## 1. Read the store from anywhere

On any Swarm manager, from a workstation with ssh or on the manager itself.

**1.1** Start the container. Use `keyman` if you have the alias, otherwise run
this on the manager:

```bash
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock --dns-search yourdomain.com -e AKV_VAULT=YourKeyVaultName -e AKV_TENANT=00000000-0000-0000-0000-000000000000 ghcr.io/scyto/key-manager:latest
```

**1.2** At `No repo in /repo. Sign in to GitHub and clone it now? [Y/n]`, press
**Enter**, then complete the GitHub device sign-in.

**1.3** Sign in to Key Vault, which is where the age identity comes from:

```
az-login
```

**1.4** Confirm the store decrypts:

```
list
```

---

## 2. Restore the store from Key Vault

When GitHub is unreachable. Key Vault holds the encrypted store and the age
identity, so one Entra login gets both.

**2.1** Start the container as in 1.1.

**2.2** At `No repo in /repo. Sign in to GitHub and clone it now? [Y/n]`, type
**n**.

**2.3** Sign in to Key Vault:

```
az-login
```

**2.4** Fetch the encrypted store into `/repo`:

```
restore
```

**2.5** Confirm it decrypts:

```
list
```

> `/repo` is not a git clone in this situation, so nothing you change here can be
> committed. Use it to read the store or rebuild a Swarm (section 4), not to add
> or rotate secrets.
>
> **If you hold accounts in more than one Entra tenant:** the code only
> completes against the tenant `az-login` prints. An account from another tenant
> fails with `AADSTS50020` rather than authorising anything.

---

## 3. Without Key Vault

The store comes from GitHub and the key from your paper copy. The key is typed
into memory inside the container and never reaches a disk.

**3.1** Start the container as in 1.1, and at the clone prompt press **Enter**
and complete the GitHub sign-in.

**3.2** Type the key into the container's memory-backed `/work`:

```
cat > /work/age-key
```

Type or paste the `AGE-SECRET-KEY-1...` line, press **Enter**, then **Ctrl-D**.

**3.3** Point sops at it and check it decrypts:

```
chmod 600 /work/age-key
export SOPS_AGE_KEY_FILE=/work/age-key
list
```

> **`no identity matched any of the recipients`** means the key was mistyped.
> age keys carry a checksum, so a typo fails rather than giving a wrong key.
>
> **Do not use `SOPS_AGE_KEY`** for this. sops accepts the key in that
> environment variable, but environment variables can be read with
> `docker inspect`.
>
> `/work` is a tmpfs: the file is in RAM and gone when the container exits.

---

## 4. Rebuild a Swarm

Everything except the secrets comes from this repo. The secrets come from the
store.

**4.1** Create the Swarm and join the other managers.

**4.2** Recreate the out-of-band networks, from a clone of this repo on each
node. First on **every** node:

```bash
./bootstrap/networks.sh config-only
```

Then once, on a manager:

```bash
./bootstrap/networks.sh swarm
```

**4.3** On a manager, start the container and read the store, as in section 1
or 2.

**4.4** Read the new Swarm's cluster ID:

```
docker info --format '{{.Swarm.Cluster.ID}}'
```

**4.5** Record it in the store, so `provision` will write to this Swarm:

```
sops set /repo/secrets/secrets.enc.yaml '["swarm"]["cluster_id"]' '"<the ID from 4.4>"'
```

**4.6** Push the changed store to Key Vault straight away:

```
backup --apply
```

**4.7** Create every secret:

```
provision --apply
```

**4.8** If you have a git clone (section 1), commit and push the change on a
branch and open the PR. It prints the PR's URL; the number at the end is `130`
here:

```
git checkout -b secrets/new-swarm-cluster-id
git add -A
git commit -m "secrets: record the rebuilt Swarm's cluster id"
git push -u origin secrets/new-swarm-cluster-id
gh pr create --fill
```

**4.9** Merge it:

```
gh pr merge 130 --rebase --delete-branch
```

**4.10** Recreate the Portainer stacks from their deploy branches.

> **Why 4.5:** the store records the one Swarm it may write to, and every write
> checks it. A rebuilt Swarm has a new cluster ID, so without 4.5, `provision`
> stops with `WRONG SWARM`.
>
> **Why 4.6 comes before anything else:** the container is thrown away when you
> exit. Until the change is in Key Vault or merged into `main`, it exists only
> inside the container, and a later `restore` or clone would bring back the old
> ID. In section 2's situation there is no clone, so 4.6 is the only durable
> copy until GitHub is back and you can do 4.8 and 4.9.
>
> **4.4 to 4.9 follow the tool's code and have not been run for real**, because
> this Swarm has not been rebuilt.

---

## 5. Bootstrap a new store

How the store was first created, kept for a rebuild from nothing.

> **Written before key operations moved into the container.** These steps create
> the age identity on a workstation, which the rules now forbid. Doing the same
> inside the container, with the identity in `/work` and then uploaded to Key
> Vault by `backup`, is the intended replacement and has not been tried.

**5.1** Create the identity:

```bash
mkdir -p ~/.config/sops/age
age-keygen -o ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

`age-keygen -o` prints only the **public** key. The identity goes to the file.

| Platform | Where sops looks for the key |
| --- | --- |
| Linux | `~/.config/sops/age/keys.txt` |
| macOS | `~/Library/Application Support/sops/age/keys.txt` |
| Windows | `%AppData%\sops\age\keys.txt` |

`SOPS_AGE_KEY_FILE` overrides all three.

**5.2** Record the recipient in `.sops.yaml` at the repo root:

```yaml
creation_rules:
  - path_regex: ^secrets/secrets\.enc\.yaml$
    encrypted_regex: '^value$'
    age: >-
      age1... your public key ...
```

`encrypted_regex: '^value$'` encrypts the values and leaves names, notes and
flags readable.

**5.3** Keep the identity in at least two independent places. To check a paper
copy, type it back, press Ctrl-D, and confirm it prints your `age1...`:

```bash
age-keygen -y
```

A typo gives `invalid checksum` rather than a silently wrong key, because the
key format carries a checksum.

**5.4** Create the vault, with soft-delete and purge protection:

```bash
az keyvault create --name <vault> --resource-group <resource group> --location <region> --enable-purge-protection true --retention-days 90
```

**5.5** Push everything offsite and check it:

```bash
key-manager backup --apply
key-manager backup --verify
```

> `backup` uploads each secret, the age identity, so a bare machine can
> bootstrap from the vault, and the whole encrypted store, so a restore
> reproduces notes and flags exactly.
>
> Without purge protection, one admin action destroys the backup permanently.

---

## What a container leaves behind

**Nothing.** With `--rm` and only the Docker socket mounted, the container takes
everything with it when it exits: the clone, the GitHub login, the Entra token,
a typed age key, and `/work`.

That is why `add`, `rotate` and `retire` changes have to be pushed before you
`exit`. If `rotate` or `retire` could not push, it says `NOT PUSHED` and exits
non-zero. That is the one time not to type `exit`.
