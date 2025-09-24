import os
import sys
import time
from pathlib import Path

_PATH = "."
_STEP_TIME = 5  # sec

# 1             2        3          4      5            6           7           8
#               STEP     TOTAL      WALL      STABLE    CRITICAL    KINETIC      TOTAL
# INCREMENT     TIME      TIME      TIME   INCREMENT     ELEMENT     ENERGY     ENERGY

# 1             2        3          4      5            6           7           8       9
#               STEP     TOTAL      WALL      STABLE    CRITICAL    KINETIC      TOTAL    PERCENT
# INCREMENT     TIME      TIME      TIME   INCREMENT     ELEMENT     ENERGY     ENERGY  CHNG MASS

_COLS_IN_STA = 1  # auto 8 / 9
_CRITICAL_ELEMENT_COL = 8 - 3
stats = []
folder_path = Path(_PATH)

# waiting for *.com and *.sta
print("[+] waiting for files...", end="\r", flush=True)
while True:

    def chk(ext):
        return [
            f.name for f in folder_path.iterdir() if f.is_file() and f.suffix == ext
        ]

    com_file = chk(".com")
    sta_file = chk(".sta")

    if com_file and sta_file:
        com_file = com_file[0]
        sta_file = sta_file[0]
        break

    time.sleep(1)


def text_append(path, data):
    with open(path, "a", encoding="utf-8") as f:
        f.write(data + "\n")


def time_fmt(seconds):
    intervals = (
        ("d", 86400),  # 60 * 60 * 24
        ("h", 3600),  # 60 * 60
        ("m", 60),
        ("s", 1),
    )
    result = []
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds %= count
            result.append(f"{int(value)}{name}")
    return " ".join(result) if result else "0 sec"


def diff_sec(file1=com_file, file2=sta_file):
    ctime1 = os.path.getmtime(file1)
    ctime2 = os.path.getmtime(file2)
    return abs(ctime1 - ctime2)


def is_str_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def eta():
    def estimate_eta(v_done, r_elapsed, v_total):
        if v_done == 0:
            return 0
        return r_elapsed / v_done * (v_total - v_done)

    global _COLS_IN_STA, stats
    stats = []
    frame_str = ""

    with open(sta_file, "r") as f:
        for l in f.readlines():
            l = l.rstrip()

            if "***ERROR" in l:
                return "[-] error, see .sta"

            if "THE ANALYSIS HAS COMPLETED SUCCESSFULLY" in l:
                return "[+] done!"

            if "Output Field Frame Number" in l:
                frame_str = l

            l = l.split()

            if not l or len(l) != _COLS_IN_STA:
                continue

            # int check (INCREMENT, CRITICAL ELEMENT)
            if not is_str_int(l[0]) or not is_str_int(l[_CRITICAL_ELEMENT_COL]):
                continue

            stats.append(l)

    if not stats:
        if _COLS_IN_STA == 8:
            _COLS_IN_STA = 9
        else:
            _COLS_IN_STA = 8
        return "[-] waiting for stats"

    if not frame_str:
        return "[-] no frames"

    if not int(stats[-1][0]):
        return "[-] no increments"

    f = frame_str.split()
    f_now = int(f[4].strip().rstrip(","))  # '200,' => 200
    f_all = int(f[6].strip().rstrip(","))
    # f_time = float(f[-1])

    v_done = float(stats[-1][1])  # virtual seconds
    r_elapsed = diff_sec()  # irl seconds
    v_total = _STEP_TIME  # step seconds

    eta = int(estimate_eta(v_done, r_elapsed, v_total))
    speed = v_done / r_elapsed

    inc_time = float(stats[-1][1])  # done 'inc_time' of 'step_time'
    inc_delta = abs(float(stats[-2][0]) - float(stats[-1][0]))

    r = f"{f_now} / {f_all} [{stats[-1][0]}] ({inc_time}s) (Δ{int(inc_delta)}) ({int(speed * 1000000)}v) [RUN: {time_fmt(r_elapsed)}, ETA: {time_fmt(eta)}]"

    return r


if __name__ == "__main__":
    try:
        text_append("log.txt", "")
        old = ""
        while True:
            new = eta()
            if old != new:
                old = new
                print(new)
                text_append("log.txt", new)

            time.sleep(1)

    except KeyboardInterrupt:
        print("[!] stopping")
        sys.exit()
