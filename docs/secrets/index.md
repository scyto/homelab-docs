---
title: "Secrets"
comments: true
---

# secrets

!!! warning "experimental"
    this is experimental, and it's how i do it, not what i'd suggest for most
    people. if you just want secrets out of your compose files, use docker
    secrets, or set environment variables by hand in portainer.

how a secret reaches a container, and which of the five ways to pick.

for years i typed passwords straight into the stack editor in portainer as
environment variables. it works, but it is the worst of the options.

## environment variables in the service spec

an environment variable on a swarm service is stored in the service spec.
anyone who can talk to the docker api can read it back in plain text, without
access to the container or the host filesystem.

you can read your own back:

```
docker service inspect <service> --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}'
```

i had a `dockerproxy` container exposing the docker socket over tcp on my lan
with no auth, so every password in every stack was readable from any device in
the house with one curl. it's read-only and the port is closed now, but the fix
was getting the values out of the specs.

## what docker gives you

docker only ever delivers a secret as a file, mounted at `/run/secrets/<name>`
on a tmpfs. the tmpfs is in ram, read only, and gone when the task stops. docker
never sets an environment variable for you.

so the job is getting from "there is a file" to "the app's config variable is
set". there are four ways to do that, plus labels, where only the app reading
them can help.

## create a secret

`docker secret create` reads the value from a file, which keeps it off the
command line:

```
docker secret create my_secret /path/to/value-file
```

that leaves nothing sensitive in your history or the process list, and you can
shred the file after.

if you do type it inline, note the **leading space** below. it keeps the line
out of history only if your shell is set to skip such lines:
`HISTCONTROL=ignorespace` in bash or `setopt HIST_IGNORE_SPACE` in zsh. neither
is on by default everywhere:

```
 printf '%s' 'the-actual-value' | docker secret create my_secret -
```

then the stack needs both halves:

```yaml
services:
  db:
    secrets:            # grant: mount this file into this service
      - my_secret
secrets:
  my_secret:
    external: true      # already exists in the swarm, don't create it
```

without the service-level `secrets:` list, the file isn't there.

secrets are immutable. to change a value you create a new secret under a new
name and repoint the compose, which is why my secret names have version
suffixes. a new one starts at `_v1`, and each change moves it on to `_v2` and
then `_v3`.

## option 1, the app reads the file itself

this is the best case: there is nothing to do but grant it.

`adguardhome-sync` knows nothing of docker secrets, but it takes a config file,
so the secret is the config file:

```yaml
    command: --config /run/secrets/adguard_sync_config run
```

both adguard passwords live in that yaml and neither ever appears in the spec.

## option 2, the `_FILE` convention

lots of official images support this. instead of `FOO` you set `FOO_FILE` to a
path and the image's own entrypoint reads it. wordpress and mysql both do:

```yaml
    environment:
      WORDPRESS_DB_PASSWORD_FILE: /run/secrets/wordpress_db_password
      MYSQL_ROOT_PASSWORD_FILE: /run/secrets/wordpress_mysql_root_password
```

check the image's docs first. it's common but not universal, and some images
support it for one variable and not another.

## option 3, an entrypoint wrapper

use this when the image supports neither, or when its own file support fails the
wrong way. npm, below, reads `DB_MYSQL_PASSWORD__FILE`, but on a missing file it
logs it and starts anyway, with no password. the wrapper stops the container
instead. it reads the file, exports the variable, then uses `exec` to run
whatever the image normally runs:

```yaml
    entrypoint:
      - /bin/sh
      - -c
      - >
        set -e;
        DB_MYSQL_PASSWORD="$$(cat /run/secrets/npm_db_password)";
        export DB_MYSQL_PASSWORD;
        exec /init
```

four things to get right:

- **do not write `export VAR="$(cat ...)"`.** it looks equivalent and is the
  form you will find in most examples. `export` is a *command*, and its own
  exit status is 0, so `set -e` never sees the `cat` fail and your app starts
  with an empty password. a plain assignment propagates the failure, so a
  missing secret crashes the container instead. try it:

  ```
  sh -c 'set -e; V="$(cat /nope)"; export V; echo REACHED'   # exit 1, silent
  sh -c 'set -e; export V="$(cat /nope)"; echo REACHED'      # exit 0, REACHED
  ```

  this matters most where an empty value doesn't make the app fail: an app
  that falls back to a different auth mode, or an image with a default baked in

- `$$` is compose's escape for a literal `$`. write one `$` and compose
  substitutes it at deploy time, which is what you're trying to avoid

- `exec` the command. without `exec` your shell stays as pid 1 and signal
  handling breaks, so the container stops responding to `docker stop`

- the image needs a shell. distroless images have no `/bin/sh`, so this option
  isn't available for them. check first:

  ```
  docker run --rm --entrypoint /bin/sh <image> -c 'echo ok'
  ```

you also need the image's real entrypoint and command to put back.
`docker inspect` shows them.

## option 4, environment variables

this is what i did for years, and it is sometimes still the only option. one of
my stacks, oauth2-proxy, still uses it: its image has no shell, and its client
id has no `_FILE` form. the way out is its config file mounted as a secret, like
adguardhome-sync in option 1. if you have to use this one, know the value is
readable over the api.

