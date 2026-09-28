---
title: "Auth"
# the access table needs the page's full width
hide:
  - navigation
---

# auth

how people sign in to each app, on the lan and from outside, and what MFA
each way in has. my accounts and their MFA are in entra ID, and entra is the
MFA for any name outside that has none of its own.

## three access paths

- direct: the app's own address and port, on the lan only
- traefik on the lan: `https://<name>.mydomain.com`, on 443 at the swarm's VIP
- traefik outside: the same name from the internet. the router forwards its
  443 to traefik's 1444, see [traefik](../apps/traefik.md#network-considerations)

## the rules

- outside, every name has MFA or is a public site. an app with MFA of its own
  keeps it, and every other name goes behind
  [oauth2-proxy](../apps/oauth2-proxy.md), so users sign in with entra first
- on the lan, oauth2-proxy is also in front of the names that give control of
  something with no login, or only a password: the zigbee and z-wave UIs,
  dozzle's container logs, apprise's notification tokens, the unifi API
  browser's stored login, traefik's dashboard, seerr and the arr apps
- an app with native oauth (entra), signing its users in with entra itself,
  needs no oauth2-proxy in front: proxmox, PBS, portainer and grafana
- oauth2-proxy protects the name only. on the lan an app's own port still
  answers, with the app's own login, so that login still matters
- jellyfin has no entra sign-in. its TV and phone apps can't pass one

## two kinds of entra sign-in

entra is the provider for both here. oauth2-proxy and each of these apps also
work with other OpenID Connect providers.

| | oauth2-proxy (entra) | native oauth (entra) |
| --- | --- | --- |
| who asks | traefik, through oauth2-proxy, before the app sees the request | the app, on its login page |
| after it | the app's own login, if it has one | nothing: the app maps the entra user to a user of its own |
| app registration | one, shared by every name behind oauth2-proxy | one per app |
| works on | the name, through traefik | any address the app's redirect URIs list |

[entra ID](entra.md) has each app registration and where it's set up.

## every app

the table is written by the same script as traefik's routes, from the same
registry, so it changes when a route does. it lists only the names traefik
serves, and its columns are grouped by the three access paths.

- each row is a name, `<name>.mydomain.com`, unless it shows another in
  brackets
- the direct columns are the app's own login and MFA, which apply whichever
  way you reach it
- sign-in and MFA on each traefik path are what you meet there: the app's own,
  with `oauth2-proxy (entra), then` in front where traefik asks oauth2-proxy
  first
- entra's MFA is whatever my conditional access policy requires
- `not recorded` means the registry doesn't say yet

--8<-- "access/table.md"

## secrets, ssh and active directory

the passwords and keys the apps use, and how they reach a container, are on
[secrets](../secrets/index.md).

!!! note "to be written"
    ssh and keys, and active directory.
