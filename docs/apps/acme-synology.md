---
title: "acme.sh for Synology DSM"
---

# acme.sh for synology DSM

!!! note "secrets"
    i make my secrets from my own [secret store](../secrets/index.md), which
    only fits my setup. the `docker secret create` commands here are plain
    swarm: use them, or however you normally make secrets.

[acme.sh](https://github.com/acmesh-official/acme.sh) renews my synology NAS
certificates and installs them in DSM, through its `synology_dsm` deploy hook
and a small wrapper, see [the hook](#the-hook).

i run it on the swarm, not in a container on the NAS: on the swarm it's in git,
it fails over between nodes, and it's one place to look. it runs as one
replica, anywhere on the swarm.

--8<-- "blocks/swarm/acme_synology/compose.yml.md"

## before you deploy

1. on each NAS, create a local user `acme` in the administrators group, with no
   2-step verification and no password expiry

    - the hook logs in with the password alone and can't answer a code

2. in cloudflare, create an account API token from the "Edit zone DNS"
   template, limited to your zone, with no expiry

    - that gives it DNS Write on the zone, which is all acme.sh needs

3. set `CF_Account_ID` to your cloudflare account id. it's on the right of any
   zone's overview page, under API

    - with a token, acme.sh needs the account id or the zone id to find the
      zone, and the account id covers every zone in the account

4. create the state directory on the cephfs mount:

    ```bash
    sudo mkdir -m 700 /mnt/docker-cephFS/acme_synology
    ```

    - acme.sh keeps its CA account, the certificates, their keys and the renewal
      settings there, and the cloudflare token once it has used it

5. create the secrets on a manager, type each value, then Ctrl-D:

    ```bash
    docker secret create acme_synology_cf_token_v1 -
    docker secret create synology_acme_password_syn02_v1 -
    ```

    - acme.sh only reads `CF_Token` from the environment, so the entrypoint
      reads the token's secret and exports it. see [secrets](../secrets/index.md)
    - each DSM password is mounted at a fixed file name, `dsm_password_<host>`.
      the wrapper takes `<host>` from the first label of the certificate's
      domain, so `syn02.mydomain.com` reads `dsm_password_syn02`

## the first certificate

do this once per NAS, after the first deploy:

1. on the node running the task, open a shell in the container:

    ```bash
    docker exec -it $(docker ps -q -f name=acme_synology_acme-sh) sh
    ```

2. find the DSM certificate to replace. DSM matches it by description, and the
   default certificate often has an empty one:

    ```bash
    B=https://syn02.mydomain.com:5101/webapi/entry.cgi
    sid=$(curl -sk "$B" --data-urlencode api=SYNO.API.Auth --data-urlencode version=6 --data-urlencode method=login --data-urlencode account=acme --data-urlencode passwd@/run/secrets/dsm_password_syn02 --data-urlencode session=Core --data-urlencode format=sid | jq -r .data.sid)
    curl -sk "$B" --data-urlencode api=SYNO.Core.Certificate.CRT --data-urlencode version=1 --data-urlencode method=list --data-urlencode _sid="$sid" | jq -r '.data.certificates[] | "desc=\"\(.desc)\" default=\(.is_default) \(.subject.common_name) \(.valid_till)"'
    curl -sk "$B" --data-urlencode api=SYNO.API.Auth --data-urlencode version=6 --data-urlencode method=logout --data-urlencode session=Core --data-urlencode _sid="$sid" >/dev/null
    ```

3. issue the certificate:

    ```bash
    export CF_Token="$(cat /run/secrets/acme_synology_cf_token_v1)"
    /acmebin/acme.sh --issue --server letsencrypt --dns dns_cf -d syn02.mydomain.com --home /acmebin --config-home /acme.sh
    ```

    - a `docker exec` shell doesn't get the token, hence the export. the
      entrypoint exports it to supercronic, which runs the renewals.
      `CF_Account_ID` is in the service's environment, which the shell does get

4. register the hook and install the certificate. use the description from
   step 2, here the empty one:

    ```bash
    export SYNO_SCHEME=https SYNO_HOSTNAME=syn02.mydomain.com SYNO_PORT=5101 SYNO_CERTIFICATE=""
    /acmebin/acme.sh --deploy -d syn02.mydomain.com --ecc --deploy-hook synology_dsm_secret --home /acmebin --config-home /acme.sh
    ```

    - replacing the certificate that is already default keeps it default, so
      every DSM service bound to it moves to the new one. a new description
      would create a second certificate that nothing uses
    - this saves the scheme, host, port, description and `Le_DeployHook` in the
      certificate's settings. renewals need nothing else, because the password
      comes from the secret each time

to add another NAS, add its password secret with a `dsm_password_<host>` target
to the compose file, then repeat steps 2 to 4 with its host name.

## the hook

the wrapper does two things acme.sh's `synology_dsm` hook doesn't:

- it reads the DSM password from a swarm secret on every run. left alone,
  `synology_dsm` saves the username and password in the certificate's settings
  on cephfs, only base64 encoded. the wrapper clears them after each deploy
- it skips certificate verification for the deploy only, because a renewal has
  to land even while DSM is serving an expired certificate

it's mounted as a swarm config at `/acmebin/deploy/synology_dsm_secret.sh`. bump
the config `name` whenever the script changes.

--8<-- "blocks/swarm/acme_synology/synology_dsm_secret.sh.md"

## how it runs

- the entrypoint uses a plain assignment under `set -e`, so an unreadable secret
  stops the container instead of starting one that can't renew
- `exec /entry.sh daemon` runs supercronic, which runs `acme.sh --cron` four
  times a day and passes its environment to the job
- nothing is published. the container calls the CA, cloudflare, and each DSM on
  its HTTPS port. mine use 5101, and the default is 5001
- the image is pinned by digest, renovate opens a PR when it changes

## checking it

DSM should serve the new certificate:

```bash
openssl s_client -connect syn02.mydomain.com:5101 -servername syn02.mydomain.com </dev/null 2>/dev/null | openssl x509 -noout -issuer -dates
```

[gatus](../monitoring/gatus.md#checking-a-job-by-its-result) checks the same
certificate every hour, with verification on, and goes red with less than 21
days left. acme.sh renews with 30 days left, so red means about nine days of
failed renewals.
