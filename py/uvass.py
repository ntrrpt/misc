import argparse
import winreg
import ctypes
import sys
from pathlib import Path
import logging as log
import os
import subprocess

log.basicConfig(level=log.INFO, format="[%(levelname)s] %(message)s")

BASE = r"Software\Classes"


def add_assoc(ext: str, uv_path: Path, icon_path: Path):
    if not uv_path.exists():
        log.error(f"uv.exe not found at: {uv_path}")
        log.info("use --uv-path to specify the correct path")
        sys.exit(1)

    # .ext -> UvScript
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE + rf"\.{ext}") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, "UvScript")

    # UvScript -> description
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, BASE + r"\UvScript") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, "UV Python Script")

    # DefaultIcon -> icon (if file exists)
    if icon_path and icon_path.exists():
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, BASE + r"\UvScript\DefaultIcon"
        ) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, f"{icon_path},0")
        log.info(f"icon set: {icon_path}")
    else:
        log.warning("icon not applied (file not found)")

    # shell\open\command -> run via uv
    cmd = f'"{uv_path}" run --script "%1" %*'
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, BASE + r"\UvScript\shell\open\command"
    ) as key:
        winreg.SetValue(key, "", winreg.REG_SZ, cmd)

    # add .UV to PATHEXT if not already present
    current_pathext = os.environ.get("PATHEXT", "").upper().split(";")
    if f".{ext.upper()}" not in current_pathext:
        new_pathext = ";".join(current_pathext + [f".{ext.upper()}"])
        subprocess.run(f'setx PATHEXT "{new_pathext}"', shell=True)
        log.info(
            f".{ext.upper()} added to PATHEXT. Restart CMD for changes to take effect."
        )
    else:
        log.info(f".{ext.upper()} is already in PATHEXT.")

    refresh_icons()
    log.info(f"association for .{ext} successfully created")


def remove_assoc(ext: str):
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, BASE + rf"\.{ext}")
        log.info(f"association for .{ext} removed (link to UvScript).")
    except FileNotFoundError:
        log.warning(f"association for .{ext} not found")

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

    deltree(winreg.HKEY_CURRENT_USER, BASE + r"\UvScript")

    # remove .UV from PATHEXT
    current_pathext = os.environ.get("PATHEXT", "").split(";")
    new_pathext = [e for e in current_pathext if e.upper() != f".{ext.upper()}"]

    if len(new_pathext) != len(current_pathext):
        new_pathext_str = ";".join(new_pathext)
        subprocess.run(f'setx PATHEXT "{new_pathext_str}"', shell=True)
        log.info(
            f".{ext.upper()} removed from PATHEXT, restart cmd for changes to take effect"
        )
    else:
        log.info(f".{ext.upper()} was not in PATHEXT")

    refresh_icons()
    log.info("UvScript key removed.")


def refresh_icons():
    SHCNE_ASSOCCHANGED = 0x8000000
    SHCNF_IDLIST = 0
    ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)


def main():
    parser = argparse.ArgumentParser(
        description="associate files with 'uv run --script' on windows"
    )
    default_uv = Path.home() / ".local" / "bin" / "uv.exe"

    # fmt:off
    parser.add_argument("action", nargs="?", choices=["add", "remove"], help="add or remove the association")
    parser.add_argument("--ext", default="uv", help="file extension without dot (default: uv)")
    parser.add_argument("--uv-path", type=Path, default=default_uv, help=f"path to uv.exe (default: {default_uv})")
    parser.add_argument("--icon-path", type=Path, default=Path(r"C:\Windows\py.exe"), help="path to icon file (exe, ico, etc.)")
    # fmt:on

    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(0)

    if args.action == "add":
        add_assoc(args.ext, args.uv_path, args.icon_path)
    elif args.action == "remove":
        remove_assoc(args.ext)


if __name__ == "__main__":
    main()
