---
title: "runs my oauth2-proxy for Azure based auth"
source_gist: https://gist.github.com/scyto/7315468af220655fea1fde7366d8c506
---

# runs my oauth2-proxy for Azure based auth

!!! note "secrets"
    i make my secrets from my own [secret store](../secrets/index.md), which
    only fits my setup. the `docker secret create` command here is plain
    swarm: use it, or however you normally make secrets.

## Description
oauth2-proxy puts an entra ID sign-in, with MFA, in front of web sites that
have no login of their own. [traefik](traefik.md) asks it about every request
to a name marked `oauth`: a signed-in browser goes on to the site, and anyone
else goes to entra first. one sign-in, on `auth.mydomain.com`, covers every
name.

## State Considerations for SWARM

- none. it keeps no files. a sign-in lives in an encrypted cookie in the
  browser
- the client secret is a swarm secret, which oauth2-proxy reads through
  `OAUTH2_PROXY_CLIENT_SECRET_FILE`, see
  [secrets](../secrets/index.md#option-2-the-_file-convention). the client ID
  and the cookie secret are portainer stack variables

## Network Considerations

- it publishes 4180 on the ingress mesh, and traefik reaches it on 4180 at the
  VIP, the same way it reaches every other app
- `auth.mydomain.com` is its own name, served by traefik on the lan and
  outside, with no sign-in in front of it. entra sends every browser back
  there after signing in, so the name needs a record in the internal DNS and
  in cloudflare
- the cookie is set on `.mydomain.com`, so a sign-in that started on one name
  covers the others

## Placement Considerations
one replica, anywhere on the swarm.

--8<-- "blocks/swarm/oauth/compose.yml.md"

## signing in with entra

users sign in through oauth2-proxy's own app registration in entra.
oauth2-proxy uses the `entra-id` provider (upstream has deprecated `azure`).
[entra ID](../auth/entra.md) lists every app registration.

1. register an app in entra (app registrations → new registration), for this
   directory only, with a web redirect URI of
   `https://auth.mydomain.com/oauth2/callback`

    - entra always sends the browser back to this one address, whichever name
      the sign-in started on

2. create a client secret, and store it as a docker secret:

    ```bash
    docker secret create oauth_client_secret -
    ```

    - paste the secret's value (not its ID), then press Ctrl-D

3. set the portainer stack variables: `OAUTH2_PROXY_CLIENT_ID` to the app's
   client ID, and `OAUTH2_PROXY_COOKIE_SECRET` to 32 random bytes,
   base64-encoded:

    ```bash
    openssl rand -base64 32 | tr -- '+/' '-_'
    ```

4. on the app's enterprise application, turn on **assignment required** and
   assign the people who may sign in

    - oauth2-proxy only checks that the email ends in `mydomain.com`, so who
      gets in is decided in entra

5. require MFA for the app with a conditional access policy

    - that's the MFA every name behind oauth relies on

## how traefik uses it

- traefik asks `/` on 4180 about each request. a signed-in browser gets the
  `static://202` upstream's 202, and traefik lets the request through.
  anyone else gets oauth2-proxy's redirect to entra, and an API client gets a 401
- `OAUTH2_PROXY_WHITELIST_DOMAINS` is plural. oauth2-proxy reads a setting that
  takes several values from the plural name only. with the singular, a sign-in
  lands on `auth.mydomain.com` instead of the page it started from
- oauth2-proxy exits at startup without `OAUTH2_PROXY_OIDC_ISSUER_URL`

## checking it

sign in, and see who you're signed in as:

```text
https://auth.mydomain.com/oauth2/sign_in?rd=/oauth2/userinfo
```

after entra, the page shows your email. `/oauth2/userinfo` on its own only
answers 401 when you're signed out: `sign_in` starts the sign-in, and `rd` is
where it lands afterwards.
