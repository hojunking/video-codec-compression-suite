import argparse
from pathlib import Path

from .config import load_yaml
from .quality import resolve_quality


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vccs")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare-yuv", help="Create a normalized YUV input.")
    prepare.add_argument("--input", required=True, help="Input video or image directory.")
    prepare.add_argument("--config", default="configs/prepare_yuv.yaml", help="YUV preparation YAML config.")
    prepare.add_argument("--output", required=True, help="Output directory for prepared YUV and metadata.")

    compress = sub.add_parser("compress", help="Run a configured compression job.")
    compress.add_argument("--input-yuv", required=True, help="Prepared raw YUV file.")
    compress.add_argument("--codec-config", required=True, help="Codec-specific YAML config.")
    compress.add_argument("--qp", type=int, required=True, help="Requested H.26x-style QP value.")
    compress.add_argument("--output", required=True, help="Output directory for compressed artifacts.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "prepare-yuv":
        cfg = load_yaml(Path(args.config))
        print("vccs YUV preparation plan")
        print(f"  input       : {args.input}")
        print(f"  config      : {args.config}")
        print(f"  output      : {args.output}")
        print(f"  fps         : {cfg.get('input', {}).get('fps')}")
        print(f"  pixel format: {cfg.get('yuv', {}).get('pixel_format')}")
        print(f"  geometry    : {cfg.get('geometry', {}).get('even_dimensions')}")
        print("  status      : scaffold only; YUV generation is not wired yet")
        return 0

    codec_cfg = load_yaml(Path(args.codec_config))
    quality_cfg = codec_cfg.get("quality", {})
    mapping_rule = quality_cfg.get("qp_mapping", "identity")
    quality = resolve_quality(args.qp, mapping_rule)

    print("vccs compression plan")
    print(f"  input_yuv      : {args.input_yuv}")
    print(f"  codec          : {codec_cfg.get('codec')}")
    print(f"  codec config   : {args.codec_config}")
    print(f"  requested_qp   : {args.qp}")
    print(f"  quality kind   : {quality.quality_param_kind}")
    print(f"  effective value: {quality.effective_value}")
    print(f"  qp mapping     : {mapping_rule}")
    print(f"  runner         : {codec_cfg.get('runner')}")
    print(f"  encoder        : {codec_cfg.get('encoder')}")
    print(f"  output         : {args.output}")
    print("  status         : scaffold only; codec adapters are not wired yet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
