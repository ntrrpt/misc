#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "requests",
#   "bs4",
#   "loguru",
#   "pysocks"
# ]
# ///

from bs4 import BeautifulSoup
from loguru import logger as log
import requests

from urllib.parse import urlparse
from pathlib import Path
from email.utils import parsedate_to_datetime
import time
import sys
import re
import os

# need "proxies"
proxy = {}

# and real-lookin headers
header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
}

not_exists = ("1223753394222")  # fmt: skip

nend_urls = [
    "http://nendoroid01.web.fc2.com/2008-03/",
    "http://nendoroid01.web.fc2.com/2008-04/",
    "http://nendoroid02.web.fc2.com/2008-05/",
    "http://nendoroid02.web.fc2.com/2008-06/",
    "http://nendoroid03.web.fc2.com/2008-07/",
    "http://nendoroid03.web.fc2.com/2008-08/",
    "http://nendoroid03.web.fc2.com/2008-09/",
    "http://nendoroid04.web.fc2.com/2008-10/",
    "http://nendoroid04.web.fc2.com/2008-11/",
    "http://nendoroid05.web.fc2.com/2008-12/",
    "http://nendoroid05.web.fc2.com/2009-01/",
    "http://nendoroid06.web.fc2.com/2009-02/",
    "http://nendoroid06.web.fc2.com/2009-03/",
    "http://nendoroid07.web.fc2.com/2009-04/",
    "http://nendoroid07.web.fc2.com/2009-05/",
    "http://nendoroid08.web.fc2.com/2009-06/",
    "http://nendoroid08.web.fc2.com/2009-07/",
    "http://nendoroid09.web.fc2.com/2009-08/",
    "http://nendoroid09.web.fc2.com/2009-09/",
]


def get_with_retries(url, max_retries=5, retry_delay=10):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, proxies=proxy, headers=header, timeout=15)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as e:
            raise Exception("http failed:", e, "| status:", r.status_code)
        except requests.exceptions.RequestException as e:
            log.error(str(e))
            time.sleep(retry_delay)
    raise Exception(f"failed {url} after {max_retries} tries")


def find_max_page(url):
    text = requests.get(url, proxies=proxy, headers=header).text
    soup = BeautifulSoup(text, "html.parser")

    for i in soup.find_all("tr"):
        if "Page" in str(i):
            all_num = i.find_all("a")
            match = re.search(r"index(\d+)\.html", all_num[-1].get("href"))

            return int(match.group(1))


if __name__ == "__main__":
    log.add("log.txt", encoding="utf-8")

    for url in nend_urls:
        images = []

        # http://nendoroid01.web.fc2.com/2008-03/ => 2008-03
        dir_name = Path(url.rstrip("/").split("/")[-1])
        dir_name.mkdir(parents=True, exist_ok=True)

        pages = [url + "index.html"]
        max_page = find_max_page(pages[0])
        log.info(f"{url}: pages => {max_page}")

        for i in range(2, max_page + 1):
            pages.append(f"{url}index{i}.html")

        for page in pages:
            log.info(page)

            parsed_url = urlparse(page)
            file_name = os.path.basename(parsed_url.path)
            file_path = dir_name / file_name

            r = get_with_retries(page)
            with open(file_path, "wb") as f:
                f.write(r.content)

            soup = BeautifulSoup(r.text, "html.parser")
            blocks = soup.find_all("td")

            for block in blocks:
                link = block.find("a")
                img = block.find("img")

                if link and img:
                    src = img.get("src")
                    alt = img.get("alt")

                    if src.startswith("thumbs"):
                        u = url + str(alt)
                        if u not in images:
                            images.append(u)

        for img in images:
            for ext in ["jpg", "gif", "png", "rip"]:
                if ext == "rip":
                    log.critical("EXT NOT FOUND")
                    log.error(img)
                    sys.exit(1)

                try:
                    img_url = f"{img}.{ext}"
                    parsed_url = urlparse(img_url)
                    file_name = os.path.basename(parsed_url.path)
                    file_path = dir_name / file_name

                    if file_path.is_file() or img.endswith(not_exists):
                        log.info(img_url)
                        break

                    r = get_with_retries(img_url)
                    with open(file_path, "wb") as f:
                        f.write(r.content)

                    if "Last-Modified" in r.headers:
                        lm = r.headers["Last-Modified"]
                        dt = parsedate_to_datetime(lm)
                        ts = dt.timestamp()
                        os.utime(file_path, (ts, ts))

                    log.success(img_url)
                    break

                except Exception:
                    log.error(img_url)
