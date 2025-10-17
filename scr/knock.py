import socket
import threading
import time
import sys
import subprocess as sp

# sequence that must be performed
KNOCK_SEQUENCE = [5464, 4356, 1234, 5464, 1234, 8888]
KNOCK_PORTS = list(set(KNOCK_SEQUENCE))

# time allocated for completing the entire sequence
SEQUENCE_TIMEOUT = 15

# time after the ports are closed again
EXPIRES_IN = 60 * 2

UNLOCK_PORTS = [
    3923,  # copyparty
    3389,  # rdp
    5900,  # vnc
]

# client data
client_knocks = {}
client_timeout = 0


def win_port(port, protocols=["TCP", "UDP"]):
    def run(c, ex=False):
        r = sp.run(
            c,
            shell=True,
            text=True,
            stdout=sp.PIPE,
            stderr=sp.PIPE,
            encoding="utf-8",
            errors="replace",
        )
        if ex and r.returncode != 0:
            print(f"[?] can't manage port {port}, are you admin?")
            sys.exit()

    block = port < 0
    port = abs(port)

    fw = ["netsh", "advfirewall", "firewall"]
    fw.insert(0, "sudo")  # choco install gsudo

    for protocol in protocols:
        allow_name = f'name="!_allow_{protocol}:{port}"'
        block_name = f'name="!_block_{protocol}:{port}"'

        allow_cmd = [
            "add",
            "rule",
            allow_name,
            "dir=in",
            "action=allow",
            f"protocol={protocol}",
            f"localport={port}",
        ]

        block_cmd = [
            "add",
            "rule",
            block_name,
            "dir=in",
            "action=block",
            "remoteip=0.0.0.0-192.167.255.255,192.169.0.0-255.255.255.255",  # lan
            f"protocol={protocol}",
            f"localport={port}",
        ]

        # recreate allow rule
        run(fw + ["delete", "rule", allow_name])
        run(fw + allow_cmd, True)

        if block:
            # create block rule
            run(fw + block_cmd, True)
            print(f"[-] {protocol} {port}")

        else:
            # remove block rule (allow)
            run(fw + ["delete", "rule", block_name])
            print(f"[+] {protocol} {port}")


port_manage = win_port  # todo iptables


def listen_on_port(port):
    global client_timeout

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    print(f"[!] lisening {port}")

    while True:
        data, addr = sock.recvfrom(1)
        ip = addr[0]

        print(f"[~] knock on {port} from {ip}")

        knocks = client_knocks.get(ip, [])
        now = time.time()

        # clean old attempts
        knocks = [k for k in knocks if now - k[1] < SEQUENCE_TIMEOUT]

        knocks.append((port, now))
        client_knocks[ip] = knocks

        # seq checking
        seq = [k[0] for k in knocks]
        if seq[-len(KNOCK_SEQUENCE) :] == KNOCK_SEQUENCE:
            print(f"[!] valid sequence from {ip}!")
            client_knocks[ip] = []  # reset after success attempt

            if not client_timeout:
                print(f"[!] opening {UNLOCK_PORTS}")
                for p in UNLOCK_PORTS:
                    port_manage(p)

            client_timeout = now + EXPIRES_IN


def check_expired():
    global client_timeout
    if client_timeout and client_timeout < time.time():
        print("[-] expired")
        for p in UNLOCK_PORTS:
            port_manage(-p)
        client_timeout = 0


if __name__ == "__main__":
    for p in UNLOCK_PORTS:
        port_manage(-p)

    for p in KNOCK_PORTS:
        port_manage(p, ["UDP"])

        threading.Thread(target=listen_on_port, args=(p,), daemon=True).start()

    try:
        while True:
            check_expired()
            time.sleep(1)

    except KeyboardInterrupt:
        print("[!] stopping")
        for p in UNLOCK_PORTS:
            port_manage(-p)
        for p in KNOCK_PORTS:
            port_manage(-p, ["UDP"])

"""
function knock() { nping --udp --count 1 --data-length 1 --dest-port $1 192.168.0.100 }

function sq()
{
    for num in 5464, 4356, 1234, 5464, 1234, 8888; do
        knock $num
    done
}
"""
