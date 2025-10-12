#!/usr/bin/env python3
import logging as log
import os
import subprocess as sp
import sys

import tomllib

RSYNC_CMD = "rsync -avzt"
DEST = "lain@192.168.0.100:/ssd/phone"

log.basicConfig(
    level=log.DEBUG,
    format="\033[36m%(asctime)s \033[33m%(levelname)5s \033[0m%(message)s",
)


def run(source, dest, excludes=None, remove_source=True):
    cmd = RSYNC_CMD.split()
    if remove_source:
        cmd += ["--remove-source-files"]
    if excludes:
        for ex in excludes:
            cmd += ["--exclude", ex]
    cmd += [source, dest]

    log.debug(f"{source} {excludes} {remove_source}")
    log.debug(f"exec: {' '.join(cmd)}")

    result = sp.run(cmd)
    if result.returncode != 0:
        log.error(f"sync error {source}")
        sys.exit(1)


def rm_rf(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            if not os.listdir(dir_path):
                log.info(f"rm -rf empty dir: {dir_path}")
                os.rmdir(dir_path)


if __name__ == "__main__":
    with open("sync.toml", "rb") as f:
        config = tomllib.load(f)

    log.info(f"start sync to {DEST!r}")

    for dir_path, options in config.items():
        if not os.path.isdir(dir_path):
            log.error(f"{dir_path!r} is not exists")
            continue

        excludes = options.get("exclude", [])
        remove = options.get("remove", True)

        run(dir_path, DEST, excludes=excludes, remove_source=remove)
        rm_rf(dir_path)

    log.info("sync completed!")
