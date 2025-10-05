# /// script
# name = "uvass"
# description = "associate files with uv run --script (.uv) and uw wrapper (.uw)"
# dependencies = [
#     "pyinstaller",
# ]
# ///

import argparse
import winreg
import random
import string
import ctypes
import sys
from pathlib import Path
import logging as log
import subprocess
import shutil

# Logging setup
log.basicConfig(level=log.INFO, format="    [%(levelname)s] %(message)s")
BASE = r"Software\Classes"


def get_env_from_registry(name, user=True):
    if user:
        root = winreg.HKEY_CURRENT_USER
        path = r"Environment"
    else:
        root = winreg.HKEY_LOCAL_MACHINE
        path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"

    with winreg.OpenKey(root, path) as key:
        try:
            value, _ = winreg.QueryValueEx(key, name)
            return value
        except FileNotFoundError:
            return None


def pathext_add(ext: str):
    # add .EXT to PATHEXT if not already present
    current_pathext = get_env_from_registry("PATHEXT").upper().split(";")
    if not current_pathext:
        log.error("PATHEXT is empty")
        return

    if f".{ext.upper()}" not in current_pathext:
        new_pathext = ";".join(current_pathext + [f".{ext.upper()}"])
        subprocess.run(f'setx PATHEXT "{new_pathext}"', shell=True)
        log.info(
            f".{ext.upper()} added to PATHEXT. Restart CMD for changes to take effect."
        )
    else:
        log.info(f".{ext.upper()} is already in PATHEXT.")


def pathext_del(ext: str):
    # remove .EXT from PATHEXT
    current_pathext = get_env_from_registry("PATHEXT").split(";")
    if not current_pathext:
        log.error("PATHEXT is empty")
        return

    new_pathext = [e for e in current_pathext if e.upper() != f".{ext.upper()}"]

    if len(new_pathext) != len(current_pathext):
        new_pathext_str = ";".join(new_pathext)
        subprocess.run(f'setx PATHEXT "{new_pathext_str}"', shell=True)
        log.info(
            f".{ext.upper()} removed from PATHEXT, restart cmd for changes to take effect"
        )
    else:
        log.info(f".{ext.upper()} was not in PATHEXT")


def refresh_icons():
    SHCNE_ASSOCCHANGED = 0x8000000
    SHCNF_IDLIST = 0
    ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)


def ensure_local_bin():
    local_bin = Path.home() / ".local" / "bin"
    if not local_bin.exists():
        local_bin.mkdir(parents=True)
        log.info(f"Created directory: {local_bin}")

    # Check if it's in PATH
    path_dirs = get_env_from_registry("PATH").split(";")
    if not path_dirs:
        log.error("PATH is empty")
        sys.exit(1)

    if str(local_bin) not in path_dirs:
        subprocess.run(
            f'setx PATH "{get_env_from_registry("PATH")};{local_bin}"', shell=True
        )
        log.info(f"Added {local_bin} to PATH (restart terminal required).")

    return local_bin


def build_wrapper(wrapper_path: Path, uv_path: Path):
    workpath = "".join(random.choice(string.ascii_letters) for x in range(10))

    wrapper_code = f"""\
import subprocess, sys

if len(sys.argv) > 1: 
    subprocess.Popen(
        [r"{uv_path}", "run", "--script", sys.argv[1], *sys.argv[2:]],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
"""
    tmp_py = wrapper_path.with_suffix(".py")
    tmp_py.write_text(wrapper_code, encoding="utf-8")
    log.info(f"Wrapper source written to {tmp_py}")

    # Build exe with pyinstaller
    subprocess.run(
        [
            "pyinstaller",
            "--onefile",
            "--noconsole",
            "--workpath", workpath,
            "--distpath", str(wrapper_path.parent),
            str(tmp_py),
        ],
        check=True,
    )  # fmt: skip

    # Cleanup pyinstaller leftovers
    for item in [workpath, tmp_py.stem + ".spec"]:
        p = Path(item)
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()

    tmp_py.unlink(missing_ok=True)
    log.info(f"Wrapper built: {wrapper_path}")


