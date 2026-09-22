---
title: "acme.sh for an ASRock Rack BMC"
---

# acme.sh for an ASRock Rack BMC

## Description
[acme.sh](https://github.com/acmesh-official/acme.sh) keeps a real certificate on
my ASRock Rack BMC, the AMI MegaRAC web UI, firmware 11.02. it renews over
cloudflare DNS, and a deploy hook installs every renewal on the BMC, so nothing
has to be done by hand after the first run.

the hook uses the BMC web UI's own upload call, the one its SSL page makes, not
redfish. redfish `ReplaceCertificate` on this firmware takes a certificate and no
private key, so it can't install a certificate whose key acme.sh generated.

## State Considerations for SWARM
acme.sh keeps its CA account, the certificate, its key and the renewal settings
in `/acme.sh`, so that is a cephfs bind. the directory holds private keys and the
cloudflare token, so create it root owned, mode 700.

## Network Considerations
nothing is published. the container only makes outbound calls: the CA,
cloudflare, and the BMC. give the hook the BMC's IPv4 address, my overlay
networks have no IPv6.

## Placement Considerations
None, by default this template will result in a single replica

## Secrets
the BMC password is a swarm secret, the hook reads it from
`/run/secrets/asrock_bmc_password` and hands it to curl as a file, never as an
argument. see [secrets](../secrets/index.md).

the account needs **Administrator** privilege, the BMC's SSL page disables every
control for anything less. i'd use a dedicated account rather than the built in
admin, with KVM and virtual media turned off.

## Setup

1. create the state directory on the cephfs mount:

    ```bash
    sudo mkdir -m 700 /mnt/docker-cephFS/acme_asrock_bmc_acme
    ```

2. create the password secret on a manager, type the password, then Ctrl-D:

    ```bash
    docker secret create asrock_bmc_password -
    ```

3. deploy the stack below.

4. on the node running the task, open a shell in the container:

    ```bash
    docker exec -it $(docker ps -q -f name=acme_asrock_bmc_acme-sh) sh
    ```

5. issue the certificate, once:

    ```bash
    export CF_Token="<cloudflare token: DNS read and write on your zone>"
    /acmebin/acme.sh --issue --server letsencrypt --dns dns_cf -d bmc.mydomain.com --home /acmebin --config-home /acme.sh
    ```

6. register the hook, once. this also installs the certificate straight away:

    ```bash
    /acmebin/acme.sh --deploy -d bmc.mydomain.com --ecc --deploy-hook asrock_bmc --home /acmebin --config-home /acme.sh
    ```

why it's done that way:

- `--deploy-hook` saves `Le_DeployHook` in the certificate's settings, and every
  renewal after that runs the hook by itself
- a `--deploy` run by hand has to name the hook every time, renewals read the
  saved one
- acme.sh saves the cloudflare token in `/acme.sh/account.conf` after the first
  issue, which is one more reason the directory is mode 700
- mine was first issued from zerossl, acme.sh's default CA, and renews there.
  letsencrypt works the same way

## The hook
mounted as a swarm config at `/acmebin/deploy/asrock_bmc.sh`, which is where
acme.sh looks for deploy hooks. swarm configs can't be changed, so bump the
config `name` whenever the script changes.

```sh
#!/usr/bin/env sh
# acme.sh deploy hook: install the certificate on an ASRock Rack BMC
# (AMI MegaRAC SP-X web UI, verified on BMC firmware 11.02.0).
#
# Mounted as a swarm config at /acmebin/deploy/asrock_bmc.sh, which is where
# acme.sh's _findHook looks. Register it once per certificate:
#
#   acme.sh --deploy -d <domain> --ecc --deploy-hook asrock_bmc
#
# That saves Le_DeployHook in the certificate's conf, and renew() then runs this
# after every successful renewal, retrying a deploy that failed.
#
# It uses the web UI's own upload API rather than Redfish. Redfish
# ReplaceCertificate on this firmware takes a certificate string and no private
# key, so it cannot install a certificate whose key acme.sh generated. The web
# API takes both, which is what the BMC's SSL page does:
#   POST /api/session                         form login, returns CSRFToken
#   POST /api/settings/ssl/certificate        multipart new_certificate + new_private_key
#   GET, PUT /api/settings/ssl/certificate-info   the UI saves this straight after
#   DELETE /api/session
#
# Settings come from the service environment, not from the certificate conf, so
# nothing about the BMC is written to CephFS:
#   ASROCK_BMC_URL             e.g. https://192.168.1.92
#   ASROCK_BMC_USER
#   ASROCK_BMC_PASSWORD_FILE   default /run/secrets/asrock_bmc_password

asrock_bmc_deploy() {
  _cdomain="$1"
  _ckey="$2"
  _cfullchain="$5"

  if [ -z "$ASROCK_BMC_URL" ] || [ -z "$ASROCK_BMC_USER" ]; then
    _err "ASROCK_BMC_URL and ASROCK_BMC_USER must be set"
    return 1
  fi
  _asrock_pwfile="${ASROCK_BMC_PASSWORD_FILE:-/run/secrets/asrock_bmc_password}"
  if [ ! -s "$_asrock_pwfile" ]; then
    _err "BMC password file $_asrock_pwfile is missing or empty"
    return 1
  fi

  _asrock_tmp="$(mktemp -d)"
  # The password goes to curl as a file, never as an argument, so it does not
  # show in the process list. printf is a shell builtin here, and $(...) drops
  # any trailing newline the secret file carries.
  printf '%s' "$(cat "$_asrock_pwfile")" >"$_asrock_tmp/pw"

  _asrock_curl() {
    # --insecure because the BMC may be serving its factory certificate, and
    # that is exactly when this hook has to work.
    curl --silent --show-error --insecure --max-time 60 \
      --cookie "$_asrock_tmp/jar" --cookie-jar "$_asrock_tmp/jar" \
      --output "$_asrock_tmp/out" --write-out '%{http_code}' "$@"
  }

  _code="$(_asrock_curl --data-urlencode "username=$ASROCK_BMC_USER" \
    --data-urlencode "password@$_asrock_tmp/pw" "$ASROCK_BMC_URL/api/session")"
  rm -f "$_asrock_tmp/pw"
  if [ "$_code" != "200" ]; then
    _err "BMC login failed: HTTP $_code"
    rm -rf "$_asrock_tmp"
    return 1
  fi
  _csrf="$(jq -r .CSRFToken "$_asrock_tmp/out")"

  _code="$(_asrock_curl --header "X-CSRFTOKEN: $_csrf" \
    --form "new_certificate=@$_cfullchain" --form "new_private_key=@$_ckey" \
    "$ASROCK_BMC_URL/api/settings/ssl/certificate")"
  if [ "$_code" != "200" ] || [ "$(jq -r .cc "$_asrock_tmp/out" 2>/dev/null)" != "0" ]; then
    _err "BMC rejected the certificate: HTTP $_code $(head -c 200 "$_asrock_tmp/out")"
    _asrock_curl --header "X-CSRFTOKEN: $_csrf" --request DELETE "$ASROCK_BMC_URL/api/session" >/dev/null
    rm -rf "$_asrock_tmp"
    return 1
  fi

  _code="$(_asrock_curl --header "X-CSRFTOKEN: $_csrf" "$ASROCK_BMC_URL/api/settings/ssl/certificate-info")"
  if [ "$_code" = "200" ]; then
    cp "$_asrock_tmp/out" "$_asrock_tmp/info"
    _code="$(_asrock_curl --header "X-CSRFTOKEN: $_csrf" --header 'Content-Type: application/json' \
      --request PUT --data "@$_asrock_tmp/info" "$ASROCK_BMC_URL/api/settings/ssl/certificate-info")"
  fi
  if [ "$_code" != "200" ]; then
    _err "certificate uploaded, but saving certificate-info failed: HTTP $_code"
  fi

  _asrock_curl --header "X-CSRFTOKEN: $_csrf" --request DELETE "$ASROCK_BMC_URL/api/session" >/dev/null
  rm -rf "$_asrock_tmp"
  [ "$_code" = "200" ] || return 1
  _info "Certificate for $_cdomain installed on $ASROCK_BMC_URL"
  return 0
}
```

## Compose

```yaml
services:
  acme-sh:
    image: neilpang/acme.sh:latest@sha256:e1a4ac9fddb260b7171dd0c269790ae4561b6af35aa305b23cfdd98419ea1baf
    volumes:
      - acme:/acme.sh
    command: daemon
    environment:
      ASROCK_BMC_URL: https://192.168.1.92
      ASROCK_BMC_USER: <bmc account>
    configs:
      - source: asrock_bmc_hook
        target: /acmebin/deploy/asrock_bmc.sh
    secrets:
      - asrock_bmc_password
    deploy:
      mode: replicated
      replicas: 1

configs:
  asrock_bmc_hook:
    file: ./asrock_bmc.sh
    name: acme_asrock_bmc_hook_v1

secrets:
  asrock_bmc_password:
    external: true

volumes:
  acme:
    driver: local
    driver_opts:
      type: none
      device: "/mnt/docker-cephFS/acme_asrock_bmc_acme"
      o: bind
```

`command: daemon` runs supercronic, which runs `acme.sh --cron` four times a day.
the image is pinned by digest, renovate opens a PR when it changes.
