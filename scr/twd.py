#!/usr/bin/env -S uv run --script

# /// script
# name = "twd"
# description = "tool for suspending twitter accounts  :D"
# requires-python = ">=3.12"
# dependencies = [
#     "loguru>=0.7.3",
#     "pause>=0.3",
#     "requests>=2.32.3",
#     "twikit>=2.3.3",
# ]
# ///

import time
import sys
import os
import re
import pathlib
import optparse
import random
import string
import shutil
import asyncio
import subprocess as sp
from datetime import datetime

import pause
from twikit import Client
from loguru import logger as log

trace, info, err, succ = (log.trace, log.info, log.error, log.success)

# import tracemalloc; tracemalloc.start()

# search_tweet => 1 search in 18-20 seconds, 50 searches in 15 minutes
SEARCH_TWEET_DELAY = 30
TIMEOUT_DELAY = 60
DROP_SEARCH_AFTER_X_ATTEMPTS = 1
COOKIES = "cookies.json"

log.remove(0)
log.add(
    sys.stderr,
    backtrace=True,
    diagnose=True,
    format="<level>[{time:HH:mm:ss}]</level> {message}",
    colorize=True,
    level=5,
)

parser = optparse.OptionParser()
parser.add_option("-s", dest="search", default="lucky star", help="search string")
parser.add_option("-y", dest="years", default="13-16", help="years interval (11,14-16)")
parser.add_option(
    "-m", dest="months", default="1-12", help="month interval (2,4,10-12)"
)
parser.add_option("-d", dest="days", default="1,15", help="dayss interval (1,15)")
parser.add_option(
    "-p",
    dest="proxy",
    default="http://127.0.0.1:10809",
    help="proxy for twikit / aria2",
)
options, arguments = parser.parse_args()

ARIA2_FILENAME = (
    "".join(random.choice(string.ascii_letters) for x in range(10)) + ".txt"
)
aria2c_args = [
    "aria2c",
    f"--input-file={ARIA2_FILENAME}",
    f"--dir={options.search}",
    "--max-connection-per-server=1",
    "--max-concurrent-downloads=2",
    "--auto-file-renaming=false",
    "--remote-time=true",
    "--log-level=error",
    "--console-log-level=error",
    "--download-result=hide",
    "--summary-interval=0",
    "--file-allocation=none",
    "--continue=true",
    "--check-certificate=false",
    "--quiet=true",
]
if options.proxy:
    aria2c_args.append(f"--all-proxy={options.proxy}")


def fileDel(filename):
    rem_file = pathlib.Path(filename)
    rem_file.unlink(missing_ok=True)


def add(dir, bin):
    with open(dir, "a", encoding="utf-8") as file:
        file.write(bin + "\n")


def con(d, c):
    return any(k in str(c) for k in d)


def is_aria2c_available():
    if shutil.which("aria2c") is None:
        return False

    try:
        r = sp.run(["aria2c", "--version"], capture_output=True, text=True, check=True)
        return "aria2" in r.stdout.lower()
    except (sp.CalledProcessError, FileNotFoundError):
        return False


def picsdump(tweets):
    medias = []
    dubs = 0

    for tweet in tweets:
        for _, media in enumerate(tweet.media):
            to = []

            media_url = media.media_url
            expanded_url = media.expanded_url

            media_id = expanded_url.split("/")[-3]  # 1741609594680725580
            all_ids.append(media_id)  # multiple medias in tweet

            media_ext = media_url.split(".")[-1]  # jpg

            full_id = "%s_%s" % (
                media_id,
                all_ids.count(media_id),
            )  # 1741609594680725580_1

            base_name = "%s %s" % (
                tweet.user.screen_name,
                full_id,
            )  # himelabo_chika 1741609594680725580_1

            match media.type:
                case "photo":
                    url = media_url.replace(
                        f".{media_ext}", "?format=%s&name=orig" % media_ext
                    )
                    to = [url, "%s.%s" % (base_name, media_ext)]
                case "animated_gif" | "video":
                    url = media.streams[-1].url
                    to = [url, "%s.%s" % (base_name, "mp4")]

            if to:
                if to[0] in all_urls:
                    dubs += 1
                else:
                    all_urls.append(to[0])
                    medias.append(to)

    if not medias:
        return ""  # only dubs

    fileDel(ARIA2_FILENAME)

    for med in medias:
        add(ARIA2_FILENAME, "%s\n    out=%s" % (med[0], med[1]))

    sp.run(aria2c_args, capture_output=False, text=False)

    fileDel(ARIA2_FILENAME)

    ret = "+%s" % len(medias)
    if dubs:
        ret += " ~%s" % dubs

    return ret


