import argparse
import ipaddress
import logging
import os
import platform
import shlex
import shutil
import socket
import subprocess as sp
import sys
import threading
import time
from typing import List, Tuple

"""
using:
    python knock.py -l knock.log \
        -k 1234 4444 1234 3333 5555 1234 \
        -u 80 3389 5900 -c DOCKER-USER
    
    # DOCKER-USER => for linux docker containers

knocking:
    apt install nmap

    knock() { 
        nping --udp --count 1 --data-length 1 --dest-port $1 192.168.0.100
    }

    sq() {
        for num in 1234 4444 1234 3333 5555 1234; do knock "$num"; done;
    }

    sqq() {
        while true; do sq; sleep 10; done;
    }

todo:
    - client mode
    - fix netsh slop
    - iptables / netsh check?

"""

client_knocks = {}
client_timeout = 0
sudo = ""


class NetshIPRangeBuilder:
    FULL_START = int(ipaddress.IPv4Address("0.0.0.0"))
    FULL_END = int(ipaddress.IPv4Address("255.255.255.255"))

    def __init__(self, allowed_patterns: List[str]):
        """
        allowed_patterns: list of patterns, for example [“192.168.*.*”, “10.*.*.*”]
        """
        self.allowed_patterns = allowed_patterns

    @staticmethod
    def _pattern_to_range(pat: str) -> Tuple[int, int]:
        """converts a pattern of the form '192.168.*.*' or '1.2.3.4' into a range (start_int, end_int)."""
        parts = pat.split(".")
        if len(parts) != 4:
            raise ValueError(f"incorrect template: {pat}")
        min_parts, max_parts = [], []
        for part in parts:
            if part == "*":
                min_parts.append(0)
                max_parts.append(255)
            else:
                n = int(part)
                if not (0 <= n <= 255):
                    raise ValueError(f"incorrect octet in {pat}: {part}")
                min_parts.append(n)
                max_parts.append(n)
        start = int(ipaddress.IPv4Address(".".join(map(str, min_parts))))
        end = int(ipaddress.IPv4Address(".".join(map(str, max_parts))))
        return start, end

    @staticmethod
    def _merge_ranges(ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """merges overlapping or adjacent ranges."""
        if not ranges:
            return []
        ranges_sorted = sorted(ranges, key=lambda x: x[0])
        merged = []
        cur_s, cur_e = ranges_sorted[0]
        for s, e in ranges_sorted[1:]:
            if s <= cur_e + 1:  # перекрываются или смежные
                cur_e = max(cur_e, e)
            else:
                merged.append((cur_s, cur_e))
                cur_s, cur_e = s, e
        merged.append((cur_s, cur_e))
        return merged

    def _complement_ranges(
        self, allowed: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """returns ranges that are not within the permitted range."""
        allowed_merged = self._merge_ranges(allowed)
        res = []
        cur = self.FULL_START
        for s, e in allowed_merged:
            if cur < s:
                res.append((cur, s - 1))
            cur = e + 1
        if cur <= self.FULL_END:
            res.append((cur, self.FULL_END))
        return res

    @staticmethod
    def _format_ranges_for_netsh(ranges: List[Tuple[int, int]]) -> str:
        """formats the list of ranges into a remoteip=... string."""
        if not ranges:
            return ""
        parts = [
            f"{ipaddress.IPv4Address(s)}-{ipaddress.IPv4Address(e)}" for s, e in ranges
        ]
        return "remoteip=" + ",".join(parts)

    def build(self) -> str:
        """main method: returns the string remoteip=... with prohibited ranges."""
        allowed = [self._pattern_to_range(p) for p in self.allowed_patterns]
        forbidden = self._complement_ranges(allowed)
        return self._format_ranges_for_netsh(forbidden)


def sp_exec(cmd: str | list, ex_handle: bool = False):
    log.debug(cmd)
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)

    try:
        p = sp.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            # shell=True,
            encoding="utf-8",
            errors="replace",
        )
        return p.stdout, p.stderr
    except sp.CalledProcessError as e:
        if ex_handle:
            cmd_fmt = " ".join(cmd)
            log.error(f"failed cmd, are you admin?: {cmd_fmt!r}")
            log.error(e)
            sys.exit(1)
        pass


