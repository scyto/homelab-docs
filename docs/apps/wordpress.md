---
title: "WordPress"
---

# wordpress

i run one wordpress multisite on the swarm. one install serves several sites on
subdomains of `mydomain.com` and a site on another domain, `mydomain1.com`. the
stack is `wordpress2025`, with three services: `wordpress`, its `db`, and
`db-dump`, which keeps an hourly dump of the database for the backup.

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

## state considerations

- `html` is wordpress's `/var/www/html` and `db` is mysql's `/var/lib/mysql`.
  both are named binds to `/mnt/docker-cephFS/wordpress_html` and
  `wordpress_db` on the replicated storage, see
  [stack conventions](../docker/conventions.md#volumes-are-a-named-bind-with-driver_opts).
  `db-dump` writes to a third, `wordpress_dumps`, see
  [the hourly dump](#the-hourly-dump)
- mysql is pinned by digest, and wordpress only by its version tag.
  [renovate](../docker/image-updates-renovate.md) asks before bumping either,
  because either can run a schema migration on start
- both official images read passwords from files, so
  `WORDPRESS_DB_PASSWORD_FILE` and the `MYSQL_*_FILE` variables point at docker
  secrets, and no password is in the service spec

## network considerations
<span id="how-its-reached"></span>
the stack publishes `8180` for wordpress's port 80, and `8443` for its 443,
through the ingress mesh. its three services share the stack's default network,
where wordpress and `db-dump` reach the database as `db`.

[traefik](traefik.md) terminates TLS for every site name and proxies plain
http to port `8180` on the swarm's VIP, 192.168.1.45:

| name | inside the lan | outside |
| --- | --- | --- |
| `www.`, `blog.` | served | served, as public sites |
| `mydomain.com`, the root site | served, but the name is active directory's, see below | every path redirects to `www.`, keeping the path |
| `mydomain1.com`, the site on another domain | through cloudflare, as from outside: the lan has no DNS of its own for it | served, as a public site |

- the root site is never reachable from outside. it holds the network admin:
  wordpress sends every network-admin page to the root site's name
- on the lan that name belongs to active directory, so traefik's route for it
  is reached only by wordpress itself, see
  [the container reaching itself](#the-container-reaching-itself), and by a
  browser that maps the name to the VIP, see
  [the network admin](#the-network-admin)
- the other domain is outside traefik's wildcard certificate, so its route
  asks for a certificate of its own, see [traefik](traefik.md#the-fields).
  the cloudflare token has to cover that domain's zone too

wordpress only sees http, so it has to be told the visitor used https. the
`wp-config.php` that the official image generates does that when the proxy
sends `X-Forwarded-Proto`, and traefik sends it:

```php
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && strpos($_SERVER['HTTP_X_FORWARDED_PROTO'], 'https') !== false) {
	$_SERVER['HTTPS'] = 'on';
}
```

## the network admin

the network admin is on the root site, and on the lan `mydomain.com` belongs
to active directory. i open it in a browser window that maps just that name
to the VIP. on a mac, with chrome or edge:

```
open -na "Google Chrome" --args --user-data-dir="$HOME/Library/Application Support/wp-network-admin" --host-resolver-rules="MAP mydomain.com 192.168.1.45"
open -na "Microsoft Edge" --args --user-data-dir="$HOME/Library/Application Support/wp-network-admin-edge" --host-resolver-rules="MAP mydomain.com 192.168.1.45"
```

on windows, with edge, in powershell:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --user-data-dir="$env:LOCALAPPDATA\wp-network-admin" --host-resolver-rules="MAP mydomain.com 192.168.1.45"
```

then go to `https://mydomain.com/wp-admin/network/`.

- only that window, and only that one name, goes to traefik. the rest of the
  machine is unchanged, so active directory's use of the name keeps working.
  a hosts file entry on a domain-joined PC would break it
- the separate `--user-data-dir` starts a browser of its own. without it, the
  command hands the url to the browser already running, which ignores the
  switch
- traefik serves the root site on its lan listener with the domain's own
  certificate, so the window shows no warning
- tested with chrome and edge on a mac

## what makes multisite fiddly

- multisite picks the site from the `Host` header, so every site name has to
  reach wordpress unchanged. public DNS needs a record per name pointing at my
  WAN address, and the proxy needs a route per name that passes the host
  header through
- the root site is the bare `mydomain.com`, and inside my lan that name belongs
  to active directory. it resolves to the windows server domain controllers,
  not to the proxy, so from inside the lan the root site's name doesn't reach
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
    - the page breaks as soon as you save, until the proxy serves the name over https

3. make the proxy serve `mydomain.com` over https (npm, when i did this; in
   traefik it's a route like any other), then log in again at
   `https://mydomain.com`
    - do this in a browser that maps `mydomain.com` to the proxy, see
      [the network admin](#the-network-admin). inside the lan that name
      resolves to the domain controllers, see
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
      - mydomain.com:192.168.1.45
```

wordpress makes requests to its own url (cron, site health). inside the lan
that name resolves to the domain controllers, so the container pins it to the
VIP, where traefik serves the root site on its lan listener. outside, every
path of the root site redirects, so these requests must not go out through the
WAN: cron calls `/wp-cron.php` on its own name, and a redirect would stop it.

## apache's header limit

apache refuses a request with any single header over 8 KB, and an admin's
browser can pass that. the [oauth2-proxy](oauth2-proxy.md) sign-in cookie is
set on the whole domain, and it travels with wordpress's, wordfence's and the
shop's own cookies. apache then answers every page with a 400 before wordpress
runs. the stack mounts a config into apache's `conf-enabled` that raises the
limit to 32 KB:

--8<-- "blocks/swarm/wordpress2025/header-limits.conf.md"

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

## restoring the whole site

the `wordpress_html` folder and the dump from one backup are the whole site.
all four sites share the folder, and the dump holds every site's tables.

1. stop all three services, on any manager:

    ```
    docker service scale wordpress2025_wordpress=0 wordpress2025_db=0 wordpress2025_db-dump=0
    ```

    - moving a folder doesn't move a running container's mount. mysql would
      keep writing the folder you moved aside, and redeploying an unchanged
      stack restarts nothing

2. copy `wordpressdb.sql` out of `wordpress_dumps`, to a folder the stack
   doesn't mount

    - `db-dump` dumps when it starts. started before the dump is loaded, it
      would replace it with a dump of the new, empty database

3. put `wordpress_html` back from the backup. move `wordpress_db` aside and
   make an empty one in its place

    - from a snapshot in `/mnt/docker-cephFS/.snap/` while cephFS is fine,
      with `cp -a` to keep owners and modes
    - from PBS when cephFS is gone. that isn't written up yet, see
      [cephFS](../backups/cephfs.md#still-to-do)
    - mysql sets itself up only in an empty folder. with files in it, it
      starts on those and ignores its `MYSQL_*` variables

4. start the database alone:

    ```
    docker service scale wordpress2025_db=1
    ```

    - mysql creates `wordpressdb` and the database user, with the passwords
      from the stack's secrets

5. load the dump, on the node running the `db` task:

    ```
    docker exec -i $(docker ps -q --filter 'name=^wordpress2025_db\.') \
      sh -c 'MYSQL_PWD="$(cat /run/secrets/wordpress_mysql_root_password)" mysql -uroot' \
      < wordpressdb.sql
    ```

    - the anchored name skips `wordpress2025_db-dump`, which a plain
      `name=wordpress2025_db` also matches
    - `MYSQL_PWD` keeps the password out of the command line
    - the dump makes the database's tables. about 70 MB takes two minutes

6. start the other two:

    ```
    docker service scale wordpress2025_wordpress=1 wordpress2025_db-dump=1
    ```

    - `db-dump` now dumps the restored database

7. check every site, as in [checking it](#checking-it), with each site's name
   in the `Host` header: `mydomain.com`, `blog.mydomain.com`,
   `www.mydomain.com` and `mydomain1.com`

    - each should print its own title

8. to replay the changes made after the dump, see
   [binary logs](#binary-logs-and-rewinding-to-a-minute). the logs are in the
   `wordpress_db` folder you moved aside, or in its backup

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
