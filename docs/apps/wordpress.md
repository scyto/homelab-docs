---
title: "WordPress"
---

# wordpress

one wordpress multisite on the swarm: several sites on subdomains of `mydomain.com`, and a site on another domain, from one install. the stack is `wordpress2025`, two services, `wordpress` and its `db`.

## how it's reached

nginx proxy manager terminates TLS for every site name and proxies plain http to the swarm on port `8180`:

| name | proxied to |
| --- | --- |
| `mydomain.com`, `www.`, `blog.`, `wordpress.`, `wpadmin.` | `http://<swarm vip>:8180` |
| the site on the other domain | `http://<swarm vip>:8180` |

wordpress only sees http, so it has to be told the visitor used https. the `wp-config.php` the official image generates already does that when the proxy sends `X-Forwarded-Proto`, which NPM does:

```php
if (isset($_SERVER['HTTP_X_FORWARDED_PROTO']) && strpos($_SERVER['HTTP_X_FORWARDED_PROTO'], 'https') !== false) {
	$_SERVER['HTTPS'] = 'on';
}
```

## what makes multisite fiddly

- **it picks the site from the `Host` header.** every site name has to reach wordpress unchanged: public DNS needs a record per name pointing at my WAN address, and NPM needs a proxy host per name that passes the host header through
- **the root site is the bare `mydomain.com`, and inside my lan that name belongs to active directory.** it resolves to the windows server domain controllers, not to NPM, so from inside the lan the root site's name doesn't reach wordpress. the container itself gets round it with `extra_hosts`, below

## multisite config lives in the compose

the image generates `wp-config.php` from environment variables and evaluates `WORDPRESS_CONFIG_EXTRA` in it, so the multisite settings sit in git, not in a file in the volume:

```yaml
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

to turn it on:

1. deploy with only `WP_ALLOW_MULTISITE`
2. Tools → Network Setup, choose sub-domains, install
3. add the other defines network setup shows you to `WORDPRESS_CONFIG_EXTRA`, and redeploy
4. replace the rewrite rules in `.htaccess`, in the html volume, with the multisite ones network setup shows you

the only active change to the generated `wp-config.php` in the volume is `define( 'WP_CACHE', true );`, which the WP Rocket plugin adds itself.

## the container reaching itself

```yaml
    hostname: mydomain.com
    extra_hosts:
      - mydomain.com:<public address>
```

wordpress makes requests to its own url (cron, site health). inside the lan that name resolves to the domain controllers, so the container pins it to the public address, and those requests go through NPM like a visitor's.

## storage and passwords

- `html` and `db` are named binds on the replicated storage, `/mnt/docker-cephFS/wordpress_html` and `wordpress_db`, see [stack conventions](../docker/conventions.md#volumes-are-a-named-bind-with-driver_opts)
- mysql is pinned by digest, and [renovate](../docker/image-updates-renovate.md) asks before bumping mysql or wordpress, because either can run a schema migration on start
- both official images read passwords from files, so `WORDPRESS_DB_PASSWORD_FILE` and the `MYSQL_*_FILE` variables point at docker secrets, and no password is in the service spec
