# Video Codec Compression Suite

![VCCS overview](asset/VCCS.png)

Configurable video compression tool for running one input through multiple
codecs, QP settings, and log exporters.

## Features

- Input: video file, image sequence, or raw YUV.
- Codecs: H.264, H.265, H.266, AV1, VP9.
- Configurable preprocessing: FPS, frame count, crop/resize, pixel format,
  bit depth, and frame export.
- Native encoder logs are saved by default.
- Optional HEVC/x265-style normalized CSV export for cross-codec analysis.
- Metadata records both requested QP and the actual encoder quality parameter.

AV1 and VP9 do not use H.26x QP directly. When these codecs are selected, the
tool records the mapping explicitly, for example requested `QP=37` to AV1 `q`
or VP9 `crf`.

## Install

Create the conda environment:

```bash
conda env create -f environment.yml
conda activate vccs
```

Install or refresh the local package:

```bash
pip install -e .
```

FFmpeg and FFprobe must be available in `PATH`. The provided conda environment
installs FFmpeg from `conda-forge`. If you need a custom FFmpeg build, build it
separately and point the shell `PATH` to that build before running `vccs`.

Reference software backends require external binaries:

- JM for `h264_jm`
- HM for `h265_hm`
- VTM for `h266_vtm`

Set those binary and config paths in YAML before using the corresponding
backend.

For VVC/H.266, use the VTM reference software as an external checkout/build and
set `vtm.encoder_path` and `vtm.cfg_path` in `configs/codecs/h266_vtm.yaml`.

## Quick Start

Prepare a YUV input first:

```bash
vccs prepare-yuv \
  --input input.mp4 \
  --config configs/prepare_yuv.yaml \
  --output outputs/input_yuv
```

Then run a codec-specific compression:

```bash
vccs compress \
  --input-yuv outputs/input_yuv/input.yuv \
  --codec-config configs/codecs/h265_ffmpeg.yaml \
  --qp 37 \
  --output outputs/h265_qp37
```

## Configuration

Use `configs/prepare_yuv.yaml` for input and YUV generation settings such as
FPS, frame count, crop/resize, pixel format, bit depth, and frame export.

Use one codec config per compression backend:

- `configs/codecs/h264_ffmpeg.yaml`
- `configs/codecs/h265_ffmpeg.yaml`
- `configs/codecs/h265_hm.yaml`
- `configs/codecs/h266_vtm.yaml`
- `configs/codecs/av1_ffmpeg.yaml`
- `configs/codecs/vp9_ffmpeg.yaml`

Reference software paths are configured in YAML. The package does not bundle JM,
HM, or VTM.

## Outputs

Each run writes a self-contained output directory:

```text
outputs/<run_id>/
  metadata.json
  input/
    input.yuv
  bitstream/
  recon/
  frames/
  logs/
```

`metadata.json` is the main audit record. It includes input properties,
preprocessing choices, selected codec, requested QP, effective encoder quality
parameter, output paths, and dummy fields used in normalized CSV exports.

Native encoder stdout/stderr logs are preserved by default. The normalized
HEVC/x265-style CSV is a compatibility export for cross-codec analysis.

## References

This project wraps or interoperates with the following codec implementations.
Check the linked projects for build instructions, licensing, and codec-specific
options.

- FFmpeg: https://ffmpeg.org/
- FFmpeg source: https://git.ffmpeg.org/ffmpeg.git
- x264 / H.264 encoder: https://www.videolan.org/developers/x264.html
- x265 / H.265 encoder: https://x265.org/
- JM / H.264 reference software: https://iphome.hhi.de/suehring/tml/download/
- HM / H.265 reference software: https://vcgit.hhi.fraunhofer.de/jct-vc/HM
- VTM / H.266 reference software: https://vcgit.hhi.fraunhofer.de/jvet/VVCSoftware_VTM
- SVT-AV1: https://gitlab.com/AOMediaCodec/SVT-AV1
- libvpx / VP9: https://www.webmproject.org/code/
