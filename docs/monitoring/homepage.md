---
title: "Homepage"
---

# homepage dashboard

[homepage](https://gethomepage.dev/) on the swarm, port `3000`: one page, three tabs, apps, infrastructure and plumbing.

it runs on a manager and never on an adguard node. a container can't reach a macvlan container on the same host, and the adguard widgets would fail:

```yaml
      placement:
        constraints:
          - node.role == manager
          - node.labels.running_adguard1 == 0
          - node.labels.running_adguard2 == 0
```

## where the tiles come from

- **labels on the stacks**, for anything with a web UI. homepage reads two docker endpoints:

    ```yaml
    swarm:
      host: dockerproxy
      port: 2375
      swarm: true
    truenas:
      host: 192.168.1.86
      port: 2375
    ```

    `dockerproxy` is a read-only docker socket proxy on the swarm, reached over an overlay network. truenas1 has its own, on the lan
- **on the swarm the labels go under `deploy.labels`.** homepage reads the swarm's service specs, and container labels aren't in them, so a tile labelled the usual way never appears
- **`services.yaml`** for everything else: the portainer environments, truenas, unifi, proxmox and its nodes, glances on each host, and the plumbing tab

## config in git

homepage has no setting for where its config lives, so it can't read a git checkout the way [gatus](gatus.md) does. a git-sync sidecar in the same stack polls `deploy/swarm/homepage` and runs a small script after each sync that copies `config/*.yaml` and `custom.css` into homepage's config volume. homepage notices and reloads.

- the script reconciles, it doesn't only copy: a file removed from git disappears from the volume too
- it refuses to run against an empty checkout, so a bad ref can't wipe the dashboard
- it writes each file to a temporary name and renames it, so homepage never reads half a file
- it never touches the key files, which live in the same volume

the sidecar itself is the same as [gatus's](gatus.md#the-sidecar), fix for fix, with its own patterns for `stacks/swarm/homepage/config/` and the alias `homepage-git-sync`.

## tabs and layout

```yaml
layout:
  Arr:
    tab: Apps
    style: column
  Infrastructure:
    tab: Infrastructure
    style: row
    columns: 4
```

- every group names its tab. a group without one shows on every tab, and so does a group discovered from a label but missing from `layout`
- apps groups are columns, side by side. infrastructure and plumbing groups are rows of four, glances rows of three
- `maxGroupColumns: 6` lets up to six groups sit side by side on a wide screen. homepage's page stops growing at 1792px, so `custom.css` lifts that cap to 2560px on wider screens, or six columns would only mean narrower ones

## widgets and their keys

labels are readable by anything that can read the service, so no key or password goes in one. the label names a placeholder, and homepage fills it from a file:

```yaml
        - homepage.widget.type=qbittorrent
        - homepage.widget.url=http://192.168.1.86:8080
        - homepage.widget.username=admin
        - homepage.widget.password={{HOMEPAGE_FILE_QBITTORRENT_PASSWORD}}
```

```yaml
    environment:
      - HOMEPAGE_FILE_QBITTORRENT_PASSWORD=/app/config/secrets/qbittorrent_password
```

the file can be a docker secret as well, `HOMEPAGE_FILE_UNIFI_KEY=/run/secrets/unifi_apikey`. the other keys are read-only where the app allows it: a helpdesk-role portainer user, a proxmox auditor token, a read-only truenas api key.

- **truenas needs `version: 2`** on the widget. truenas 26 removed the REST api the default version uses
- **mind the upstream's lockout rules before testing a password.** qbittorrent bans an address for an hour after five failed logins, and homepage's address is its node's
- **to test a widget**, ask homepage's own proxy from inside its container, with the widget's endpoint name, not the upstream's api path:

    ```
    wget -q -O - 'http://127.0.0.1:3000/api/services/proxy?group=Downloads&service=qBittorrent&endpoint=torrents'
    ```

## plumbing tiles show gatus

the plumbing tab is things with no web UI. each tile shows its [gatus](gatus.md) check through a `customapi` widget, and none has a container status badge:

```yaml
        widget:
          type: customapi
          url: http://192.168.1.45:8085/api/v1/endpoints/plumbing_mosquitto/statuses?page=1&pageSize=1
          mappings:
            - field: results.0.success
              label: Gatus
              format: text
              remap:
                - value: true
                  to: UP
                - value: false
                  to: DOWN
```

- `pageSize=1`, because gatus lists results oldest first, so without it `results.0` would be the oldest sample it holds, not the latest
- no badges, because homepage can only take a badge from docker, kubernetes, proxmox, a ping or its own http check, not from gatus, and a mix of `running 1/1`, `running` and `healthy` side by side said different things

## glances tiles open glances

homepage only links a tile's icon and name, and the glances widget covers the rest of the tile. `custom.css` stretches the name's link over the whole tile, for tiles with `id: glances-<host>`:

```css
li.service[id^="glances-"] .service-card { position: relative; }
li.service[id^="glances-"] a.service-title-text::after {
  content: ""; position: absolute; inset: 0; z-index: 30;
}
```

## the stale page after a restart

homepage serves a prebuilt page, and after a restart that page has the image's placeholder settings: no tabs, no layout. a browser only asks homepage to rebuild it when the config has changed since it last looked, so after a restart it can keep showing the placeholder. to rebuild it:

```
wget -q -O - http://127.0.0.1:3000/api/revalidate
```

from inside the container, then reload the page.
