---
title: "Entra ID"
---

# entra ID

entra ID is where my accounts and their MFA live. each app that signs users in
with entra has its own app registration, which decides who may sign in and
where entra sends them back to.

## app registrations

| app | signs in through | redirect URI | set up on |
| --- | --- | --- | --- |
| oauth2-proxy, for every name behind oauth | oauth2-proxy's `entra-id` provider | `https://auth.mydomain.com/oauth2/callback` | [oauth2-proxy](../apps/oauth2-proxy.md#signing-in-with-entra) |
| portainer | portainer's oauth setting | `https://portainer.mydomain.com` | [portainer](../docker/portainer.md#signing-in-with-entra) |
| proxmox | an OpenID Connect realm | every name you open proxmox on, each node's with `:8006` | [entra ID auth](../proxmox/extras/azure-ad-auth.md) |
| PBS | an OpenID Connect realm | to be written | [PBS](../truenas/containers.md#signing-in-with-entra) |
| grafana | grafana's azure AD setting | to be written | [grafana](../truenas/apps.md#grafana-signing-in-with-entra) |

## on every registration

1. on the app's enterprise application, turn on **assignment required** and
   assign the people who may sign in

    - without it, every account in the directory can sign in

2. require MFA for the app with a conditional access policy

    - that's the MFA every entra sign-in relies on

3. note when the client secret expires

    - when it does, signing in with entra to that app stops until you make a
      new secret and give it to the app

## when entra is down

each app with its own entra sign-in keeps a password login beside it:

| app | password login |
| --- | --- |
| portainer | the initial admin, always on |
| proxmox | the `pam`, `pve` and active directory realms. root@pam also needs its TOTP or passkey |
| PBS | the `pam` and `pbs` realms |
| grafana | its password form |

- from outside, portainer's password login is behind oauth2-proxy, so an
  entra outage means using it from the lan
- a name behind oauth2-proxy has no way round it from outside. on the lan,
  the app's own port still answers with the app's own login
