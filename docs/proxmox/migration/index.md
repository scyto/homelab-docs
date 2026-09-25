---
title: "Migrating from Hyper-V"
---

# migrating from hyper-v

these are my notes from moving off hyper-v in august and september 2023, kept as
written. the swarm page is from the glusterFS era. the swarm's shared storage is
cephFS now, see
[cephFS - virtiofs passthrough](../cephfs-virtiofs-passthrough.md).

read them in this order:

1. [windows gen2 VMs](windows-gen2-from-hyperv.md) - the method
2. [domain controller 2](domain-controller-2.md) - the first real server i moved
3. [domain controller 1 (FSMO/CA)](domain-controller-1.md)
4. [windows admin center VM](admin-center-vm.md)
5. [home assistant](home-assistant.md)
6. [the docker swarm VMs](docker-swarm-vms.md), then its
   [EFI / BIOS changes](docker-swarm-vms-efi-bios.md)