def netsh(port: int, protocols: list = ["tcp", "udp"], allowed: list = []):
    global sudo

    block = port < 0
    port = abs(port)

    fw = f"{sudo} netsh advfirewall firewall"

    for protocol in protocols:
        protocol = protocol.upper()

        allow_name = f'name="!_alw_{protocol}-{port}"'
        block_name = f'name="!_blk_{protocol}-{port}"'

        allow_cmd = f"add rule {allow_name} dir=in action=allow \
            protocol={protocol} localport={port}"

        ip_range = NetshIPRangeBuilder(allowed)
        block_cmd = f"add rule {block_name} dir=in action=block \
            {ip_range.build()} protocol={protocol} localport={port}"

        # recreate allow rule
        sp_exec(f"{fw} delete rule {allow_name}")
        sp_exec(f"{fw} {allow_cmd}", True)

        if block:
            # create block rule
            log.info(f"[block] {protocol} {port}")
            sp_exec(f"{fw} {block_cmd}", True)

        else:
            # remove block rule (allow)
            log.info(f"[allow] {protocol} {port}")
            sp_exec(f"{fw} delete rule {block_name}")


def iptables_del_via_comm(comm: str, chk: bool = False):
    ip_l, _ = sp_exec(f"{sudo} iptables -L {ar.iptables_chain} --line-numbers", True)
    for line in ip_l.split("\n"):
        rule = line.split()
        if (
            len(rule) >= 3
            and rule[-3] == "/*"
            and rule[-2] == comm
            and rule[-1] == "*/"
        ):
            log.debug(f"[ipt del] {comm}")
            sp_exec(f"{sudo} iptables -D {ar.iptables_chain} {rule[0]}", True)

            # nums are now dismatched, recursing...
            iptables_del_via_comm(comm)
            break


def iptables(port: int, protocols: list = ["tcp", "udp"], allowed: list = []):
    """
    block:
        sudo iptables -I INPUT 1 -p udp --dport 1234 -s 192.168.0.0/16 -j ACCEPT
        sudo iptables -A INPUT -p udp --dport 1234 -j DROP

    unblock:
        sudo iptables -D INPUT -p tcp --dport 3923 -s 192.168.0.0/16 -j ACCEPT
        sudo iptables -D INPUT -p tcp --dport 3923 -j DROP
    """

    global sudo

    block = port < 0
    port = abs(port)

    for protocol in protocols:
        protocol = protocol.lower()

        allow_name = f"_alw_{protocol}-{port}"
        block_name = f"_blk_{protocol}-{port}"

        fw = f"{sudo} iptables -p {protocol} --dport {port}"

        ip_range = " ".join([f"-s {x}" for x in allowed])

        if block:
            log.info(f"[block] {protocol} {port}")
            iptables_del_via_comm(block_name)
            iptables_del_via_comm(allow_name)

            if allowed:
                sp_exec(
                    f"{fw} -m comment --comment {allow_name} -I {ar.iptables_chain} 1 -j ACCEPT {ip_range}",
                    True,
                )
            sp_exec(
                f"{fw} -m comment --comment {block_name} -A {ar.iptables_chain} -j DROP",
                True,
            )
        else:
            log.info(f"[allow] {protocol} {port}")
            iptables_del_via_comm(block_name)
            iptables_del_via_comm(allow_name)
            """
            if allowed:
                sp_exec(f"{fw} -D INPUT -j ACCEPT {ip_range}")
            sp_exec(f"{fw} -D INPUT -j DROP")
            """


def listen_on_port(port):
    global client_timeout

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    log.info(f"lisening {port}")

    while True:
        data, addr = sock.recvfrom(1)
        ip = addr[0]

        log.info(f"[knock] {ip}:{port}")

        knocks = client_knocks.get(ip, [])
        now = time.time()

        # clean old attempts
        knocks = [k for k in knocks if now - k[1] < ar.sequence_timeout]

        knocks.append((port, now))
        client_knocks[ip] = knocks

        # seq checking
        seq = [k[0] for k in knocks]
        if seq[-len(ar.knock_sequence) :] == ar.knock_sequence:
            log.info(f"[!] valid sequence from {ip}!")
            client_knocks[ip] = []  # reset after success attempt

            if not client_timeout:
                log.info(f"[!] opening {ar.unlock_ports}")
                for p in ar.unlock_ports:
                    port_set(p, allowed=ar.allowed_ips)

            client_timeout = now + ar.expires_in


def check_expired():
    global client_timeout
    if client_timeout and client_timeout < time.time():
        log.warning("[-] expired")
        for p in ar.unlock_ports:
            port_set(-p, allowed=ar.allowed_ips)
        client_timeout = 0


