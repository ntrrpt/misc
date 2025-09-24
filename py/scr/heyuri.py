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
import time
import subprocess
import sys
import re
from bs4 import BeautifulSoup
from loguru import logger as log

DELAY = 1

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


def add(dir, bin):
    with open(dir, "a", encoding="utf-8") as file:
        file.write(bin + "\n")


def dump_thread(url):
    img_urls = []

    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    htm_urls = [x.get("href") for x in soup.find_all("a") if x.get("href") is not None]

    # //img.heyuri.net/b/src/1732386430483.jpg
    for htm in htm_urls:
        if not htm.startswith("//img.heyuri.net/"):
            continue
        if "/src/" not in htm:
            continue

        img_urls.append(f"https:{htm}")

    img_urls = list(set(img_urls))  # remove duplicates
    log.debug(f"{len(img_urls)} pics to dump")

    _dir = os.listdir()

    img_urls.insert(0, "-nc")
    img_urls.insert(0, "wget")
    subprocess.run(img_urls)  # , stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print()

    return


def dump(url, _from, _to):
    if "html" in url:
        url = os.path.dirname(url)

    board_sfx = url[url.rfind(".net") + 5 : -1]  # /b/
    _range = [x for x in range(_from, _to + 1)]
    log.trace(f"{url} => {board_sfx}")

    soup = BeautifulSoup(requests.get(url).text, "html.parser")

    page_sfx = []
    if 0 in _range:
        page_sfx.append("index.html")

    for sp in soup.find_all("a"):
        if ".html?" not in str(sp):
            continue
        href = sp.get("href")
        if len(href) > 9:  # > 999.html
            continue
        for i in _range:
            if href.startswith(f"{i}.html?"):
                page_sfx.append(href)

    log.trace(f"total pages => {len(page_sfx)}")

    threads = []
    for sfx in page_sfx:
        th = url + sfx

        soup = BeautifulSoup(requests.get(th).text, "html.parser")
        htm_links = [
            x.get("href") for x in soup.find_all("a") if x.get("href") is not None
        ]
        for htm in htm_links:
            if not htm.startswith("koko.php?res="):
                continue
            if "#p" in htm:
                continue
            if "#q" in htm:
                continue
            if htm in threads:
                continue

            threads.append(htm)

        print(f"{page_sfx.index(sfx) + 1} / {len(page_sfx)}", end="\r")
        time.sleep(DELAY)

    for thread in threads:
        match = re.search(r"res=(\d+)", thread)
        if not match:
            log.error(url)
            log.error("no match in re url!")
            sys.exit()
        thread_id = match.group(1)

        name = f"{board_sfx} {thread_id}"
        os.makedirs(name, exist_ok=True)
        os.chdir(name)

        log.trace(f"[{threads.index(thread) + 1} / {len(threads)}] {thread}")
        dump_thread(url + thread)
        time.sleep(DELAY)

        os.chdir("..")


if len(sys.argv) < 3:
    print(sys.argv[0], "startpage-endpage <link to board>")
    print(sys.argv[0], "0-5 https://img.heyuri.net/b/")
    sys.exit()

_from, _to = sys.argv[1].split("-")

for i in range(2, len(sys.argv)):
    dump(sys.argv[i], int(_from), int(_to))
