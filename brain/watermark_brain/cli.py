"""CLI: a folder of photos -> a damage-documentation scope report.

  watermark-brain --input <folder> --backend mock        # free, instant
  watermark-brain --input <folder> --backend bedrock     # AWS Bedrock (needs AWS creds)
  watermark-brain --input <folder> --backend ollama      # local GPU (ollama pull qwen2.5vl:7b)
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from datetime import datetime
from pathlib import Path

from .pipeline import IMAGE_EXTS, analyze_paths
from .report import ImageResult, write_reports
from .schema import ImageAnalysis


def find_images(input_dir: Path, limit: int, exclude: list[str]) -> list[Path]:
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    if exclude:
        files = [p for p in files if not any(fnmatch.fnmatch(p.name.lower(), pat.lower()) for pat in exclude)]
    return files[:limit] if limit > 0 else files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scan photos -> insurance scope report.")
    ap.add_argument("--input", "-i", required=True)
    ap.add_argument("--output", "-o", default="out")
    ap.add_argument("--backend", choices=["mock", "bedrock", "ollama", "claude"], default="mock")
    ap.add_argument("--model", default=None)
    ap.add_argument("--region", default="us-east-1", help="AWS region for the bedrock backend")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    ap.add_argument("--max-dim", type=int, default=1536)
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args(argv)

    input_dir = Path(args.input)
    if not input_dir.is_dir():
        print(f"error: input folder not found: {input_dir}", file=sys.stderr)
        return 2
    images = find_images(input_dir, args.limit, args.exclude)
    if not images:
        print(f"error: no images in {input_dir}", file=sys.stderr)
        return 2

    print(f"Analyzing {len(images)} photo(s) via {args.backend}:{args.model or 'default'}\n")

    def progress(i, n, name, tag):
        print(f"  [{i}/{n}] {name}: {tag}")

    results = analyze_paths(images, backend=args.backend, model=args.model, max_dim=args.max_dim,
                            use_cache=not args.no_cache, bedrock_region=args.region, on_progress=progress)
    if not results:
        print("\nNo photos produced a result.", file=sys.stderr)
        return 1
    out_dir = Path(args.output)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    image_results = [ImageResult(path=Path(r["path"]), analysis=ImageAnalysis.model_validate(r["analysis"])) for r in results]
    paths = write_reports(image_results, out_dir, generated_at)
    (out_dir / "findings.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\nDone.")
    print(f"  Report (HTML): {paths['html']}")
    print(f"  Report (MD):   {paths['markdown']}")
    print(f"  Raw findings:  {out_dir / 'findings.json'}")
    tok_in = sum(r["usage"].get("input_tokens", 0) for r in results if not r["cached"])
    tok_out = sum(r["usage"].get("output_tokens", 0) for r in results if not r["cached"])
    if tok_in or tok_out:
        print(f"  Tokens (new calls): {tok_in:,} in / {tok_out:,} out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
