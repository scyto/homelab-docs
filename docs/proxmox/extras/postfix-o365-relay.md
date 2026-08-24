---
title: "Postfix M365 (Office 365) relay as LXC"
source_gist: https://gist.github.com/scyto/e0755b318ae84103c7c192a7a2dd1101
---

# Postfix M365 (Office 365) relay as LXC 
The purposes of this gist:
1. setup an smtp smarthost/relay that can send mail to Exchange Online 365 Office Outlook M365 (they keep renaming it)
2. setup postfix each proxmox host and backup server to use this relay
3. require the relay does authentications from devices like pve and pbs - having an open SMTP relay inside the network is not something i can bring myself to do  
4. And incidentally document the istall of a HA LXC based on debian

Also i am aware i probably over engineered this - after i had done this i realized postfix as shipped in PVE and PBS was attmepting to contact a variety of servers in my network based on DNS - i still haven't figured the logic out for that.... maybe all i needed was a relay and an MX record (and no config on PVE and PBS?)

**TODO**
- switch to TLS to protect creds in transit (this is gonna need certbot in the postfix VM)

[this gist is part of this series](../index.md)

## Prepare Exchange Online (or whatver it is called this week)
### ASSUMPTIONS:
* You have valid Office 365 Business Plan of some sort
* You have a mailbox called something like system@mydomain.com (this is must be a full mailbox, shared mailbox will not work)
* you haven't disabled SMTP Auth - See [this MS guide](https://learn.microsoft.com/en-us/exchange/clients-and-mobile-in-exchange-online/authenticated-client-smtp-submission) if the steps below can't be done.

### INSTRUCTIONS:
1. Open the [Microsoft 365 admin center](https://admin.cloud.microsoft/exchange#) and go to Users > Active users.
2. Select the user, and in the flyout that appears, click Mail.
3. In the Email apps section, click Manage email apps.
4. Set Authenticated SMTP setting to checked (aka enabled)

When you're finished, click Save changes.


## Install Debian LXC (HA Mode)

### Download CT Template
1. Navigate to `Datacenter > pve node`
2. select your local or ceph storage where you store ISOs and CT templates (for me this is my ISOs-Templates disk)
3. click `CT Templates`
4. click `templates`
5. donwnload  `debian-12-standard_12.0-1_amd64`
6. wait for download to finish


### Create CT
1. click `create CT` in upper right of pve console
2. choose a node (any node will do if you followed all my other gists)
3. give it a CT ID
4. hostname = `postfix.mydomain.com`
5. give is a password and optionally your ssh public key (if you want to login via an ssh client)
6. click `next`
7. choose your storage location and the debian 12 template downloaded earlier
8. click `next`
9. For storage set it to your ceph rbd (in my case vm-disks) (if you only have local storage use that)
10. leave other settings at default
11. click `next`
12. memory leave as defaults and click `next`
13. set networking tab as you prefer and click `next`(also don't forget to put the name of the client in your local DNS server - if you don't have a local DNS sever make one)
14. DNS tab - i prefer use host settings change as you see fit and click `next`
15. check start after created and click finish

### Make HA 
1. this can be skipped if you don't have a HA cluster
2. navigate to `Datacenter > HA`
3. click `add` under resources
4. select the containe VMID in the VM box
5. add to a cluster group e.g `ClusterGroup1` (this was created in an ealier gist)
6. set requested state = `started`
7. click `add`

## Install and Configure Postifx Relay to connect to M365
1. login to container you just created

### Prepare the Container
1. As always issue a `apt update && apt upgrade`
2. Install requirements with `apt install postfix libsasl2-modules mailutils rsyslog`
3. add a new user to the system with `add user system`
4. give the user a password with `passwd system`

### Configure Postfix
1. edit the postifix config file with `nano /etc/postfix/main.cf`
2. change the following
```
mydomain = mydomain.com
myhostname = postfix.mydomain.com
relayhost = smtp.office365.com:587
compatibility_level = 0
```
3. add the following
```
smtp_use_tls = yes
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_tls_CApath = /etc/ssl/certs
smtp_sasl_security_options = noanonymous, noplaintext
smtp_sasl_tls_security_options = noanonymous
mynetworks = 127.0.0.0/8, 192.168.1.0/24
inet_interfaces = all
smtpd_sasl_auth_enable = yes
smtpd_sasl_path = smtpd
smtpd_sasl_security_options = noanonymous
smtpd_sasl_local_domain = $myhostname
smtpd_recipient_restrictions = permit_sasl_authenticated,reject_unauth_destination,check_relay_domains  
```
4. save the file
5. create a password file with `nano /etc/postfix/sasl_passwd`
6. Add the following:
```
smtp.office365.com system@mydomain.com:mypassword
```
6. save the file
7. run `postmap /etc/postfix/sasl_passwd`
8. edit the aliases file with `nano /etc/aliases`
```
postmaster: root
webmaster: root
root: system@mydomain.com
system: system@mydomain.com
```
8. save the file
9. run `newaliases`
10. reload postfix with `postfix reload`

#### Test by issuing this comamnd
`echo "this is a test email" | mail -s "pve node X test email" to@whomever.com -a "FROM:system@mydomain.com"`

Replace my placeholders to match your env

## Confgure postfix on each proxmox node and backup server
1. `apt install libsasl2-modules`
2. edit the postifix config with `nano /etc/postfix/main.cf`
3. change these lines
```
relayhost = postfix.mydomain.com:25
compatibility_level = 3.6
```
4. add these lines
```
smtp_sasl_auth_enable = yes
smtp_sasl_security_options = 
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
```
4. save the file
5. create the sasl password file `nano /etc/postfix/sasl_passwd`
7. add the following
```
postfix.mydomain.com system:<password>
```
7. save the file
8. run `postmap /etc/postfix/sasl_passwd` to process the password file
9. restart postfix service `systemctl restart postfix`

### Test
Test by issuing this comamnd
`echo "this is a test email" | mail -s "pve node X test email" to@whomever.com -a "FROM:system@mydomain.com"`

Replace my placeholders to match your env

## set from name on on cluster
1. Navigate to `Datacenter > options`
2. doubleclick `email from address`
3. set emal as `system@mydomain.com` and click `ok`

(repeat on PBS in `Configuration > Other`)
