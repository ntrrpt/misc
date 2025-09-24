#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "requests",
#   "bs4",
#   "loguru",
#   "schedule",
# ]
# ///

import requests
import subprocess
import sys
import random
import string
import pathlib
from bs4 import BeautifulSoup

from loguru import logger as log

trace, info, err, succ = (log.trace, log.info, log.error, log.success)

log.remove(0)
log.add(
    sys.stderr,
    format="<level>[{time:DD-MMM-YYYY HH:mm:ss}]</level> {message}",
    backtrace=True,
    diagnose=True,
    colorize=True,
    level=5,
)

files = []
ARIA2_FILENAME = (
    "".join(random.choice(string.ascii_letters) for x in range(10)) + ".txt"
)


def fileDel(filename):
    rem_file = pathlib.Path(filename)
    rem_file.unlink(missing_ok=True)


def add(dir, bin):
    with open(dir, "a", encoding="utf-8") as file:
        file.write(bin + "\n")


def dump(url):
    log.debug(url)
    r = requests.get(url)
    if not r:
        err("no ret")
        return

    main_soup = BeautifulSoup(r.text, "html.parser")
    tr_soup = main_soup.find_all("tr")

    for tr in tr_soup:
        tr = str(tr)
        if "bgcolor" in tr or "SIZE(KB)" in tr:  # header
            continue
        if '<span class="deleted">' in tr:  # deleted
            err("deleted")
            continue

        soup = BeautifulSoup(str(tr), "html.parser")
        f_del = soup.find("a", href=lambda x: x and "up.php?del=" in x).get("href")
        f_name = soup.find("td", class_="fnm").a.text
        f_link = soup.find("td", class_="fnm").a.get("href")
        f_code = soup.find("td", class_="fco").text
        f_size = soup.find("td", class_="fsz").text
        f_date = soup.find("td", class_="fnw").text

        file = [f_del, f_name, f_link, f_code, f_size, f_date]
        files.append(file)
        succ(file)

    fileDel(ARIA2_FILENAME)

    for f in files:
        add(ARIA2_FILENAME, f"https://dec.2chan.net/up2/{f[2]}\n    out={f[1]}")

    aria2c_args = [
        "aria2c",
        f"--input-file={ARIA2_FILENAME}",
        "--dir=up2",
        "--max-connection-per-server=2",
        "--max-concurrent-downloads=5",
        "--auto-file-renaming=false",
        "--remote-time=true",
        "--log-level=error",
        "--console-log-level=error",
        "--download-result=hide",
        "--summary-interval=0",
        "--file-allocation=none",
        "--continue=true",
        #'--all-proxy=http://127.0.0.1:10809'
    ]
    subprocess.run(aria2c_args)
    print("", end="\r", flush=True)
    fileDel(ARIA2_FILENAME)


if len(sys.argv) < 2:
    print(sys.argv[0], "<link>")
    print(sys.argv[0], "https://dec.2chan.net/up2/up.htm")
    sys.exit()

for i in range(1, len(sys.argv)):
    dump(sys.argv[i])

"""
schedule.every().minute.at(":00").do(dump, url='https://dec.2chan.net/up2/up.htm')

while True:
    schedule.run_pending()
    time.sleep(1)
"""