async def auth(USERNAME, PASSWORD):
    await client.login(auth_info_1=USERNAME, password=PASSWORD)
    client.save_cookies(COOKIES)


async def searchdump(search_str):
    def status(str):
        print(str, end=" ", flush=True)

    tweets = None
    all_tweets = []
    zero_searches = 0
    rip_searches = 0

    for first_search in (1, 0):
        while True:
            try:
                if first_search:
                    tweets = await client.search_tweet(search_str, "Media")
                else:
                    try:
                        tweets = await tweets.next()
                    except RuntimeError:
                        break

                status(len(tweets))

                if first_search and not tweets:  # fuck
                    time.sleep(SEARCH_TWEET_DELAY + random.randint(-10, 10))
                    rip_searches += 1
                    if rip_searches > 10:
                        break
                else:
                    zero_searches = (zero_searches + 1) if not tweets else 0
                    all_tweets += list(tweets)

                    if zero_searches >= DROP_SEARCH_AFTER_X_ATTEMPTS:
                        break

                    time.sleep(SEARCH_TWEET_DELAY + random.randint(-10, 10))

                    if first_search:
                        break

            except Exception as ex:
                idk = [
                    "list index out of range",
                    "views",
                    "is_translatable",
                    "legacy",
                    "Multiple cookies exist with name",
                    "object has no attribute",
                ]

                if con(["Rate limit"], ex):
                    status("r")
                    pause.until(ex.rate_limit_reset + 5)

                elif con(["timed out", "getaddrinfo"], ex):  # rip internet
                    status("t")
                    time.sleep(TIMEOUT_DELAY)

                elif con(["items"], ex):  # no pics in first search
                    return

                elif con(["moduleItems"], ex):  # no pics in second search
                    break

                elif con(idk, ex):
                    time.sleep(TIMEOUT_DELAY)
                    break

                else:
                    err(f"tw exc => {str(ex)}")
                    sys.exit()

    # print('', end='\r', flush=True)
    succ(f"{search_str} {picsdump(all_tweets)}        ")
    return True


stop = False
all_urls = []
all_ids = []

if not is_aria2c_available():
    err("need aria2 downloader to working")
    sys.exit(1)

client = Client("en-US", proxy=options.proxy)

if not os.path.exists(COOKIES):
    log.warn(f"no {COOKIES} detected, auth required")
    u, p = input("username: "), input("password: ")
    asyncio.run(auth(u, p))
    sys.exit()
else:
    client.load_cookies(COOKIES)
    info("cookies ok!")


# "1-5,8,10-12" => 1,2,3,4,5,8,10,11,12
def expand_ranges(s):
    def replace_range(match):
        start, end = map(int, match.group().split("-"))
        return ",".join(map(str, range(start, end + 1)))

    return re.sub(r"\d+-\d+", replace_range, s)


years = expand_ranges(options.years).split(",")
months = expand_ranges(options.months).split(",")
days = expand_ranges(options.days).split(",")

for y in years:
    if int(y) < 10:
        y = "0" + str(y)

    for m in months:
        if int(m) < 10:
            m = "0" + str(m)

        for d in days:
            if int(d) < 10:
                d = "0" + str(d)

            if stop:
                break

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            sd = loop.run_until_complete(
                searchdump(f"{options.search} lang:ja until:20{y}-{m}-{d}")
            )

            if not sd:
                break

            if datetime(int(f"20{y}"), int(m), int(d)) > datetime.now():
                stop = True

info(f"all_urls => {len(all_urls)}")
