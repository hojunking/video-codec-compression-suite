from __future__ import annotations

import subprocess
import os
from pathlib import Path
from typing import Any

from .utils import ensure_dir, expected_yuv420_size, run_logged, sorted_image_files, write_json, write_lines


def _probe_size(ffprobe: str, image: Path) -> tuple[int, int]:
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(image),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    width_s, height_s = proc.stdout.strip().split("x", 1)
    return int(width_s), int(height_s)


def _crop_even(width: int, height: int) -> tuple[int, int]:
    return width // 2 * 2, height // 2 * 2


def _quote_concat_path(path: Path) -> str:
    return str(path).replace("'", "'\\''")


def prepare_yuv(input_path: Path, config: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    input_cfg = config.get("input", {})
    input_type = input_cfg.get("type", "video")
    fps = input_cfg.get("fps")
    frame_limit = input_cfg.get("frames")
    yuv_cfg = config.get("yuv", {})
    geometry_cfg = config.get("geometry", {})
    tools_cfg = config.get("tools", {})

    ffmpeg = tools_cfg.get("ffmpeg") or os.environ.get("FFMPEG", "ffmpeg")
    ffprobe = tools_cfg.get("ffprobe") or os.environ.get("FFPROBE", "ffprobe")
    pixel_format = yuv_cfg.get("pixel_format", "yuv420p")
    yuv_name = yuv_cfg.get("filename", "input.yuv")

    input_dir = ensure_dir(output_dir / "input")
    logs_dir = ensure_dir(output_dir / "logs")
    yuv_path = input_dir / yuv_name
    source_names_path = input_dir / "source_names.txt"

    if pixel_format != "yuv420p":
        raise ValueError("Only yuv420p is currently supported by the packaged adapters.")

    if input_type == "image_sequence":
        if not input_path.is_dir():
            raise NotADirectoryError(f"Image sequence input must be a directory: {input_path}")
        images = sorted_image_files(input_path)
        if frame_limit is not None:
            images = images[: int(frame_limit)]
        if not images:
            raise ValueError(f"No image frames found: {input_path}")
        source_names = [p.name for p in images]
        src_w, src_h = _probe_size(ffprobe, images[0])
        enc_w, enc_h = _crop_even(src_w, src_h)
        if geometry_cfg.get("even_dimensions", "crop") != "crop" and (src_w != enc_w or src_h != enc_h):
            raise ValueError("Only even_dimensions: crop is currently implemented.")

        concat_path = input_dir / "concat.txt"
        write_lines(source_names_path, source_names)
        write_lines(concat_path, [f"file '{_quote_concat_path(p)}'" for p in images])
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_path),
            "-vf",
            f"crop={enc_w}:{enc_h}",
            "-frames:v",
            str(len(images)),
            "-pix_fmt",
            pixel_format,
            "-f",
            "rawvideo",
            str(yuv_path),
        ]
        run_logged(cmd, logs_dir / "prepare_yuv.log")
        frames = len(images)
    else:
        if not input_path.is_file():
            raise FileNotFoundError(f"Input video/YUV not found: {input_path}")
        if input_type == "yuv":
            raise ValueError("Raw YUV input requires explicit width/height/frames support; use image_sequence or video for now.")
        src_w, src_h = _probe_size(ffprobe, input_path)
        enc_w, enc_h = _crop_even(src_w, src_h)
        if fps is None:
            fps = 30
        video_cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-i",
            str(input_path),
            "-vf",
            f"crop={enc_w}:{enc_h}",
            "-pix_fmt",
            pixel_format,
            "-f",
            "rawvideo",
            str(yuv_path),
        ]
        if frame_limit is not None:
            video_cmd[-4:-4] = ["-frames:v", str(frame_limit)]
        run_logged(video_cmd, logs_dir / "prepare_yuv.log")
        frame_bytes = expected_yuv420_size(enc_w, enc_h, 1)
        frames = yuv_path.stat().st_size // frame_bytes
        write_lines(source_names_path, [f"{idx + 1:06d}.jpg" for idx in range(frames)])

    expected_size = expected_yuv420_size(enc_w, enc_h, frames)
    actual_size = yuv_path.stat().st_size
    if actual_size != expected_size:
        raise ValueError(f"Bad prepared YUV size: actual={actual_size} expected={expected_size}")

    metadata = {
        "input": {
            "path": str(input_path),
            "type": input_type,
            "source_width": src_w,
            "source_height": src_h,
            "encoded_width": enc_w,
            "encoded_height": enc_h,
            "frames": frames,
            "fps": fps,
            "source_names": str(source_names_path),
        },
        "yuv": {
            "path": str(yuv_path),
            "pixel_format": pixel_format,
            "chroma_format": yuv_cfg.get("chroma_format", 420),
            "bit_depth": yuv_cfg.get("bit_depth", 8),
            "bytes": actual_size,
        },
        "geometry": {
            "even_dimensions": geometry_cfg.get("even_dimensions", "crop"),
            "source_width": src_w,
            "source_height": src_h,
            "encoded_width": enc_w,
            "encoded_height": enc_h,
        },
        "logs": {"prepare_yuv": str(logs_dir / "prepare_yuv.log")},
    }
    write_json(output_dir / "metadata.json", metadata)
    return metadata
