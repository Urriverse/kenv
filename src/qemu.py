import os
import re
import subprocess
from pathlib import Path
from core import get_target_dir
from utils import status, finished, error


def run_qemu(root: Path, profile_name: str):
    target_dir = get_target_dir(root)
    iso = target_dir / "x86_64-unknown-none" / profile_name / "image.iso"
    if not iso.is_file():
        error(f"ISO not found: {iso}")

    elf_path = target_dir / "x86_64-unknown-none" / profile_name / "kernel"
    if not elf_path.exists():
        elf_path = target_dir / "x86_64-unknown-none" / "debug" / "kernel"

    kvm = os.access("/dev/kvm", os.W_OK)
    if kvm:
        status("Available", "KVM")

    finished("guest startup")
    print("-" * 80)

    qemu_cmd = [
        "qemu-system-x86_64",
        "-device", "isa-debug-exit,iobase=0x501,iosize=0x01",
        "-no-reboot",
        "-cdrom", str(iso),
        "-boot", "d",
        *(["--enable-kvm"] if kvm else []),
        "-cpu", "host",
        "-m", "2G",
        "-smp", "4",
        "-serial", "stdio",
        "-vga", "std",
        "-machine", "q35,accel=kvm:tcg",
        "-device", "ahci,id=ahci",
        "-rtc", "base=utc",
    ]

    proc = subprocess.Popen(
        qemu_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    
    cpu_re = re.compile(r'CPU #(\d+)')
    begin_re = re.compile(r'\$\$ST:BEGIN\$\$')
    end_re = re.compile(r'\$\$ST:END\$\$')
    addr_re = re.compile(r'(#\d+\s+)(0x[0-9a-fA-F]+)')

    inside_stack = False
    stack_cpu = None
    addr_cache = {}

    def resolve_addr(addr: str) -> str:
        if addr in addr_cache:
            return addr_cache[addr]
        try:
            output = subprocess.check_output(
                ["addr2line", "-e", str(elf_path), "-f", "-i", "-p", "-C", addr],
                stderr=subprocess.DEVNULL,
                text=True,
                env={'LANG': 'C'},
            ).strip()
            
            if output.startswith(("/", "..")):
                output = output.split("/")[-1]
            result = output
        except subprocess.CalledProcessError:
            result = addr
        addr_cache[addr] = result
        return result

    try:
        for line in iter(proc.stdout.readline, ''):
            if not inside_stack:
                if begin_re.search(line):
                    m = cpu_re.search(line)
                    if m:
                        stack_cpu = m.group(1)
                        inside_stack = True
                else:
                    print(line, end='', flush=True)
            else:
                if end_re.search(line):
                    inside_stack = False
                    stack_cpu = None
                    continue

                m = cpu_re.search(line)
                if m and m.group(1) != stack_cpu:
                    continue

                def repl(match):
                    prefix = match.group(1)
                    addr = match.group(2)
                    resolved = resolve_addr(addr)
                    return f"{prefix}{resolved}"

                new_line = addr_re.sub(repl, line)
                print(new_line, end='', flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        proc.terminate()
        proc.wait()
