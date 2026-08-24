---
title: "Setup HTTPS Certs with ACME"
source_gist: https://gist.github.com/scyto/7a67e48ae2c6b1cffdefb8f984734b5d
---

# Setup HTTPS Certs with ACME
I use Cloudflare as my external DNS provider and will be using this for my challenge, if you don't use cloudlfare adjust accordingly.

[this gist is part of this series](../index.md)

## Create Account
1. navigate to `Datcenter > ACME`
2. under accounts click `add`
3. the account name is anything useful to you - i recommend using something like \<mydomain>-\<tld>-acme where mydomain is your DNS domain prefix and tld is the suffice (like com or net etc) so mydomain-com-acme
4. enter your email
5. accept the TOS and click `register` 

## Create Challenge Plugin
1. under 'challenge plugins' click `add`
2. set any name for the plugin ID, i chose to call mine CF-\<domain>-\<tld> (e.g CF-mydomain-com 
3. select DNS API = Cloudflare Managed DNS
4. fill in CF_Key=
5. Fill in CF_Token=
6. click `ok`

## Get Certificates
1. navigate to `Datacenter > pve1 > System > Certificates`
2. click `add`
3. Challenge type = DNS
4. Plugin = CF-mydomain-com (or whatver you called it)
5. create domain `pve1.mydomain.com`
6. click `create`
7. in the ACME section click `edit` next 'Using Account'
8. select the account you created (e.g. mydomain-com-acme)
9. click `apply`
10. now click `order certificates` to get a letsencrypt certificate. 

At this point it will create the DNS challenger, order the cert and then restart the web interface and if you did evertying right you mop jabe a cert.  repeat the steps on pve2 and pve3 remebering to set the name correctly
