---
title: "Portainer Backups to S3"
---

# portainer backups to S3

portainer's database is on cephFS, so the [cephFS backup](cephfs.md) already
copies it. that is a copy of a live database file though, and there is no dump
tool for it. so portainer also backs itself up, to the
[S3 on my NAS](../truenas/s3-versity-gateway.md).

portainer's docs are clear about scope: this backs up **portainer's
configuration only**, not what is deployed on your environments. my stacks are in
[git](../docker/gitops-with-portainer.md), so that is fine.

scheduled backup to S3 is a Business Edition feature.

## 1. a bucket and a user for it

in versity, a user with role `user` and a bucket it owns, see
[step 5](../truenas/s3-versity-gateway.md#5-a-user-and-a-bucket-per-consumer).
portainer gets that user's keys, never the root keys.

## 2. settings

Settings, Backup Portainer, **Store in S3**:

| field | value |
| --- | --- |
| Access Key ID / Secret Access Key | the bucket user's keys |
| Region | `us-east-1` |
| Bucket name | `portainer-backups` |
| S3 compatible host | `https://truenas.mydomain.com:30157` |
| Password protect | on |
| Password | long and random |
| Cron rule | `0 3 * * *` |

**keep the password outside portainer.** if you ever need this backup, it is
because portainer is gone, and a password that only lived in portainer went with
it. same for the S3 keys, though those you can just reissue from versity.

generate it straight into the clipboard so it never lands in terminal scrollback
(macOS), paste it into portainer and your password store, then clear it:

```
openssl rand -hex 32 | pbcopy
pbcopy < /dev/null
```

## 3. run it once and check

run a backup by hand rather than waiting for the schedule. on the NAS:

```
docker logs --tail 5 ix-versitygw-versity-1
ls -la /mnt/rust/S3/portainer-backups/
```

what good looks like: a run of `PUT ... partNumber=N` lines with `200`, a final
`POST` with `200` (the multipart upload being assembled), and a file named
`portainer-backup_<date>_<time>.tar.gz.encrypted` owned by `apps`. the
`.encrypted` is how you know the password took. mine was 68 MB when i set this
up and is 356 MB now, which is the per-stack clones rather than the database,
see [things to know](#things-to-know).

a `403` in the log means the keys are wrong or the bucket's owner is a different
user.

## cold copies, before an upgrade

the scheduled backup runs while portainer runs. its log says what it does:
`Backing up database | from=/data/portainer.db to=/data/backup/...`. that file
is BoltDB, memory mapped, so it is a copy of a database being written. mine has
been corrupted twice, and an upgrade is when it matters, because the migration
rewrites it.

so before an upgrade i stop portainer and copy the directory cold:

```
docker service scale portainer_portainer=0

# as root, from a throwaway container: the data directory has root-owned paths
# (chisel/, some of the per-stack clones) that your own user cannot read
docker run --rm -v /mnt/docker-cephFS:/ceph alpine:3 \
  cp -a /ceph/portainer_data /ceph/portainer_data.cold-$(date +%Y%m%d)

docker service update --replicas 1 --image portainer/portainer-ee:2.45.1 portainer_portainer
```

- **check the copy before starting portainer again**: same size, and
  `md5sum` of `portainer.db` equal on both sides
- **rolling back is a directory swap**, not a restore: stop, put the copy back,
  set the image to the digest you came from. a minute, no backup password
- **it costs about a minute of downtime** for the UI and API. stacks, containers
  and agents are untouched, nothing runs through portainer at runtime
- **the S3 backup is still the offsite one.** this is the local copy you roll
  back from

## things to know

- **a manual backup through a reverse proxy will look like it failed.** nginx
  proxy manager gives up after 90 seconds and returns `504 Gateway Time-out`
  while portainer carries on and finishes the upload. run manual backups against
  portainer directly, or raise `proxy_read_timeout` for that host. the scheduled
  run never touches the proxy, which is why it always works
- **the archive is mostly not the database.** portainer keeps its own git clone
  per stack under `/data/compose`, about 14 MB each, so the archive grows with
  the number of stacks: mine went from 68 MB to 356 MB as stacks were added. the
  database itself is 8 MB

- **it grows.** nothing expires old backups, so a daily run is a couple of GB a
  month. clear it out now and then
- **database encryption is a separate thing.** portainer can also encrypt its
  database at rest with a docker secret named `portainer`. its docs say that
  cannot be reversed, and the key lives in the swarm, so rebuild the swarm without
  a copy of the key and the database is unreadable. i have not turned it on
- **restore test still to do.** until a backup has been restored somewhere, it
  is a file of unknown value
