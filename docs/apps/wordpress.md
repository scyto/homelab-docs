---
title: "WordPress"
---

# wordpress

i run one wordpress multisite on the swarm. one install serves several sites on
subdomains of `mydomain.com` and a site on another domain. the stack is
`wordpress2025`, with three services: `wordpress`, its `db`, and `db-dump`,
which keeps an hourly dump of the database for the backup.

--8<-- "blocks/swarm/wordpress2025/compose.yml.md"

## before you deploy

1. create the three folders on the cephfs mount:

    ```
    sudo mkdir -p /mnt/docker-cephFS/wordpress_html /mnt/docker-cephFS/wordpress_db
    sudo mkdir -m 700 /mnt/docker-cephFS/wordpress_dumps
    ```

    - each volume binds its folder by path, so a missing folder fails the task
    - `wordpress_dumps` holds a full copy of the database, password hashes
      included, so only root can read it

2. create two docker secrets: `wordpress_db_password_v2` for the database
   user's password, and `wordpress_mysql_root_password` for mysql's root
   password

    - mysql reads both only when it first starts on an empty `wordpress_db`
      folder, to create the database. wordpress reads
      `wordpress_db_password_v2` on every connection, so that one has to match
      the database user's password in mysql

## how it's reached

nginx proxy manager terminates TLS for every site name and proxies plain http
to port `8180` on the swarm's VIP, 192.168.1.45:

| name | proxied to |
| --- | --- |
| `mydomain.com`, `www.`, `blog.`, `wordpress.`, `wpadmin.` | `http://192.168.1.45:8180` |
| the site on the other domain | `http://192.168.1.45:8180` |

wordpress only sees http, so it has to be told the visitor used https. the
`wp-config.php` that the official image generates does that when the proxy
sends `X-Forwarded-Proto`, and NPM sends it:

```php
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && strpos($_SERVER['HTTP_X_FORWARDED_PROTO'], 'https') !== false) {
	$_SERVER['HTTPS'] = 'on';
}
```

## what makes multisite fiddly

- multisite picks the site from the `Host` header, so every site name has to
  reach wordpress unchanged. public DNS needs a record per name pointing at my
  WAN address, and NPM needs a proxy host per name that passes the host header
  through
- the root site is the bare `mydomain.com`, and inside my lan that name belongs
  to active directory. it resolves to the windows server domain controllers,
  not to NPM, so from inside the lan the root site's name doesn't reach
  wordpress. the container gets round it with `extra_hosts`, below

## the multisite config

the image generates `wp-config.php` from environment variables and evaluates
`WORDPRESS_CONFIG_EXTRA` in it, so the multisite settings sit in git, not in a
file in the volume:

```yaml title="compose.yml"
      WORDPRESS_CONFIG_EXTRA: |
        /* Multisite */
        define('WP_ALLOW_MULTISITE', true );
        define( 'MULTISITE', true );
        define( 'SUBDOMAIN_INSTALL', true );
        define( 'DOMAIN_CURRENT_SITE', 'mydomain.com' );
        define( 'PATH_CURRENT_SITE', '/' );
        define( 'SITE_ID_CURRENT_SITE', 1 );
        define( 'BLOG_ID_CURRENT_SITE', 1 );
```

| define | does |
| --- | --- |
| `WP_ALLOW_MULTISITE` | adds Tools → Network Setup, where the network gets created |
| `MULTISITE` | says the network exists |
| `SUBDOMAIN_INSTALL` | sites are subdomains, `blog.mydomain.com`, not paths |
| `DOMAIN_CURRENT_SITE`, `PATH_CURRENT_SITE` | the main site's domain and path |
| `SITE_ID_CURRENT_SITE`, `BLOG_ID_CURRENT_SITE` | the network's and the main site's ids, 1 for the first |

to turn multisite on:

1. deploy with only `WP_ALLOW_MULTISITE`

2. in Settings → General, set the WordPress Address (URL) and the Site Address
   (URL) both to `https://mydomain.com`

    - keep the two the same. if they differ, everything breaks once multisite
      is on
    - the page breaks as soon as you save, until NPM serves the name over https

