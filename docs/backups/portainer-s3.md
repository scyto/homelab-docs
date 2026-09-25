---
title: "Portainer Backups to S3"
---

# portainer backups to S3

portainer's database is on cephFS, so the [cephFS backup](cephfs.md) already
copies it. that is a copy of a live database file though, and there is no dump
tool for it. so portainer also backs itself up to the
[S3 on my NAS](../truenas/s3-versity-gateway.md).

portainer's docs say this backs up **portainer's configuration only**, not what
is deployed on your environments. my stacks are in
[git](../docker/gitops-with-portainer.md), so that is fine.

scheduled backup to S3 is a Business Edition feature.

## 1. a bucket and a user for it

in versity, make a user with role `user` and a bucket it owns, as in
[step 5](../truenas/s3-versity-gateway.md#5-a-user-and-a-bucket-per-consumer).
portainer gets that user's keys, never the root keys.

## 2. settings

Settings, Backup Portainer, **Store in S3**:

| field | value |
| --- | --- |
| Access Key ID / Secret Access Key | the bucket user's keys |
| Region | `us-east-1` |
| Bucket name | `portainer-backups` |
| S3 compatible host | `https://truenas1.mydomain.com:30157` |
| Password protect | on |
| Password | long and random |
| Cron rule | `0 3 * * *` |

**keep the password outside portainer.** if you ever need this backup, it is
because portainer is gone, and a password that only lived in portainer went with
it. the same goes for the S3 keys, though you can reissue those from versity.

generate it straight into the clipboard so it never lands in terminal scrollback
(macOS), paste it into portainer and your password store, then clear it:

```
openssl rand -hex 32 | pbcopy
pbcopy < /dev/null
```

## 3. run it once and check

run a backup by hand instead of waiting for the schedule, then check on the NAS:

```
docker logs --tail 5 ix-versitygw-versity-1
ls -la /mnt/rust/S3/portainer-backups/
```

the log should show a run of `PUT ... partNumber=N` lines with `200`, then a
final `POST` with `200` (the multipart upload being assembled). the bucket should
hold a file named `portainer-backup_<date>_<time>.tar.gz.encrypted` owned by
`apps`. the `.encrypted` shows the password took. mine is 356 MB, most of it the
per-stack clones rather than the database, see [things to know](#things-to-know).

a `403` in the log means the keys are wrong or the bucket's owner is a different
user.

## cold copies, before an upgrade

the scheduled backup runs while portainer runs, and its log shows it copying the
database file:
`Backing up database | from=/data/portainer.db to=/data/backup/...`. that file
is BoltDB, memory mapped, so the backup holds a copy of a database being
written. mine has been corrupted twice. an upgrade is when that matters,
because the migration rewrites the database.

so before an upgrade i stop portainer and copy the directory cold. the first
command prints the image to roll back to:

```
docker service inspect portainer_portainer --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
docker service scale portainer_portainer=0

# repeat until no line starts with Running, so the copy is cold
docker service ps portainer_portainer --format '{{.CurrentState}}'

# as root, from a throwaway container: the data directory has root-owned paths
# (chisel/, some of the per-stack clones) that your own user cannot read
docker run --rm -v /mnt/docker-cephFS:/ceph alpine:3 \
  cp -a /ceph/portainer_data /ceph/portainer_data.cold-$(date +%Y%m%d)

docker run --rm -v /mnt/docker-cephFS:/ceph alpine:3 \
  md5sum /ceph/portainer_data/portainer.db /ceph/portainer_data.cold-$(date +%Y%m%d)/portainer.db
```

when the two checksums match, start it on the new version:

```
docker service update --replicas 1 --image portainer/portainer-ee:<new version> portainer_portainer
```

- **check the copy before starting portainer again**: the same size, and
  `md5sum` of `portainer.db` equal on both sides
- rolling back is a directory swap, not a restore: stop portainer, put the copy
  back, and set the image to the digest you came from. it takes a minute and
  needs no backup password
- it costs about a minute of downtime for the UI and API. stacks, containers
  and agents are untouched, because nothing runs through portainer at runtime
- the S3 backup is still the one off the cluster. the cold copy is the local one
  you roll back from

## things to know

- a manual backup through a reverse proxy looks like it failed. nginx proxy
  manager gives up after 90 seconds and returns `504 Gateway Time-out`, while
  portainer carries on and finishes the upload. run manual backups against
  portainer directly, or raise `proxy_read_timeout` for that host. the scheduled
  run never touches the proxy, which is why it always works
- most of the archive is not the database. portainer keeps its own git clone
  per stack under `/data/compose`, about 14 MB each, so the archive grows with
  the number of stacks: mine went from 68 MB to 356 MB as stacks were added. the
  database itself is 8 MB
- the bucket grows. nothing expires old backups, so a daily run adds about 10 GB
  a month. clear it out now and then
- portainer can also encrypt its database at rest, with a docker secret named
  `portainer`. that is separate from this backup's password. its docs say it
  cannot be reversed, and the key lives in the swarm, so rebuild the swarm
  without a copy of the key and the database is unreadable. i have not turned it
  on
- the restore test is still to do