## labels

two of my adguard passwords were `homepage.widget.password` labels. a label is
part of the service spec, so it cannot be a secret. it cannot use `_FILE`
either, and an entrypoint wrapper cannot set it, because the scheduler applies
it before the container exists.

a label can hold a placeholder instead. homepage reads those labels and swaps
`{{HOMEPAGE_FILE_X}}` for the contents of the file named by its
`HOMEPAGE_FILE_X` variable. the label only says:

```yaml
    deploy:
      labels:
        - homepage.widget.password={{HOMEPAGE_FILE_ADGUARD1_PASSWORD}}
```

and the password sits in a file on homepage's config volume, never in a spec.
this works only because homepage does the swap. docker has no mechanism for it,
so a label that nothing swaps still can't carry a secret.

## non-swarm hosts

`docker secret` is swarm only. on a standalone host the api says:

```
This node is not a swarm manager
```

but the compose syntax still works with `file:` instead of `external: true`:

```yaml
secrets:
  my_secret:
    file: /path/on/host/my_secret
```

compose bind mounts that file to `/run/secrets/my_secret`, so options 1, 2 and 3
work unchanged. only the storage differs: it's a plain file on that host's disk,
with no encryption and no replication. this works for linux containers only.

if the compose comes from git, use an absolute host path. a relative
`file: ./secret.txt` resolves relative to the compose file, which under gitops
means inside the cloned repo, and you would be committing the value.

## where they live

swarm secrets are stored in the raft log on the manager nodes:

```
/var/lib/docker/swarm/raft/wal-v3-encrypted/
/var/lib/docker/swarm/raft/snap-v3-encrypted/
```

the log is encrypted and replicated to every manager. two things to understand:

**you cannot read a secret back out.** the api is write only for values. if you
haven't kept a copy somewhere, the only place that value exists is inside the
containers that have it mounted.

the encryption depends on autolock. with `AutoLockManagers` false, the default
and what i run, the decryption key sits on the same disk, so managers can reboot
unattended. that protects against the docker api and the service specs, not
against someone with root on a manager or a copy of the vm. autolock closes that
gap, at the price of unlocking the swarm by hand after every reboot.

so keep your own copy of every value outside the swarm. mine is
`secrets.enc.yaml`: every value is encrypted with sops and age, the file is
committed to a private repo, and azure key vault holds a copy. the key-manager
pages below show how.

## pick one, in this order

1. the app reads the file. nothing in the spec, nothing to maintain
2. `_FILE`. nothing in the spec, one line of config
3. entrypoint wrapper. nothing in the spec, but you own the entrypoint now
4. environment variable. readable over the api. last resort
5. label. never the value: a placeholder, if the app reading the label fills
   one from a file. otherwise change the design

read your own service specs back even if you fix nothing today. i assumed none
of mine were readable over the api for about four years.

## the key-manager tooling

the operations have their own pages:

| page | for |
| --- | --- |
| [background](background.md) | the model, in depth. age and SOPS, and where Key Vault fits |
| [key-manager reference](key-manager.md) | how to run the container, what it mounts, and every command |
| [add a secret](add.md) | a value that does not exist yet |
| [rotate a secret](rotate.md) | replacing one that does, and why rotation difficulty is set by where the authority lives |
| [retire a secret](retire.md) | taking a superseded one out of service |
| [recover](recover.md) | reading the store from anywhere, restoring it, rebuilding a swarm |

the tooling is a public container, `ghcr.io/scyto/key-manager`, so the commands
on those pages run as written. they operate on my own encrypted store, so
substitute your own.

## one-time setup: the keyman alias

every command on the operations pages runs **inside that container**, never on a
host. the container runs with `--rm`, so the clone, the logins and any key go
when you exit.

**1** add this to `~/.zshrc`, as one line:

```bash
alias keyman='ssh -t docker01 '\''docker pull -q ghcr.io/scyto/key-manager:latest && docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock --dns-search mydomain.com -e AKV_VAULT=YourKeyVaultName -e AKV_TENANT=00000000-0000-0000-0000-000000000000 -e GIT_AUTHOR_NAME=you -e GIT_AUTHOR_EMAIL=you@mydomain.com -e HOMELAB_REPO_URL=https://github.com/you/your-repo.git ghcr.io/scyto/key-manager:latest'\'''
```

**2** load it, and check it reaches a prompt. type `exit` to leave:

```bash
source ~/.zshrc
keyman
```

- it goes through `ssh -t <a swarm manager>` because `provision` and `verify`
  need that node's docker socket, which on a manager is the Swarm API. `-t`
  gives it a terminal. without it `docker run -it` fails with "the input device
  is not a TTY"
- paste it as one line. splitting the `ssh` and the `docker` parts across
  lines runs the docker half on your workstation after ssh exits
- `HOMELAB_REPO_URL` is the one you must change. the container clones a repo
  into `/repo` on first run, and left unset that is *my* repo, which is
  private, so the clone fails for anyone else. point it at your own.
  `clone --url <repo>` does the same thing per-run
- substitute your own vault, tenant and domain
- there are other ways to run it, including on a machine with nothing set up,
  see [key-manager reference](key-manager.md#three-ways-to-run-it)
