---
title: "acme.sh for Synology DSM"
---

# acme.sh for Synology DSM

## Description
renews my synology NAS certificates and installs them in DSM, from the swarm
rather than from a container on the NAS. i ran it on the NAS before, it stopped
renewing and nothing told me until the certificates had been expired for months.
on the swarm it's in git, it fails over between nodes, and it's one place to
look.

it uses [acme.sh](https://github.com/acmesh-official/acme.sh)'s own
`synology_dsm` deploy hook through a small wrapper. the wrapper does two things
the built in hook doesn't:

- it reads the DSM password from a swarm secret on every run. `synology_dsm`
  otherwise saves the username and password, only base64 encoded, in the
  certificate's settings, which here are on cephfs. the wrapper clears them after
  each deploy
- it skips certificate verification for the deploy only. DSM is serving an
  expired certificate at exactly the moment a renewal has to land

## State Considerations for SWARM
acme.sh keeps its CA account, the certificates, their keys and the renewal
settings in `/acme.sh`, a cephfs bind. it holds private keys and the cloudflare
token, so create it root owned, mode 700.

## Network Considerations
nothing is published. the container calls the CA, cloudflare, and each DSM on
its HTTPS port. mine use 5101, the default is 5001.

## Placement Considerations
None, by default this template will result in a single replica

## Secrets

- **cloudflare account API token:** made from the "Edit zone DNS" template, DNS
  read and write on one zone. acme.sh only reads `CF_Token` from the environment,
  so an entrypoint wrapper reads the secret and exports it. see
  [secrets](../secrets/index.md)
- **a DSM password per NAS:** mounted at a fixed file name,
  `dsm_password_<host>`. the wrapper takes `<host>` from the first label of the
  certificate's domain, so `syn02.mydomain.com` reads `dsm_password_syn02`
- **the DSM account:** a local user in the administrators group, with no 2-step
  verification (the hook can't answer a code) and no password expiry

## Setup

1. on each NAS, create a local user `acme` in the **administrators** group, with
   no 2-step verification and no password expiry.

2. in cloudflare, create an **account** API token from the "Edit zone DNS"
   template, limited to your zone, with no expiry.

3. create the state directory on the cephfs mount:

    ```bash
    sudo mkdir -m 700 /mnt/docker-cephFS/acme_synology
    ```

4. create the secrets on a manager, type each value, then Ctrl-D:

    ```bash
    docker secret create acme_synology_cf_token_v1 -
    docker secret create synology_acme_password_syn02_v1 -
    ```

5. deploy the stack below.

6. on the node running the task, open a shell in the container:

    ```bash
    docker exec -it $(docker ps -q -f name=acme_synology_acme-sh) sh
    ```

7. find the DSM certificate to replace. DSM matches it by description, and the
   default certificate often has an empty one:

    ```bash
    B=https://syn02.mydomain.com:5101/webapi/entry.cgi
    sid=$(curl -sk "$B" --data-urlencode api=SYNO.API.Auth --data-urlencode version=6 --data-urlencode method=login --data-urlencode account=acme --data-urlencode passwd@/run/secrets/dsm_password_syn02 --data-urlencode session=Core --data-urlencode format=sid | jq -r .data.sid)
    curl -sk "$B" --data-urlencode api=SYNO.Core.Certificate.CRT --data-urlencode version=1 --data-urlencode method=list --data-urlencode _sid="$sid" | jq -r '.data.certificates[] | "desc=\"\(.desc)\" default=\(.is_default) \(.subject.common_name) \(.valid_till)"'
    curl -sk "$B" --data-urlencode api=SYNO.API.Auth --data-urlencode version=6 --data-urlencode method=logout --data-urlencode session=Core --data-urlencode _sid="$sid" >/dev/null
    ```

8. issue the certificate, once:

    ```bash
    export CF_Token="$(cat /run/secrets/acme_synology_cf_token_v1)"
    /acmebin/acme.sh --issue --server letsencrypt --dns dns_cf -d syn02.mydomain.com --home /acmebin --config-home /acme.sh
    ```

9. register the hook and install the certificate, once. use the description from
   step 7, here the empty one:

    ```bash
    export SYNO_SCHEME=https SYNO_HOSTNAME=syn02.mydomain.com SYNO_PORT=5101 SYNO_CERTIFICATE=""
    /acmebin/acme.sh --deploy -d syn02.mydomain.com --ecc --deploy-hook synology_dsm_secret --home /acmebin --config-home /acme.sh
    ```

10. check DSM serves it:

    ```bash
    openssl s_client -connect syn02.mydomain.com:5101 -servername syn02.mydomain.com </dev/null 2>/dev/null | openssl x509 -noout -issuer -dates
    ```

why it's done that way:

- the `export CF_Token` in step 8 is because a `docker exec` shell doesn't get
  it. the entrypoint exports it to supercronic, which runs the renewals
- replacing the certificate that is already default keeps it default, so every
  DSM service bound to it moves to the new one. a new description would create a
  second certificate that nothing uses
- step 9 saves the scheme, host, port, description and `Le_DeployHook` in the
  certificate's settings. renewals need nothing else, the password comes from the
  secret each time
- for another NAS: add its password secret with a `dsm_password_<host>` target to
  the compose file, then repeat steps 7 to 10 with its host name

## The hook
mounted as a swarm config at `/acmebin/deploy/synology_dsm_secret.sh`. bump the
config `name` whenever the script changes.

```sh
#!/usr/bin/env sh
# acme.sh deploy hook: acme.sh's own synology_dsm hook, fed from swarm secrets.
#
# Mounted as a swarm config at /acmebin/deploy/synology_dsm_secret.sh. Register
# it once per certificate, with that NAS's settings in the environment:
#
#   SYNO_SCHEME=https SYNO_HOSTNAME=syn02.<domain> SYNO_PORT=5101 \
#   SYNO_CERTIFICATE='<description of the DSM cert to replace>' \
#   acme.sh --deploy -d syn02.<domain> --ecc --deploy-hook synology_dsm_secret
#
# synology_dsm saves scheme, hostname, port and description in the certificate's
# conf, so renewals find them there. Two things it does that this wrapper undoes:
#
#   - it saves SYNO_USERNAME and SYNO_PASSWORD in that conf too, base64 only,
#     which here means on CephFS. The password comes from
#     /run/secrets/dsm_password_<host> on every run instead, and both saved
#     copies are cleared afterwards. <host> is the first label of the
#     certificate's domain, so syn02.<domain> reads dsm_password_syn02. That
#     file name is a fixed `target:` in compose.yml, so rotating the secret
#     does not move it.
#   - it verifies DSM's certificate when it connects, and DSM is serving an
#     expired one exactly when a renewal has to land. HTTPS_INSECURE is scoped to
#     this deploy; acme.sh checks it per request, so ACME traffic is unaffected.

synology_dsm_secret_deploy() {
  _cdomain="$1"
  _syno_host="${_cdomain%%.*}"
  _syno_pwfile="/run/secrets/dsm_password_${_syno_host}"

  if [ ! -s "$_syno_pwfile" ]; then
    _err "No DSM password for $_syno_host: $_syno_pwfile is missing or empty"
    return 1
  fi

  SYNO_USERNAME="${SYNO_USERNAME:-acme}"
  SYNO_PASSWORD="$(cat "$_syno_pwfile")"
  HTTPS_INSECURE=1
  export SYNO_USERNAME SYNO_PASSWORD HTTPS_INSECURE

  # shellcheck disable=SC1091
  . "$_SCRIPT_HOME/deploy/synology_dsm.sh"
  synology_dsm_deploy "$@"
  _syno_rc=$?

  _cleardeployconf SYNO_PASSWORD
  _cleardeployconf SYNO_USERNAME
  return $_syno_rc
}
```

## Compose

```yaml
services:
  acme-sh:
    image: neilpang/acme.sh:latest@sha256:5e5713c64816ca2f2dde780df87bc7464e6f6a5995d457710131b688317b8352
    entrypoint:
      - /bin/sh
      - -c
      - set -e; CF_Token="$$(cat /run/secrets/acme_synology_cf_token_v1)"; export CF_Token; exec /entry.sh daemon
    volumes:
      - acme:/acme.sh
    configs:
      - source: synology_dsm_secret_hook
        target: /acmebin/deploy/synology_dsm_secret.sh
    secrets:
      - acme_synology_cf_token_v1
      - source: synology_acme_password_syn02_v1
        target: dsm_password_syn02
    deploy:
      mode: replicated
      replicas: 1

configs:
  synology_dsm_secret_hook:
    file: ./synology_dsm_secret.sh
    name: acme_synology_hook_v1

secrets:
  acme_synology_cf_token_v1:
    external: true
  synology_acme_password_syn02_v1:
    external: true

volumes:
  acme:
    driver: local
    driver_opts:
      type: none
      device: "/mnt/docker-cephFS/acme_synology"
      o: bind
```

- the entrypoint uses a plain assignment under `set -e`, so an unreadable secret
  stops the container instead of starting one that can't renew
- `exec /entry.sh daemon` runs supercronic, which runs `acme.sh --cron` four
  times a day and passes its environment to the job
- the image is pinned by digest, renovate opens a PR when it changes
