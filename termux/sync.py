#!/usr/bin/env python3
import subprocess
import logging as log
import os

SYNC_DIRS = {
    "/sdcard/Download": ["KateDownloads/"],
    "/sdcard/Pictures": ["KatePhotos/"],
    "/sdcard/Movies": [],
    "/sdcard/Music": [],
    "/sdcard/Kuroba": [],
    "/sdcard/DCIM": ["DCIM_24/"]
}

DEST = "foo@192.168.0.1:/ssd/phone"

log.basicConfig(
	level = log.DEBUG,
	format = '\033[36m%(asctime)s \033[33m%(levelname)5s \033[0m%(message)s'
)

def rsync_sync(source, dest, excludes=None, remove_source=True):
    cmd = ["rsync", "-avzt"]
    if remove_source:
        cmd.append("--remove-source-files")
    if excludes:
        for ex in excludes:
            cmd.extend(["--exclude", ex])
    cmd.extend([source, dest])

    log.debug(f"{source} {excludes}")
    log.debug(f"exec: {" ".join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log.error(f"sync error {source}")

def remove_empty_dirs(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                log.info(f"rm -rf empty dir: {dir_path}")

def main():
    log.info("start sync...")

    for dir_path, excludes in SYNC_DIRS.items():
        rsync_sync(dir_path, DEST, excludes=excludes, remove_source=True)
        remove_empty_dirs(dir_path)

    log.info("sync completed!")

if __name__ == "__main__":
    main()
