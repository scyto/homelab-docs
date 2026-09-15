---
title: "S3 with Versity Gateway"
---

# S3 with Versity Gateway

an S3 endpoint on the NAS, for things that can back themselves up to S3.
first user is [portainer](../backups/portainer-s3.md).

## why versity

MinIO was the obvious answer and is not any more. its community edition stopped
publishing images in October 2025, went into maintenance mode that December and
the repo was archived in February 2026. TrueNAS pulled the MinIO app from its
stable train on 2026-07-09.

what the TrueNAS catalog offered when i set this up:

| app | version | why / why not |
| --- | --- | --- |
| **Versity Gateway** | v1.8.0 | S3 in front of an ordinary dataset. objects are plain files, metadata in xattrs, so ZFS snapshots and replication protect them and you can read them without the gateway |
| AIStor | stable train | MinIO's paid product, free tier allows homelabs. the licence expires and renews online; lapse 30 days and it goes read-only, 90 days and **all** S3 access is refused, reads included. not what i want holding backups |
| Garage | v2.4.1 | solid. its own on-disk format, built for spreading copies across sites |
| RustFS | 1.0.0-beta.12 | still beta |
| SeaweedFS | 4.46 | more moving parts than this needs |

versity's readme says nothing about object lock, so ZFS snapshots are my
protection against deletion. S3 credentials cannot delete a ZFS snapshot.

## 1. datasets

two, because the account file must not sit inside the bucket root, where
every top-level directory is a bucket:

| dataset | holds |
| --- | --- |
| `rust/S3` | buckets. each bucket is a directory, each object a file |
| `fast/configs/versitygw` | versity's account file (plain text, only protected by file permissions) |

both Generic preset. then give them to the apps user, the app does not do this
for host paths (see [TrueNAS](index.md#permission-denied-inside-the-app-on-a-host-path)):

```
chown 568:568 /mnt/rust/S3 /mnt/fast/configs/versitygw
chmod 700 /mnt/rust/S3 /mnt/fast/configs/versitygw
```

skip this and the app restart-loops on `open /var/lib/versitygw-iam/users.json:
permission denied`, or starts fine and fails the first bucket with
`InternalError` (`mkdir bucket: ... permission denied` in its log).

## 2. root credentials

generate them, and keep them somewhere that is not the NAS:

```
openssl rand -hex 20   # access key
openssl rand -hex 32   # secret key
```

## 3. install the app

Apps, Discover, **Versity Gateway** (community train).

| section | field | value |
| --- | --- | --- |
| Versity | Root User Access Key / Secret | from step 2 |
| | Additional Global Flags | see below |
| | Additional POSIX Flags | none |
| User and Group | | 568 / 568 (default) |
| Network | WebUI Port | 30355, published |
| | API Port | 30157, published |
| | Admin Port | bind mode None, the admin API then shares the API port |
| | Certificate | your TrueNAS certificate |
| Storage | Bucket Storage | Host Path `/mnt/rust/S3`, ACL off |
| | Additional Storage | Host Path `/mnt/fast/configs/versitygw`, mount path `/var/lib/versitygw-iam` |

additional global flags, one row each, flag and value in separate boxes:

| flag | value |
| --- | --- |
| `--iam-dir` | `/var/lib/versitygw-iam` |
| `--webui-gateways` | `https://truenas.yourdomain.com:30157` |
| `--webui-admin-gateways` | `https://truenas.yourdomain.com:30157` |
| `--cors-allow-origin` | `https://truenas.yourdomain.com:30355` |

- `--iam-dir` turns on versity's own user accounts. without it the root key is
  the only key and everything that uses the S3 has to hold it
- the two `--webui-*-gateways` flags matter. without them the login page fills
  in its endpoints from the container's own addresses (`127.0.0.1` and the
  docker bridge IP), your browser cannot reach those, and login fails with
  "Network error: cannot reach gateway" listing CORS and certificate problems
  as possible causes. neither was the cause for me. chrome also asked for
  permission to access local network devices, which fits the page trying
  `127.0.0.1`
- `--cors-allow-origin` because the web UI and the API are different ports, so
  different origins. the default is `*`. requests without an `Origin` header,
  which is every non-browser client, are not affected

## 4. check it

```
curl -fsS https://truenas.yourdomain.com:30157/healthz
```

that is the path the app's own healthcheck uses. use the full hostname the
certificate is for.

## 5. a user and a bucket per consumer

log in to `https://truenas.yourdomain.com:30355` with the root keys.

1. **Users**, create user, generate both keys, role **`user`**. a `user` can only
   see buckets assigned to it, and cannot create buckets or users
2. **Buckets**, create the bucket, owner is that user's access key
3. leave versioning off. on this backend it needs a separate `--versioning-dir`
   and versity marks it experimental. the ZFS snapshots do that job

check it landed as a directory owned by 568:

```
ls -ldn /mnt/rust/S3/<bucket>
```

## 6. snapshots

a periodic snapshot task on `rust/S3`. match the schedule to the busiest writer
and the retention to how long a mistake could go unnoticed. mine writes once a
day, so:

| task | keep |
| --- | --- |
| daily | 30 days |
| weekly | 12 weeks |

snapshots of files that only get added cost almost nothing, a snapshot only
holds blocks that later change or get deleted. add a daily one on
`fast/configs/versitygw` too, it is tiny.

## notes

- `.sgwtmp` inside a bucket is versity's scratch space for multipart uploads.
  leave it. if it keeps growing, interrupted uploads are leaving parts behind
- nothing expires objects for you. a daily backup of a few tens of MB is a
  couple of GB a month

## sources

- [MinIO ends active development](https://linuxiac.com/minio-ends-active-development/)
- [TrueNAS apps: S3](https://apps.truenas.com/tags/s3/)
- [AIStor licences](https://docs.min.io/aistor/operations/licenses/)
- [Versity Gateway](https://github.com/versity/versitygw) and its [wiki](https://github.com/versity/versitygw/wiki)
