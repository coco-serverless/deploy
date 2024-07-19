from invoke import task
from os.path import join
from subprocess import run
from tasks.util.env import BIN_DIR, PROJ_ROOT, KATA_ROOT

# refer to 
# https://github.com/coconut-svsm/svsm/blob/main/Documentation/docs/installation/INSTALL.md

QEMU_IMAGE_TAG = "qemu-igvm-build"
DATA_DIR = join(KATA_ROOT, "coconut", "qemu-svsm", "share")

@task
def build(ctx):
    print(DATA_DIR)
    docker_cmd = "docker build --build-arg QEMU_DATADIR={} -t {} -f {} .".format(
        DATA_DIR, QEMU_IMAGE_TAG, join(PROJ_ROOT, "docker", "coconut", "qemu.dockerfile")
    )
    run(docker_cmd, shell=True, check=True, cwd=PROJ_ROOT)
    
    tmp_ctr_name = "tmp-qemu-igvm-run"
    docker_cmd = "docker run -td --name {} {}".format(tmp_ctr_name, QEMU_IMAGE_TAG)
    run(docker_cmd, shell=True, check=True)
    copy_from_container(tmp_ctr_name, "/root/bin/qemu-svsm/bin/qemu-system-x86_64", join(BIN_DIR, "qemu-system-x86_64-igvm"))
    copy_from_container(tmp_ctr_name, f"{DATA_DIR}/.", DATA_DIR)
    run("docker rm -f {}".format(tmp_ctr_name), shell=True, check=True)

def copy_from_container(ctr_name, ctr_path, host_path):
    docker_cmd = "docker cp {}:{} {}".format(
        ctr_name,
        ctr_path,
        host_path,
    )
    run(docker_cmd, shell=True, check=True)

@task
def guest(ctx, guest_img_path=join(PROJ_ROOT, "ubuntu-guest.qcow2")):
    qemu_path = join(BIN_DIR, "qemu-system-x86_64-igvm")
    igvm_path = join(BIN_DIR, "coconut-qemu.igvm")
    
    qemu_cmd = [
        "sudo", 
        qemu_path, 
        "-enable-kvm",
        "-cpu EPYC-v4",
        "-machine q35,confidential-guest-support=sev0,memory-backend=ram1",
        "-object memory-backend-memfd,id=ram1,size=8G,share=true,prealloc=false,reserve=false",
        "-object sev-snp-guest,id=sev0,cbitpos=51,reduced-phys-bits=1,igvm-file={}".format(igvm_path),
        "-smp 8",
        "-no-reboot",
        "-netdev user,id=vmnic -device e1000,netdev=vmnic,romfile=",
        "-device virtio-scsi-pci,id=scsi0,disable-legacy=on,iommu_platform=on",
        "-device scsi-hd,drive=disk0,bootindex=0",
        "-drive file={},if=none,id=disk0,format=qcow2,snapshot=off".format(guest_img_path),
        "-serial stdio",
        "-serial pty",
        "-display none",
        "-vnc :1",
        #-vga std \
    ]
    qemu_cmd = " ".join(qemu_cmd)

    print(qemu_cmd)
    run(qemu_cmd, shell=True, check=True)