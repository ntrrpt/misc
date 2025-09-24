#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "requests",
#   "bs4",
#   "loguru",
# ]
# ///

import requests
import os
import subprocess
import sys
import re
import pathlib
import random
import string
from loguru import logger as log

MAIN_URL = None  # https://wapchan.org/cel
ARIA2_FILENAME = (
    "".join(random.choice(string.ascii_letters) for x in range(10)) + ".txt"
)

log.remove(0)
log.add(
    sys.stderr,
    format="<level>[{time:DD-MMM-YYYY HH:mm:ss}]</level> {message}",
    backtrace=True,
    diagnose=True,
    colorize=True,
    level=5,
)
log.add(
    "log.txt",
    format="[{time:DD-MMM-YYYY HH:mm:ss}] {message}",
    backtrace=True,
    diagnose=True,
    colorize=True,
    level=5,
)


def fileDel(filename):
    rem_file = pathlib.Path(filename)
    rem_file.unlink(missing_ok=True)


def add(dir, bin):
    with open(dir, "a", encoding="utf-8") as file:
        file.write(bin + "\n")


def str_cut(string, letters, postfix="..."):
    return string[:letters] + (string[letters:] and postfix)


def str_fix(string):
    return str_cut(re.sub(r'[/\\?%*:{}【】|"<>]', "", string), 200, "")


def dump_thread(th_url):
    global MAIN_URL
    images = []

    r = requests.get(th_url)

    try:
        r = r.json()["posts"]
    except:
        log.error(th_url)
        return

    dirname = str(r[0]["no"])
    if "sub" in r[0]:
        dirname += " " + str_fix(r[0]["sub"])

    for post in r:
        if "filename" not in post:
            continue

        f = f"{post['tim']} {post['filename']}{post['ext']}"  #  1725081265298 mpv-shot0001.jpg
        u = f"{MAIN_URL}/src/{post['tim']}{post['ext']}"  # https://wapchan.org/cel/src/1724962488992.jpg
        images.append([f, u])

    if not images:
        log.debug(f"{th_url} (no images)")
        return

    fileDel(ARIA2_FILENAME)

    for img in images:
        if img[1].endswith("deleted"):
            continue

        add(ARIA2_FILENAME, f"{img[1]}\n    out={img[0]}")
    add(ARIA2_FILENAME, f"{th_url}\n    out={dirname}.json")

    # dirname = 'kissu' + '/' + 'maho' + '/' + dirname

    aria2c_args = [
        "aria2c",
        f"--input-file={ARIA2_FILENAME}",
        f"--dir={dirname}",
        "--max-connection-per-server=1",
        "--max-concurrent-downloads=1",
        "--auto-file-renaming=false",
        "--remote-time=true",
        "--log-level=error",
        "--console-log-level=error",
        "--download-result=hide",
        "--summary-interval=0",
        "--file-allocation=none",
        #'--all-proxy=http://127.0.0.1:10809'
    ]

    log.debug(th_url)
    subprocess.run(aria2c_args)
    print("", end="\r", flush=True)
    fileDel(ARIA2_FILENAME)
    return


def dump(url, _from, _to):
    global MAIN_URL
    if "htm" in url:  # https://wapchan.org/cel/index.html
        url = os.path.dirname(url)  # https://wapchan.org/cel
    MAIN_URL = url
    log.info(MAIN_URL)

    _range = [x for x in range(_from, _to + 1)]

    u = MAIN_URL + "/catalog.json"  # https://wapchan.org/cel/catalog.json
    r = requests.get(u).json()

    for page in r:
        page_num = page["page"]
        if page_num not in _range:
            continue

        log.trace(f"page {page_num} of {len(r) - 1}")
        for th in page["threads"]:
            th_url = f"{MAIN_URL}/res/{th['no']}.json"  # https://wapchan.org/cel/res/2788.json
            dump_thread(th_url)


if len(sys.argv) < 3:
    print(sys.argv[0], "startpage-endpage <link to board>")
    print(sys.argv[0], "0-5 https://wapchan.org/cel")
    sys.exit()

_from, _to = sys.argv[1].split("-")

for i in range(2, len(sys.argv)):
    dump(sys.argv[i], int(_from), int(_to))