def add_assoc(
    ext: str, target_path: Path, icon_path: Path, progid: str, desc: str, args: str
):
    if not target_path.exists():
        log.error(f"uv.exe not found at: {target_path}")
        log.info("use --uv-path to specify the correct path")
        sys.exit(1)

    # .ext -> ProgID
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE + rf"\.{ext}") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, progid)

    # ProgID -> description
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE + rf"\{progid}") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, desc)

    # DefaultIcon
    if icon_path and icon_path.exists():
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, BASE + rf"\{progid}\DefaultIcon"
        ) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f"{icon_path},0")
        log.info(f"Icon set for .{ext}: {icon_path}")
    else:
        log.warning(f"Icon not applied for .{ext} (file not found).")

    # shell\open\command -> run via uv
    cmd = f"{target_path} {args}"
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, BASE + rf"\{progid}\shell\open\command"
    ) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, cmd)

    pathext_add(ext)
    log.info(f"Association for .{ext} successfully created!")


def del_assoc(ext: str, progid: str):
    try:
        pathext_del(ext)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, BASE + rf"\.{ext}")
        log.info(f"Association for .{ext} removed.")
    except FileNotFoundError:
        log.warning(f"Association for .{ext} not found.")

    def deltree(root, subkey):
        try:
            with winreg.OpenKey(root, subkey) as k:
                while True:
                    sub = winreg.EnumKey(k, 0)
                    deltree(root, subkey + "\\" + sub)
        except OSError:
            pass
        try:
            winreg.DeleteKey(root, subkey)
        except FileNotFoundError:
            pass

    deltree(winreg.HKEY_CURRENT_USER, BASE + rf"\{progid}")
    log.info(f"{progid} key removed.")


def main():
    parser = argparse.ArgumentParser(
        description="Associate files with uv run --script (.uv) and uw wrapper (.uw)"
    )
    default_uv = Path.home() / ".local" / "bin" / "uv.exe"

    # fmt: off
    parser.add_argument(
        "action", nargs="?", choices=["add", "del"],
        help="Add or remove the associations",
    )
    parser.add_argument(
        "--uv-path", type=Path, default=default_uv,
        help=f"Path to uv.exe (default: {default_uv})",
    )
    parser.add_argument(
        "--icon-path", type=Path, default=Path(r"C:\Windows\py.exe"),
        help="Path to icon file",
    )
    # fmt: on

    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(0)

    local_bin = ensure_local_bin()
    wrapper_exe = local_bin / "uw.exe"

    if args.action == "add":
        # Normal .uv association
        add_assoc(
            "uv",
            args.uv_path,
            args.icon_path,
            "UvScript",
            "UV Python Script",
            'run --script "%1" %*',
        )

        # Silent .uw association
        if not wrapper_exe.exists():
            build_wrapper(wrapper_exe, args.uv_path)
        add_assoc(
            "uw",
            wrapper_exe,
            args.icon_path,
            "UvWScript",
            "UV Python Script (Windowless)",
            '"%1" %*',
        )

    elif args.action == "del":
        del_assoc("uv", "UvScript")
        del_assoc("uw", "UvWScript")
        if wrapper_exe.exists():
            wrapper_exe.unlink()
            log.info(f"Removed wrapper exe: {wrapper_exe}")

    refresh_icons()


if __name__ == "__main__":

    def is_pyinstaller_available():
        if shutil.which("pyinstaller") is None:
            return False

        try:
            r = subprocess.run(
                ["pyinstaller", "--version"], capture_output=True, text=True, check=True
            )

            # 6.16.0 => 6160 => digit
            return r.stdout.lower().replace(".", "").strip().isdigit()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    if not is_pyinstaller_available():
        log.error("pyinstaller not found, make sure you run uvass via uv")
        sys.exit(1)

    main()