3. in NPM, give `mydomain.com`'s proxy host a certificate and Force SSL, then
   log in again at `https://mydomain.com`
    - do this from outside the lan, or from a machine whose hosts file points
      `mydomain.com` at NPM. inside the lan that name resolves to the domain
      controllers, see
      [what makes multisite fiddly](#what-makes-multisite-fiddly)

4. in Tools → Network Setup, choose sub-domains and install

5. add the other defines that network setup shows you to
   `WORDPRESS_CONFIG_EXTRA`, and redeploy

6. in the html volume, replace the rewrite rules in `.htaccess` with the
   multisite ones that network setup shows you

the only active change to the generated `wp-config.php` in the volume is
`define( 'WP_CACHE', true );`, which the WP Rocket plugin adds itself.

## the container reaching itself

```yaml title="compose.yml"
    hostname: mydomain.com
    extra_hosts:
      - mydomain.com:203.0.113.10
```

wordpress makes requests to its own url (cron, site health). inside the lan
that name resolves to the domain controllers, so the container pins it to the
public address, and those requests go through NPM like a visitor's.

## storage and passwords

- `html` and `db` are named binds to `/mnt/docker-cephFS/wordpress_html` and
  `wordpress_db` on the replicated storage, see
  [stack conventions](../docker/conventions.md#volumes-are-a-named-bind-with-driver_opts)
- mysql is pinned by digest, and wordpress only by its version tag.
  [renovate](../docker/image-updates-renovate.md) asks before bumping either,
  because either can run a schema migration on start
- both official images read passwords from files, so
  `WORDPRESS_DB_PASSWORD_FILE` and the `MYSQL_*_FILE` variables point at docker
  secrets, and no password is in the service spec

## the hourly dump

`db-dump` writes `wordpressdb.sql` to `/mnt/docker-cephFS/wordpress_dumps` when
it starts and at :50 every hour. ceph's snapshot at :00 catches it, and the
[cephFS backup](../backups/cephfs.md#databases) ships it at :15, so every backup
holds a dump known to be consistent next to mysql's own files.

- it runs the db service's image and digest, with `db-dump.sh` as its
  entrypoint instead of mysqld, so `mysqldump` matches the server
- `--single-transaction` reads one consistent view of the InnoDB tables without
  locking them, so wordpress keeps serving while it runs. the dump is about
  70 MB and takes a few seconds
- `--source-data=2` writes the binary log position the dump was taken at into
  the dump, as a comment. reading it takes a global read lock for a moment at
  the start
- the dump goes to a temporary name and is renamed only once complete, so a
  snapshot never catches half of one
- it is uncompressed on purpose. PBS compresses and deduplicates, and a dump
  whose rows barely changed shares almost every chunk with the hour before
- it has no healthcheck. on the swarm a failing one gets the task restarted,
  which can't fix a missing database or cephFS, and the script already retries
  every five minutes. a stale dump is for [gatus](../monitoring/gatus.md) to
  report, which isn't set up yet

--8<-- "blocks/swarm/wordpress2025/db-dump.sh.md"

### binary logs, and rewinding to a minute

mysql's binary log records every change in order. mysql 8 keeps it for thirty
days by default, which here was 6.1 GB. nothing replicates from this server, so
the log is only for replaying changes after a restore, and the database keeps
two days of it (`--binlog-expire-logs-seconds=172800`).

- with an hourly dump, two days is plenty: a restore needs the log only from
  the dump's position onward
- to rewind to just before a mistake, load the last dump from before it, then
  replay the log from the position in the dump's header comment up to the
  minute before, with `mysqlbinlog --start-position` and `--stop-datetime`.
  mysqldump 8.0.42 writes that comment as `CHANGE MASTER TO`; newer versions
  write `CHANGE REPLICATION SOURCE TO`
- older logs are still in older PBS backups of the `wordpress_db` folder

## wpadmin.conf

`wpadmin.conf` is an apache virtual host for `mydomain.com`, `www.`, `wpadmin.`
and `blog.`. the compose makes it into the swarm config `wpadmin_conf_v2`, but
no service mounts it, so apache never reads it. the `_v2` is the config's
version, see
[stack conventions](../docker/conventions.md#swarm-configs-are-versioned-by-name).

--8<-- "blocks/swarm/wordpress2025/wpadmin.conf.md"

## checking it

wordpress picks the site by name, so ask for the root site's:

```
curl -s -H 'Host: mydomain.com' http://192.168.1.45:8180/wp-json/ | jq -r .name
```

it prints the site's title, which wordpress reads from the database, so a
title means both services work. without the `Host` header wordpress redirects
to `wp-signup.php`.
[gatus](../monitoring/gatus.md#checking-a-database-through-the-app-that-uses-it)
runs this check every two minutes.
