# /// script
# name = "uvass"
# description = "Associate files with uv run --script (.uv, .uvw)"
# dependencies = [
#     "pyinstaller",
# ]
# ///


from pathlib import Path
import logging as log
import subprocess as sp
import argparse
import winreg
import shutil
import random
import string
import ctypes
import sys


# Logging setup
log.basicConfig(level=log.INFO, format="    [%(levelname)s] %(message)s")
BASE = r"Software\Classes"


def is_pyinstaller_available():
    if shutil.which("pyinstaller") is None:
        return False

    try:
        r = sp.run(
            ["pyinstaller", "--version"], capture_output=True, text=True, check=True
        )

        # 6.16.0 => 6160 => digit
        return r.stdout.lower().replace(".", "").strip().isdigit()
    except (sp.CalledProcessError, FileNotFoundError):
        return False


def refresh_icons():
    SHCNE_ASSOCCHANGED = 0x8000000
    SHCNF_IDLIST = 0
    ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)


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


def ensure_local_bin():
    PATH = get_env_from_registry("PATH", user=True)
    if not PATH and ctypes.windll.shell32.IsUserAnAdmin():
        PATH = get_env_from_registry("PATH", user=False)
    if not PATH:
        log.error("PATH is empty")
        sys.exit(1)

    local_bin = Path.home() / ".local" / "bin"
    if not local_bin.exists():
        local_bin.mkdir(parents=True)
        log.info(f"Created directory: {local_bin}")

    # Check if it's in PATH
    path_dirs = PATH.split(";")
    if str(local_bin) not in path_dirs:
        sp.run(f'setx PATH "{PATH};{local_bin}"', shell=True)
        log.info(f"Added {local_bin} to PATH (restart terminal required).")


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
        sp.run(f'setx PATHEXT "{new_pathext}"', shell=True)
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
        sp.run(f'setx PATHEXT "{new_pathext_str}"', shell=True)
        log.info(
            f".{ext.upper()} removed from PATHEXT, restart cmd for changes to take effect"
        )
    else:
        log.info(f".{ext.upper()} was not in PATHEXT")


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
    sp.run(
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Associate files with uv run --script (.uv, .uvw)"
    )

    local_bin = Path.home() / ".local" / "bin"
    def_uv = local_bin / "uv.exe"
    def_uvw = local_bin / "uvw.exe"
    def_uvc = local_bin / "uvc.exe"  # c => custom
    def_py = Path(r"C:\Windows\py.exe")
    

    # fmt: off
    parser.add_argument(
        "action", nargs="?", choices=["add", "del"],
        help="Add or remove the associations",
    )
    parser.add_argument(
        "-w", "--wrapper", action='store_true',
        help="Use custom windowless wrapper instead of uvw.exe (need pyinstaller)",
    )
    parser.add_argument(
        "--uv-path", type=Path, default=def_uv,
        help=f"Path to uv.exe (default: {def_uv})",
    )
    parser.add_argument(
        "--uvw-path", type=Path, default=def_uvw,
        help=f"Path to uvw.exe (default: {def_uvw})",
    )    
    parser.add_argument(
        "--icon-path", type=Path, default=def_py,
        help=f"Path to icon file (default: {def_py})",
    )
    # fmt: on

    args = parser.parse_args()


    if args.wrapper and not def_uvc.exists() and not is_pyinstaller_available():
        log.error("pyinstaller not found, make sure you run uvass via uv")
        sys.exit(1)

    match args.action:
        case "add":
            add_assoc(
                "uv",
                args.uv_path,
                args.icon_path,
                "UvScript",
                "UV Python Script",
                'run --script "%1" %*',
            )

            if not args.wrapper:
                add_assoc(
                    "uvw",
                    args.uvw_path,
                    args.icon_path,
                    "UvWScript",
                    "UVW Python Script (Windowless)",
                    'run --script "%1" %*',
                )
            else:
                ensure_local_bin()

                if not def_uvc.exists():
                    build_wrapper(def_uvc, args.uv_path)

                add_assoc(
                    "uvw",
                    def_uvc,
                    args.icon_path,
                    "UvWScript",
                    "UVW Python Script (Windowless)",
                    '"%1" %*',
                )

        case "del":
            del_assoc("uv", "UvScript")
            del_assoc("uvw", "UvWScript")

            if def_uvc.exists():
                def_uvc.unlink()
                log.info(f"Removed wrapper exe: {def_uvc}")

        case _:
            parser.print_help()
            sys.exit(0)

    refresh_icons()
