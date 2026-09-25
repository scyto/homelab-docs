---
title: "acme.sh for an ASRock Rack BMC"
---

# acme.sh for an asrock rack BMC

!!! note "secrets"
    i make my secrets from my own [secret store](../secrets/index.md), which
    only fits my setup. the `docker secret create` commands here are plain
    swarm: use them, or however you normally make secrets.

[acme.sh](https://github.com/acmesh-official/acme.sh) keeps a real certificate on
my ASRock Rack BMC (the AMI MegaRAC web UI, firmware 11.02). it renews over
cloudflare DNS, and a deploy hook installs every renewal on the BMC. after the
first run there is nothing to do by hand. it runs as one replica, anywhere on
the swarm.

--8<-- "blocks/swarm/acme_asrock_bmc/compose.yml.md"

## before you deploy

1. give acme.sh an account on the BMC with Administrator privilege, and KVM and
   virtual media turned off

    - the BMC's SSL page disables every control for anything less
    - mine is a dedicated account, `acme-sh`, not the built in admin

2. create the state directory on the cephfs mount:

    ```bash
    sudo mkdir -m 700 /mnt/docker-cephFS/acme_asrock_bmc_acme
    ```

    - acme.sh keeps its CA account, the certificate, its key and the renewal
      settings there, and the cloudflare token once it has used it

3. create the password secret on a manager, type the password, then Ctrl-D:

    ```bash
    docker secret create asrock_bmc_password_v2 -
    ```

    - swarm secrets can't be changed, so a new password goes in a new secret,
      `_v3`. `ASROCK_BMC_PASSWORD_FILE` in the compose names the one in use

4. set `CF_Account_ID` to your cloudflare account id. it's on the right of any
   zone's overview page, under API

    - with a token, acme.sh needs the account id or the zone id to find the
      zone, and the account id covers every zone in the account

## the first certificate

do this once, after the first deploy:

1. on the node running the task, open a shell in the container:

    ```bash
    docker exec -it $(docker ps -q -f name=acme_asrock_bmc_acme-sh) sh
    ```

2. issue the certificate:

    ```bash
    export CF_Token="<cloudflare token>"
    /acmebin/acme.sh --issue --server letsencrypt --dns dns_cf -d asrock-bmc.mydomain.com --home /acmebin --config-home /acme.sh
    ```

    - the token needs DNS edit on the zone: Zone > DNS > Edit on a user token,
      DNS Write on an account-owned token
    - acme.sh saves the token in `/acme.sh/account.conf`, and renewals read it
      from there
    - `--server letsencrypt` is saved with the certificate, so renewals stay
      with let's encrypt. without it acme.sh uses zerossl

3. register the hook. this also installs the certificate straight away:

    ```bash
    /acmebin/acme.sh --deploy -d asrock-bmc.mydomain.com --ecc --deploy-hook asrock_bmc --home /acmebin --config-home /acme.sh
    ```

    - `--deploy-hook` saves `Le_DeployHook` in the certificate's settings, and
      every renewal after that runs the hook by itself
    - a `--deploy` run by hand has to name the hook every time. renewals read
      the saved one

## the hook

the hook uploads with the same call that the BMC web UI's SSL page makes. it
doesn't use redfish: on this firmware redfish `ReplaceCertificate` takes a
certificate and no private key, so it can't install a certificate whose key
acme.sh generated.

the hook reads the password from the file that `ASROCK_BMC_PASSWORD_FILE` names,
and hands it to curl as a file, never as an argument. see
[secrets](../secrets/index.md).

it's mounted as a swarm config at `/acmebin/deploy/asrock_bmc.sh`, which is
where acme.sh looks for deploy hooks. swarm configs can't be changed, so bump
the config `name` whenever the script changes.

--8<-- "blocks/swarm/acme_asrock_bmc/asrock_bmc.sh.md"

## how it runs

- `command: daemon` runs supercronic, which runs `acme.sh --cron` four times a
  day
- nothing is published. the container only calls out: to the CA, cloudflare and
  the BMC
- `ASROCK_BMC_URL` is the BMC's IPv4 address, because my overlay networks have
  no IPv6
- the image is pinned by digest, renovate opens a PR when it changes

## checking it

the BMC should serve the new certificate, issued by let's encrypt:

```bash
openssl s_client -connect asrock-bmc.mydomain.com:443 -servername asrock-bmc.mydomain.com </dev/null 2>/dev/null | openssl x509 -noout -issuer -dates
```

[gatus](../monitoring/gatus.md#checking-a-job-by-its-result) checks the same
certificate every hour, with verification on, and goes red with less than 21
days left. acme.sh renews with 30 days left, so red means about nine days of
failed renewals.
