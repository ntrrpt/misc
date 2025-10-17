#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "ffpb", "loguru", "tqdm", "humanize"
# ]
# ///
import ffpb
from sys import stderr, exit as die
from pathlib import Path
from loguru import logger as log
from humanize import naturalsize as hsize


def ff(args):
    try:
        r = ffpb.main(argv=args, encoding="utf-8")
        if r != 0:
            log.warning(f"{r} | {file.name}")
            die(r)

    except Exception as e:
        log.opt(exception=True).error(f"{file.name}: {e}")
        die(1)


def conv(in_file):
    out_file = Path(f"{in_file.stem}_cnv.mp4")

    cnv = [
        "-y",
        "-hwaccel", "cuda",
        "-hwaccel_output_format", "cuda",
        "-extra_hw_frames", "10",
        "-i", str(in_file),
        "-c:a", "copy",
        "-c:v", "h264_nvenc",
        str(out_file),
    ]  # fmt: skip

    chk = [
        "-i", str(out_file),
        "-f", "null",
        "-",
    ]  # fmt: skip

    ff(cnv)
    ff(chk)

    if out_file.exists():
        in_size = in_file.stat().st_size
        out_size = out_file.stat().st_size

        if in_size > out_size:
            log.success(
                f"out:{hsize(out_size)} < in:{hsize(in_size)}, removing SOURCE file"
            )
            in_file.unlink()

        elif out_size > in_size:
            log.success(
                f"in:{hsize(in_size)} < out:{hsize(out_size)}, removing output file"
            )
            out_file.unlink()

    else:
        log.error(f"not exist | {out_file.name} ")
        die(1)


if __name__ == "__main__":
    log.remove()
    log.add(
        stderr,
        backtrace=True,
        diagnose=True,
        format="<level>[{time:HH:mm:ss}]</level> {message}",
        colorize=True,
        level="TRACE",
    )

    exts = ["*.ts", "*.mp4", "*.mkv"]
    files = [f for ext in exts for f in Path(".").glob(ext)]

    for file in files:
        conv(file)
        print()
