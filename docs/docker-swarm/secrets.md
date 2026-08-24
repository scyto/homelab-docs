---
title: "getting secrets into swarm containers"
comments: true
---

# getting secrets into swarm containers

for years i typed passwords straight into the stack editor in portainer as
environment variables. it works. its also the worst of the options, for a reason
that isn't obvious.

## why not environment variables

an environment variable on a swarm service is stored in the **service spec**.
anyone who can talk to the docker api can read it back in plain text. not the
container, not the host filesystem, the api.

go and look at your own:

```
docker service inspect <service> --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}'
```

i had a `dockerproxy` container exposing the docker socket over tcp on my lan
with no auth, because something needed read access and that was the quick way to
give it. so every password in every stack was readable from any device in the
house with one curl. its read-only and the port is closed now, but the fix was
getting the values out of the specs.

## what docker gives you

docker only ever delivers a secret **as a file**, mounted at `/run/secrets/<name>`
on a tmpfs. ram, read only, gone when the task stops. it never sets an
environment variable for you.

so the job is getting from "there is a file" to "the app's config variable is
set". four ways to do that, and one case with no way at all.

## Create a secret

mind your shell history, a leading space keeps it out of most shells, or pipe a
file in instead:

```
printf '%s' 'the-actual-value' | docker secret create my_secret -
```

then in the stack you need **both** halves:

```yaml
services:
  db:
    secrets:            # grant: mount this file into this service
      - my_secret
secrets:
  my_secret:
    external: true      # already exists in the swarm, don't create it
```

miss the service level `secrets:` list and the file just isn't there.

**secrets are immutable.** you cannot edit one. to change a value you create a
new secret under a new name and repoint the compose, which is why my secret names
are growing `_v2` suffixes.

## option 1, the app reads the file itself

best case, nothing to do but grant it.

`adguardhome-sync` has no idea what a docker secret is but it takes a config
file, so the secret **is** the config file:

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

check the image docs first, its common but not universal, and some images support
it for one variable and not another.

## option 3, an entrypoint wrapper

when the image supports neither. read the file, export the variable, then `exec`
whatever the image normally runs:

```yaml
    entrypoint:
      - /bin/sh
      - -c
      - >
        export DB_MYSQL_PASSWORD="$$(cat /run/secrets/npm_db_password)";
        exec /init
```

three things that will bite you:

- `$$` is compose's escape for a literal `$`. write one `$` and compose
  substitutes it at deploy time, which is exactly what you're trying to avoid
- you must `exec`, not just run the command, or your shell stays as pid 1 and
  signal handling breaks, so the container stops responding to `docker stop`
- the image needs a shell. distroless images have no `/bin/sh` so this option
  isn't available. check first:

  ```
  docker run --rm --entrypoint /bin/sh <image> -c 'echo ok'
  ```

you also need the image's real entrypoint and command to put back, `docker
inspect` will tell you.

## option 4, environment variables

what i did for years, and still sometimes the only option. three of my stacks are
stuck here because the images read environment variables and offer nothing else.
if you have to, know the value is readable over the api.

## no option at all, labels

two of my adguard passwords were `homepage.widget.password` **labels**. a label is
part of the service spec by definition. it cannot be a secret, cannot use `_FILE`
and cannot be set by an entrypoint wrapper, because the scheduler applies it
before the container exists.

there is no mechanism. i deleted the credential and lost the dashboard widget.

## non-swarm hosts

`docker secret` is swarm only, on a standalone host the api says:

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
work unchanged. only the storage differs, its a plain file on that host's disk,
no encryption, no replication. linux containers only.

one trap if the compose comes from git: a relative `file: ./secret.txt` resolves
relative to the compose file, which under gitops means inside the cloned repo,
and you would be committing the value. use an absolute host path.

## where they actually live

on the manager nodes, in the raft log:

```
/var/lib/docker/swarm/raft/wal-v3-encrypted/
/var/lib/docker/swarm/raft/snap-v3-encrypted/
```

encrypted, replicated to every manager. two things to understand:

**you cannot read a secret back out.** the api is write only for values. if you
haven't kept a copy somewhere, the only place that value exists is inside the
containers that have it mounted.

**"encrypted" depends on autolock.** with `AutoLockManagers` false, which is the
default and what i run, the decryption key sits on the same disk so managers can
reboot unattended. that protects against the docker api and the service specs,
not against someone with root on a manager or a copy of the vm. autolock closes
that gap and the price is unlocking the swarm by hand after every reboot.

so keep your own copy of every value, offline, outside the swarm. mine is a
gitignored file mode 600 in a private repo.

## pick one, in this order

1. the app reads the file. nothing in the spec, nothing to maintain
2. `_FILE`. nothing in the spec, one line of config
3. entrypoint wrapper. nothing in the spec, but you own the entrypoint now
4. environment variable. readable over the api. last resort
5. label. not possible, change the design

do the audit even if you fix nothing today. i assumed none of mine were readable
over the api, for about four years.