def clean():
    for action in ["alw", "blk"]:
        for protocol in ["udp", "tcp"]:
            for port in list(set(ar.unlock_ports + ar.knock_sequence)):
                log.info(f"[-] {action}_{protocol}-{port}")

                match platform.system():
                    case "Windows":
                        sp_exec(
                            f'{sudo} netsh advfirewall firewall delete rule \
                                name="!_{action}_{protocol.upper()}-{port}"'
                        )

                    case "Linux":
                        iptables_del_via_comm(f"_{action}_{protocol.lower()}-{port}")

    log.info("cleaned")


if __name__ == "__main__":
    # fmt: off
    ap = argparse.ArgumentParser()
    add = ap.add_argument

    add('-k', '--knock-sequence',   nargs='+', type=int, default=[], help='knock sequence that must be performed')
    add('-u', '--unlock-ports',     nargs='+', type=int, default=[], help='ports to unlock')
    add('-a', '--allowed-ips',      nargs='+', type=str, default=[], help='allowed ip\'s ("192.168.*.*" for windows, "192.168.0.0/16" for linux)') # todo: fix netsh
    add('-c', '--iptables-chain',   type=str,  default="INPUT",      help='iptables chain (ex: INPUT, DOCKER-USER)')
    add('-t', '--sequence-timeout', type=int, default=15,            help='time allocated for completing the entire sequence (in seconds)')
    add('-e', '--expires-in',       type=int, default=120,           help='time after the ports are closed again (in seconds)')
    add('-b', '--block-at-exit',    action='store_true',             help='block all ports at exit')

    add('-l', '--log',     type=str, default="", help='write log to file')
    add('-r', '--remove',  action='store_true',  help='remove all blocks / allows')
    add('-v', '--verbose', action='store_true',  help='verbose output (traces)')

    ar = ap.parse_args()
    # fmt: on

    log = logging.getLogger()
    log.setLevel(logging.DEBUG if ar.verbose else logging.INFO)

    formatter = logging.Formatter("%(asctime)s | %(levelname)7s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    log.addHandler(console_handler)

    if ar.log:
        file_handler = logging.FileHandler(ar.log, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        log.addHandler(file_handler)

    if not ar.knock_sequence:
        log.error("no knocks to knock, set with -k")
        sys.exit(1)

    if not ar.unlock_ports:
        log.error("no ports to unlock, set with -u")
        sys.exit(1)

    match platform.system():
        case "Windows":
            port_set = netsh

            import ctypes

            if not ctypes.windll.shell32.IsUserAnAdmin():
                if shutil.which("sudo"):
                    log.warning(
                        "no admin rights, but sudo found (expect slow netsh starts)"
                    )
                    sudo = "sudo"
                else:
                    s = "rerun as admin, or install gsudo"
                    if shutil.which("choco"):
                        s = s + " (via choco: choco install gsudo)"
                    log.error(s)
                    sys.exit(1)

        case "Linux":
            port_set = iptables

            if os.getuid() != 0:
                try:
                    assert shutil.which("sudo")

                    sp.run(
                        ["sudo", "-n", "true"],
                        check=True,
                        stdout=sp.DEVNULL,
                        stderr=sp.DEVNULL,
                    )

                    log.info("sudo mode on")
                    sudo = "sudo"
                except sp.CalledProcessError:
                    log.error("sudo installed, but pass is required")
                    sys.exit(1)
                except AssertionError:
                    log.error("sudo not found")
                    sys.exit(1)
                except Exception as e:
                    log.error(f"sudo chk err: {e}")
                    sys.exit(1)

        case _:
            log.error(f"platform {platform.system()!r} is not supported")
            sys.exit(1)

    if ar.remove:
        clean()
        sys.exit(0)

    for p in ar.unlock_ports:
        port_set(-p, allowed=ar.allowed_ips)

    for p in list(set(ar.knock_sequence)):
        port_set(p, ["udp"])
        threading.Thread(target=listen_on_port, args=(p,), daemon=True).start()

    try:
        while True:
            check_expired()
            time.sleep(1)

    except KeyboardInterrupt:
        log.warning("[!] stopping")

        if ar.block_at_exit:
            for p in ar.unlock_ports:
                port_set(-p, allowed=ar.allowed_ips)
            for p in list(set(ar.knock_sequence)):
                port_set(-p, ["udp"])
        else:
            clean()
