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
[git](../docker-swarm/gitops-with-portainer.md), so that is fine.

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
| S3 compatible host | `https://truenas.yourdomain.com:30157` |
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
`.encrypted` is how you know the password took. mine is about 68 MB.

a `403` in the log means the keys are wrong or the bucket's owner is a different
user.

## things to know

- **it grows.** nothing expires old backups, so a daily run is a couple of GB a
  month. clear it out now and then
- **database encryption is a separate thing.** portainer can also encrypt its
  database at rest with a docker secret named `portainer`. its docs say that
  cannot be reversed, and the key lives in the swarm, so rebuild the swarm without
  a copy of the key and the database is unreadable. i have not turned it on
- **restore test still to do.** until a backup has been restored somewhere, it
  is a file of unknown value
