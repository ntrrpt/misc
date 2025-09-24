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
from loguru import logger as log

MAIN_URL = None  #  https://hikari3.ch/t/

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


"""
def str_cut_re(string, letters, postfix='...'): # reverse
    #if len(filename) >= 64:
    #    filename = str_cut_re(file["originalName"], 55, "")
            
    return string[letters:] + (string[:letters] and postfix)
"""


def str_fix(string):
    return str_cut(re.sub(r'[/\\?%*:{}【】|"<>]', "", string), 200, "")


def dump_thread(th_url):
    global MAIN_URL
    images = []

    log.debug(th_url)
    r = requests.get(th_url).json()

    dirname = str(r["threadId"])
    if "subject" in r and r["subject"]:
        dirname += " " + str_fix(r["subject"])

    # op pics
    if r["files"]:
        for file in r["files"]:
            filename = str_cut(file["originalName"], 200, "")
            f = f"{r['threadId']} {filename}"  #  94  teplé ponožky.jpeg
            u = f"https://hikari3.ch{file['path']}"  # https://hikari3.ch/.media/ae3....b4d.jpg
            images.append([f, u])

    for post in r["posts"]:
        files = post["files"]
        if not files:
            continue

        for file in files:
            filename = str_cut(file["originalName"], 200, "")
            f = f"{post['postId']} {filename}"
            u = f"https://hikari3.ch{file['path']}"
            images.append([f, u])

    if not images:
        log.error(f"{th_url} (no images)")
        return

    fileDel("tmp.txt")
    for img in images:
        add("tmp.txt", f"{img[1]}\n    out={img[0]}")

    aria2c_args = [
        "aria2c",
        "--input-file=tmp.txt",
        f"--dir={dirname}",
        "--max-connection-per-server=1",
        "--max-concurrent-downloads=2",
        "--auto-file-renaming=false",
        "--remote-time=true",
        "--log-level=error",
        "--console-log-level=error",
        "--download-result=hide",
        "--summary-interval=0",
        "--file-allocation=none",
    ]

    subprocess.run(aria2c_args)
    print("", end="\r", flush=True)
    return


def dump(url, _from, _to):
    global MAIN_URL
    if "htm" in url:  # https://hikari3.ch/t/index.html
        url = os.path.dirname(url)  # https://hikari3.ch/t/
    MAIN_URL = url
    log.info(MAIN_URL)

    _range = [x for x in range(_from, _to + 1)]

    for i in range(1, 337):
        if i not in _range:
            continue

        # https://hikari3.ch/t/5.json
        u = MAIN_URL + f"/{i}.json"
        r = requests.get(u)

        if not r:
            log.success("no more pages")
            break

        threads = r.json()["threads"]
        log.trace("page %s" % i)

        for th in threads:
            # https://hikari3.ch/t/res/48.json
            th_url = f"{MAIN_URL}/res/{th['threadId']}.json"
            dump_thread(th_url)


if len(sys.argv) < 3:
    print(sys.argv[0], "startpage-endpage <link to board>")
    print(sys.argv[0], "0-5 https://hikari3.ch/t")
    sys.exit()

_from, _to = sys.argv[1].split("-")

for i in range(2, len(sys.argv)):
    dump(sys.argv[i], int(_from), int(_to))
