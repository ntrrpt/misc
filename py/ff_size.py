#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "ffmpeg-python",
#   "ffpb",
#   "tqdm",
# ]
# ///

import ffmpeg
import ffpb
import argparse
import sys
import shlex
import os


def probe(file_path):
    probe_data = ffmpeg.probe(file_path)
    audio_stream = next(
        (stream for stream in probe_data["streams"] if stream["codec_type"] == "audio"),
        None,
    )
    audio_bitrate = (
        float(audio_stream["bit_rate"]) / 1000
        if audio_stream and "bit_rate" in audio_stream
        else None
    )
    duration = float(probe_data["format"]["duration"])
    return duration, audio_bitrate


def conv(filename):
    print(filename)
    name, extension = os.path.splitext(filename)
    duration, audio_bitrate = probe(filename)
    print(f"duration = {duration}, audio_bitrate = {audio_bitrate}")

    target_audio_bitrate = (
        audio_bitrate  # TODO: adjust target audio bitrate. use source bitrate for now
    )
    target_video_bitrate = (
        args.target_video_size_MB * 8192 / (1.048576 * duration) - target_audio_bitrate
    )
    print(
        f"target_audio_bitrate = {target_audio_bitrate}, target_video_bitrate = {target_video_bitrate}"
    )

    first_cmd = f'-y -i "{filename}" -c:v h264_nvenc -b:v {target_video_bitrate}k -pass 1 -an -f mp4 nul'
    second_cmd = f'-y -i "{filename}" -c:v h264_nvenc -b:v {target_video_bitrate}k -pass 2 -c:a aac -b:a {target_audio_bitrate}k "{name} {args.target_video_size_MB}MB{extension}"'
    ffpb.main(argv=shlex.split(first_cmd))
    ffpb.main(argv=shlex.split(second_cmd))
    print()


if __name__ == "__main__":
    # fmt: off
    ap = argparse.ArgumentParser(description="compressing video to a specified size via ffmpeg (NVENC)")
    add = ap.add_argument

    add("-s", "--size", dest="target_video_size_MB", type=int, default=4000, help="target video size in MB (default: 4000).")
    add("-e", "--ext",  dest="files_ext",            default="",             help="file extensions for conversion (e.g., mp4). If specified, all files with this extension in the current directory will be converted.")

    add("files", nargs="*", help="file names for conversion (if --ext is not specified).")

    args = ap.parse_args()
    # fmt: on

    print(f"target_video_size_MB => {args.target_video_size_MB}")

    files_to_convert = args.files
    if args.files_ext:
        files_to_convert = [f for f in os.listdir(".") if f.endswith(args.files_ext)]

    if not files_to_convert:
        print("no files to process. Specify files or the --ext parameter.")
        sys.exit(1)

    for file in files_to_convert:
        conv(file)
