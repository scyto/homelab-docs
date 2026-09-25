---
title: "EFI / BIOS Changes"
source_gist: https://gist.github.com/scyto/042c8c41b23bd5ddb31d1e4e38156dff
---

# EFI / BIOS changes


# These are the steps need to boot disks when the source hypervisort (in my case hyper-v) was using EFI and GPT disks.

Note wether the OS is Debian, Ubuntu, etc or Windows these steps change - the main difference will be step 7 and the name of the efi file.  You will only need to do this if the OS has been install on  a source hypervisor where EFI was enabled on VMs (e.g. gen2 VMs on Hyper-v)

## Steps

1. boot and entio bios to change UEFI order click in console as it says bootin and mash esc key until you see:

    ![image](../../assets/img/39326eed6869.png){ width="600" }

2. select boot maintenace manager above

    ![image](../../assets/img/9b237a7cdc61.png){ width="600" }

3. then select boot options.

    ![image](../../assets/img/0fdc4977f52a.png){ width="600" }

4. then select add boot option

    ![image](../../assets/img/205052ef11fe.png){ width="600" }

5. then select the boot volume (if you did [step 8](docker-swarm-vms.md) right there will be only one)

    ![image](../../assets/img/ee708bbb18ab.png){ width="600" }

6. select EFI

    ![image](../../assets/img/ec7ee06b8c08.png){ width="600" }

7. select the OS (in my case debian)

    ![image](../../assets/img/c04b5637b1c2.png){ width="600" }

8. select the right EFI file - in my case either grubx64.efi or shimx64.efi will work, i go with grubx64.efi

    ![image](../../assets/img/2bbce62ba75c.png){ width="600" }

9. add a description - anything will do, just rememebr it

    ![image](../../assets/img/4c735f4e782f.png){ width="600" }

10. commit changes and exit

    ![image](../../assets/img/97748e0793ca.png){ width="600" }

11. select change boot order:

    ![image](../../assets/img/97f4ec463e6d.png){ width="600" }

12. select what you see here ny default by pressing enter:

    ![image](../../assets/img/d9af985f7d82.png){ width="600" }

13. now highlught the entry you made:

    ![image](../../assets/img/c2ab256bc0b6.png){ width="574" }

14. and keep pressing + until it looks like this and press enter:

    ![image](../../assets/img/3e9f6cad4cb2.png){ width="571" }

15. you be back here, press F10 to save, and then esc and esc and   :

    ![image](../../assets/img/fd443b97602b.png){ width="600" }

16. when you are back here choose reset and your new vm will boot

    ![image](../../assets/img/92f22fe3754e.png){ width="600" }
