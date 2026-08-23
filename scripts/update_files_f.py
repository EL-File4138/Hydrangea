#!/usr/bin/env python3

"""Update the Makefile RTL manifest from the source tree."""

import argparse
from pathlib import Path


def build_manifest_entries(repo_root: Path, rtl_dir: Path) -> list[str]:
    entries = []
    for path in rtl_dir.rglob("*.sv"):
        # Manifest should list only RTL sources, not itself.
        if path.name == "files.f":
            continue
        rel = path.relative_to(repo_root).as_posix()
        entries.append(rel)
    entries.sort()
    return entries

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate rtl/files.f from discovered SystemVerilog sources."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to this script's parent project).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("rtl/files.f"),
        help="Output manifest path relative to --repo-root.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; return non-zero if manifest is out of date.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_path = (repo_root / args.output).resolve()
    rtl_dir = (repo_root / "rtl").resolve()

    if not rtl_dir.is_dir():
        raise SystemExit(f"RTL directory not found: {rtl_dir}")

    entries = build_manifest_entries(repo_root, rtl_dir)
    generated = "\n".join(entries) + "\n"

    existing = ""
    if output_path.exists():
        existing = output_path.read_text(encoding="ascii")

    if args.check:
        if existing != generated:
            print(f"Manifest is out of date: {output_path}")
            return 1
        print(f"Manifest is up to date: {output_path}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated, encoding="ascii")
    print(f"Updated {output_path} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
