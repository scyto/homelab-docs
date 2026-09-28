---
title: "Entra ID (Azure AD) Auth"
source_gist: https://gist.github.com/scyto/038b35c913018ee1cbd4dc62e49a6355
---

# Azure Active Directory (AAD) Auth
This gist assumes a working Azure AD (not Azure AD-DS is already up and fully configured)
This gist assumes working DNS / name resolution on your internal network.

[this gist is part of this series](../index.md)

## Create App Registrations
All of these steps will be done in the Azure Portal AAD UI

1. Select App Registration from the nav bar
2. Click new registration in the task pane
3. name it `proxmox`
4. set initial redirect URI to web https://node.mydomain.com:8006 (this assume you are not publishing externaly)
5. click register

    nav should change to the the proxmox  app reg

7. click certificans & secrets
8. click the client secrets tab
9. click new client secret
10. set description to say proxmox-auth
11. set expires to 730 days
12. copy the value `<a string hash>`
13. copy the secret id `<a guid>`

    **very important - you will never see the value again - must copy it down now**
  
14. click authentication in the left nav
15. add all the internally and externally accessible node names, in my case this is as follows for my 3 internal node names, the pbs server name and cluster name via internal nginx.

    ```
    https://pve1.mydomain.com:8006
    https://pve2.mydomain.com:8006
    https://pve3.mydomain.com:8006
    https://pbs.mydomain.com:8007
    https://cluster1.mydomain.com  
    ```  

16. nothing else needs to be changed here so click save once these have been added
17. navigate to overview > endpoints
18. Copy the OpenID Connect metadata document link and remove /.well-known/openid-configuration this part from the link, so you end up with something like this https://login.microsoftonline.com/{Your-Tenant-ID}/v2.0


## Add realm on PVE Cluster
1. go to `datacenter > realms` click `add` at the top of page  and select `OpenID Connect Server`
2. issuer URL = https://login.microsoftonline.com/{Your-Tenant-ID}/v2.0
3. realm is domain name 
4. client ID =  GUID (from AAD app reg > proxmox > overview > application (client ID)
5. client key = hashed value  (should be the secret value from earlier)
6. default = checked
7. autocreate users = checked
8. username claim = email or username (it gives same result in my system - the username will alwasy be name@mydomain.com)

## Create a Group
1. click `datacenter > permissions > groups>`
2. click `create`
3. name = admins
4. click `create`

## Assign Permissions to group
1. click `datacenter > permissions`
2. click `add`
3. path = /
4. group = admins
5. role = administrator
6. propogate = checked

## create user
1. user name = name@mydomain.com
2. realm = Azure AAD
3. Group = Admins
4. name = folks names of course
5. email = ususally the same as name@mydomain.com

## login with AAD!

## webauthn keys on every node

a security key or passkey is bound to one "relying party ID", set for the
whole cluster in datacenter → options → webauthn settings. i set it to the
domain, so every node's name and the cluster's name share it.

1. set it from a shell on any node:

    ```bash
    pvesh set /cluster/options --webauthn 'rp=mydomain.com,origin=https://mydomain.com,id=mydomain.com,allow-subdomains=1'
    ```

    - the settings dialog has no subdomain box, so `allow-subdomains` is only
      set this way, and saving the dialog again can drop it
    - changing the ID breaks every key registered under the old one. add a
      TOTP entry and recovery keys first

2. register the key again, from a name served on port 443. mine is the
   cluster's name through [traefik](../../apps/traefik.md)

    - the origin check compares the port, so a key works on names served on
      443 and not on a node's own `:8006`. i use TOTP there

if a key stops working, the web UI's second factor doesn't cover ssh or the
console. as root on a node, with `ENTRY_ID` set to an ID from the list:

```bash
pveum user tfa list root@pam
pveum user tfa delete root@pam --id "$ENTRY_ID"
pveum user tfa unlock root@pam
```

- `delete` without `--id` removes all of the user's entries, leaving a
  password-only login until you add them again
