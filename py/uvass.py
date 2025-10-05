from pathlib import Path
import logging as log
import argparse
import winreg
import ctypes
import sys
import subprocess

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
    PATHEXT = get_env_from_registry("PATHEXT", user=True)
    if not PATHEXT and ctypes.windll.shell32.IsUserAnAdmin():
        PATHEXT = get_env_from_registry("PATHEXT", user=False)
    if not PATHEXT:
        log.error("PATHEXT is empty")
        return

    current_pathext = PATHEXT.upper().split(";")

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
    PATHEXT = get_env_from_registry("PATHEXT", user=True)
    if not PATHEXT and ctypes.windll.shell32.IsUserAnAdmin():
        PATHEXT = get_env_from_registry("PATHEXT", user=False)
    if not PATHEXT:
        log.error("PATHEXT is empty")
        return

    current_pathext = PATHEXT.split(";")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Associate files with uv run --script (.uv, .uvw)"
    )

    default = Path.home() / ".local" / "bin"
    default_uv = default / "uv.exe"
    default_uvw = default / "uvw.exe"

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
        "--uvw-path", type=Path, default=default_uvw,
        help=f"Path to uvw.exe (default: {default_uvw})",
    )    
    parser.add_argument(
        "--icon-path", type=Path, default=Path(r"C:\Windows\py.exe"),
        help="Path to icon file",
    )
    # fmt: on

    args = parser.parse_args()

    if args.action == "add":
        add_assoc(
            "uv",
            args.uv_path,
            args.icon_path,
            "UvScript",
            "UV Python Script",
            'run --script "%1" %*',
        )

        add_assoc(
            "uvw",
            args.uvw_path,
            args.icon_path,
            "UvWScript",
            "UVW Python Script (Windowless)",
            'run --script "%1" %*',
        )

    elif args.action == "del":
        del_assoc("uv", "UvScript")
        del_assoc("uvw", "UvWScript")

    else:
        parser.print_help()
        sys.exit(0)

    refresh_icons()
