import argparse
from pathlib import Path

from .compress import compress_one, compress_suite
from .config import load_yaml
from .prepare import prepare_yuv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vccs")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare-yuv", help="Create a normalized YUV input.")
    prepare.add_argument("--input", required=True, help="Input video or image directory.")
    prepare.add_argument("--config", default="configs/prepare_yuv.yaml", help="YUV preparation YAML config.")
    prepare.add_argument("--output", required=True, help="Output directory for prepared YUV and metadata.")

    compress = sub.add_parser("compress", help="Run a configured compression job.")
    compress.add_argument("--input-yuv", required=True, help="Prepared raw YUV file.")
    compress.add_argument("--input-metadata", default=None, help="metadata.json from prepare-yuv. Auto-discovered when omitted.")
    compress.add_argument("--codec-config", required=True, help="Codec-specific YAML config.")
    compress.add_argument("--qp", type=int, required=True, help="Requested H.26x-style QP value.")
    compress.add_argument("--output", required=True, help="Output directory for compressed artifacts.")
    compress.add_argument(
        "--hmstyle-csv",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write an HM/x265-style normalized CSV log. Overrides codec YAML when set.",
    )

    suite = sub.add_parser("compress-suite", help="Run multiple codec configs, optionally in parallel.")
    suite.add_argument("--input-yuv", required=True, help="Prepared raw YUV file.")
    suite.add_argument("--input-metadata", default=None, help="metadata.json from prepare-yuv. Auto-discovered when omitted.")
    suite.add_argument("--codec-config", action="append", required=True, help="Codec YAML config. Repeat for multiple codecs.")
    suite.add_argument("--qp", type=int, required=True, help="Requested H.26x-style QP value.")
    suite.add_argument("--output", required=True, help="Output directory for all codec artifacts.")
    suite.add_argument("--workers", type=int, default=1, help="Number of codec jobs to run in parallel.")
    suite.add_argument(
        "--hmstyle-csv",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Write HM/x265-style normalized CSV logs. Overrides codec YAML when set.",
    )

    check_ref = sub.add_parser("check-reference", help="Check JM/HM/VTM executable paths in a codec YAML.")
    check_ref.add_argument("--codec-config", required=True, help="Reference codec YAML config.")

    return parser


def _check_path(path_value: str | None, label: str) -> bool:
    if not path_value:
        print(f"  MISSING {label}: not set")
        return False
    path = Path(path_value)
    if path.exists():
        print(f"  OK      {label}: {path}")
        return True
    print(f"  MISSING {label}: {path}")
    return False


def check_reference_config(config_path: Path) -> int:
    cfg = load_yaml(config_path)
    codec = cfg.get("codec")
    runner = cfg.get("runner")
    print(f"reference config: {config_path}")
    print(f"codec           : {codec}")
    print(f"runner          : {runner}")

    ok = True
    if runner == "jm":
        jm = cfg.get("jm", {})
        ok &= _check_path(jm.get("encoder_path"), "jm.encoder_path")
        ok &= _check_path(jm.get("workdir"), "jm.workdir")
    elif runner == "hm":
        hm = cfg.get("hm", {})
        ok &= _check_path(hm.get("encoder_path"), "hm.encoder_path")
        ok &= _check_path(hm.get("cfg_path"), "hm.cfg_path")
    elif runner == "vtm":
        vtm = cfg.get("vtm", {})
        ok &= _check_path(vtm.get("encoder_path"), "vtm.encoder_path")
        ok &= _check_path(vtm.get("cfg_path"), "vtm.cfg_path")
    else:
        print("  This is not a JM/HM/VTM reference backend config.")
        return 2

    if ok:
        print("status          : ready")
        return 0
    print("status          : edit the YAML paths above before running this backend")
    return 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "prepare-yuv":
        cfg = load_yaml(Path(args.config))
        input_path = Path(args.input)
        cfg.setdefault("input", {})["path"] = str(input_path)
        metadata = prepare_yuv(input_path, cfg, Path(args.output))
        print(f"prepared YUV: {metadata['yuv']['path']}")
        print(f"metadata    : {Path(args.output) / 'metadata.json'}")
        return 0

    if args.command == "check-reference":
        return check_reference_config(Path(args.codec_config))

    if args.command == "compress":
        result = compress_one(
            Path(args.input_yuv),
            Path(args.codec_config),
            args.qp,
            Path(args.output),
            Path(args.input_metadata) if args.input_metadata else None,
            args.hmstyle_csv,
        )
        print(f"compressed {result['codec']}: {result['bitstream']}")
        print(f"metadata            : {Path(args.output) / 'metadata.json'}")
        return 0

    results = compress_suite(
        Path(args.input_yuv),
        [Path(path) for path in args.codec_config],
        args.qp,
        Path(args.output),
        args.workers,
        Path(args.input_metadata) if args.input_metadata else None,
        args.hmstyle_csv,
    )
    print(f"completed codec jobs: {len(results)}")
    print(f"metadata            : {Path(args.output) / 'metadata.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
