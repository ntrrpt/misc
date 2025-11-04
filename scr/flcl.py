import os
import subprocess
from pathlib import Path

cmd = "fclones group . | fclones remove"


def has_subfolders(directory: Path) -> bool:
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        return False
    try:
        return any(item.is_dir() for item in directory.iterdir())
    except PermissionError:
        return False


def run_fclones(path: Path) -> None:
    print(f"\nProcessing: {path}")
    try:
        subprocess.run(
            cmd.split(),
            cwd=path,
            shell=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"fclones failed in {path}: {e}")


def execute_fclones_in_subdirs(root: Path = Path(".")) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath == ".":
            continue
        d = Path(dirpath)
        if not has_subfolders(d):
            run_fclones(d)


if __name__ == "__main__":
    execute_fclones_in_subdirs()
