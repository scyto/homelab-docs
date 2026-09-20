---
title: "Retire a Secret"
---

# Retire a secret

Stop a superseded secret from ever being created again, and remove it from
Swarm. The value itself stays in the store.

Uses the made-up `example_app` stack from [ROTATE.md](rotate.md), case A:
`example_app_session_secret_v1` has been replaced by
`example_app_session_secret_v2`. Where you see the example's names, use your
own. Background is in [BACKGROUND.md](background.md).

## Before you start

**1** The PR that stopped using `example_app_session_secret_v1` is **merged**.
For a rotation that is the `rotate/...` or `stacks/...` PR.

**2** Portainer has **redeployed** the stack, and it works on the new secret.

> `retire` checks both and refuses otherwise. It looks at the running tasks,
> not just the compose file, because a stalled rollout can leave old tasks
> running on the old secret while the file already names the new one.

## How the branch fits

```text
main
 |
 +-- retire/example-app-session-secret-v1   made and pushed by `retire`, in the container:
 |                                            secrets.enc.yaml marks _v1 provision:false
 |
 +-> (no deploy branch moves: only secrets.enc.yaml changes)
```

The container must be on `main`, and a fresh `keyman` session is.

## 1. Retire it (in the container)

**1.1** On your workstation, start a fresh container and sign in to GitHub when
it asks:

```bash
keyman
```

**1.2** Confirm the container is on `main`. It prints `main`:

```
git branch --show-current
```

**1.3** Sign in to Key Vault:

```
az-login
```

**1.4** See what it would do. It prints
`would retire  example_app_session_secret_v1` and
`still in swarm: yes -- remove separately`:

```
retire example_app_session_secret_v1
```

**1.5** Do it. It prints `retired`, `value kept`, and
`pushed branch retire/example-app-session-secret-v1`:

```
retire example_app_session_secret_v1 --apply
```

**1.6** Open the PR and note its number, `128` here:

```
gh pr create --fill
```

**1.7** Remove the secret from Swarm:

```
docker secret rm example_app_session_secret_v1
```

**1.8** Push the updated store to Key Vault:

```
backup --apply
```

**1.9** Leave the container:

```
exit
```

> **Why the value is kept:** `provision: false` stops `provision` recreating
> the secret, but the value stays readable, to roll a rotation back and to spot
> the same credential if it turns up elsewhere.
>
> **Why 1.8 is not optional:** without it Key Vault still holds the old secret
> as provisionable. A rebuild from the vault, which is the total-loss recovery
> path, would recreate the credential you just retired.

## 2. Merge (on your workstation)

**2.1** Merge the PR:

```bash
gh pr merge 128 --rebase --delete-branch
```

> Only `secrets/secrets.enc.yaml` changed, so no deploy branch moves and nothing
> restarts.

## 3. Revoke it at the source, if there is one

**3.1** For a credential a provider issued (ROTATE.md case B), revoke the old one
in the provider's console now.

**3.2** For the other cases there is nothing to revoke: the database or the web
UI already holds only the new value.

---

## If `retire` refuses

| It says | What it means | What to do |
| --- | --- | --- |
| `MOUNTED BY RUNNING TASKS in: example_app` | a task still uses the old secret | wait for the redeploy to finish, check `docker service ps example_app_app`, then run 1.5 again |
| `still referenced by a compose file` | a compose file, including `_attic/` and `_excluded/`, still names it | merge the PR that changed it, or change the other file first |
| `still named in the PreviousSpec of: example_app_app` | `docker service rollback` would bring the old secret back | see below |
| `this checkout is on '...', which is already merged into main` | the container is on an old branch | `git checkout main`, `git fetch origin main`, `git reset --hard origin/main`, then 1.5 |

**If you accept losing the rollback** (after a database or a web UI has already
moved to the new value, rolling back could not work anyway):

```
retire example_app_session_secret_v1 --allow-rollback-loss --apply
```
