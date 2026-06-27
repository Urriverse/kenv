"""
QEMU launcher with configuration.
"""
import os
import glob
from ..utils.log import *


def find_latest_image() -> str | None:
    """Find the most recently built image (osenv.iso or similar)."""
    build_dir = "build"
    candidates = glob.glob(os.path.join(build_dir, "*.iso"))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def build_qemu_command(image_path: str, config_env: dict[str, str],
                       extra_args: str | None = None) -> list[str]:
    """Construct QEMU command line."""
    qemu_cmd = [
        "qemu-system-x86_64",
        "-device",
        "isa-debug-exit,iobase=0x501,iosize=0x01",
        "-no-reboot",
        "-device", "ahci,id=ahci",
        "-rtc", "base=utc",
    ]

    if not config_env.get("NOVGA", "no").lower() in "notdisabled0false":
        qemu_cmd.extend(["-vga", "std"])
    
    # CPU
    cpu = config_env.get("QEMU_CPU", "host")
    qemu_cmd.extend(["-cpu", cpu])

    # Machine
    machine = config_env.get("QEMU_MACHINE", "q35,accel=kvm:tcg")
    qemu_cmd.extend(["-machine", machine])

    # Memory
    mem = config_env.get("QEMU_MEM", "512M")
    qemu_cmd.extend(["-m", mem])

    # Display
    display = config_env.get("QEMU_DISPLAY", None)
    if display is not None:
        qemu_cmd.extend(["-display", display])

    # Serial
    serial = config_env.get("QEMU_SERIAL", "stdio")
    qemu_cmd.extend(["-serial", serial])

    # Cores
    smp = config_env.get("QEMU_SMP", "4")
    qemu_cmd.extend(["-smp", smp])

    # KVM
    if config_env.get("QEMU_KVM", "").lower() in ("1", "true", "yes"):
        # Check if /dev/kvm exists
        if os.path.exists("/dev/kvm"):
            qemu_cmd.append("-enable-kvm")
        else:
            w("KVM requested but /dev/kvm not found, skipping.")

    # Drive
    qemu_cmd.extend(["-cdrom", image_path])

    # Extra user arguments
    if extra_args:
        qemu_cmd.extend(extra_args.split())

    return qemu_cmd
