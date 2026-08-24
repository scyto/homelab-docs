---
title: "These are the steps need to boot disks when the source hypervisort (in my case hyper-v) was using EFI and GPT disks."
source_gist: https://gist.github.com/scyto/042c8c41b23bd5ddb31d1e4e38156dff
---

# These are the steps need to boot disks when the source hypervisort (in my case hyper-v) was using EFI and GPT disks.

Note wether the OS is Debian, Ubuntu, etc or Windows these steps change - the main difference will be step 7 and the name of the efi file.  You will only need to do this if the OS has been install on  a source hypervisor where EFI was enabled on VMs (e.g. gen2 VMs on Hyper-v)

## Steps

1. boot and entio bios to change UEFI order click in console as it says bootin and mash esc key until you see:

<img width="600" alt="image" src="../../../assets/img/39326eed6869.png">

2. select boot maintenace manager above

<img width="600" alt="image" src="../../../assets/img/9b237a7cdc61.png">

3. then select boot options.

<img width="600" alt="image" src="../../../assets/img/0fdc4977f52a.png">

4. then select add boot option

<img width="600" alt="image" src="../../../assets/img/205052ef11fe.png">

5. then select the boot volume (if you did step 12 right there will be only one)

<img width="600" alt="image" src="../../../assets/img/ee708bbb18ab.png">

6. select EFI

<img width="600" alt="image" src="../../../assets/img/ec7ee06b8c08.png">

7. select the OS (in my case debian)

<img width="600" alt="image" src="../../../assets/img/c04b5637b1c2.png">

8. select the right EFI file - in my case either grubx64.efi or shimx64.efi will work, i go with grubx64.efi

<img width="600" alt="image" src="../../../assets/img/2bbce62ba75c.png">

9. add a description - anything will do, just rememebr it

<img width="600" alt="image" src="../../../assets/img/4c735f4e782f.png">

10. commit changes and exit

<img width="600" alt="image" src="../../../assets/img/97748e0793ca.png">

11. select change boot order:

<img width="600" alt="image" src="../../../assets/img/97f4ec463e6d.png">

12. select what you see here ny default by pressing enter:

<img width="600" alt="image" src="../../../assets/img/d9af985f7d82.png">

13. now highlught the entry you made:

<img width="574" alt="image" src="../../../assets/img/c2ab256bc0b6.png">

14. and keep pressing + until it looks like this and press enter:

<img width="571" alt="image" src="../../../assets/img/3e9f6cad4cb2.png">

15. you be back here, press F10 to save, and then esc and esc and   :

<img width="600" alt="image" src="../../../assets/img/fd443b97602b.png">

16. when you are back here choose reset and your new vm will boot

<img width="600" alt="image" src="../../../assets/img/92f22fe3754e.png">
