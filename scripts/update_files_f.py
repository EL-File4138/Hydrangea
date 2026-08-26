#!/usr/bin/env python3

"""Update RTL and testbench SystemVerilog manifests from the source tree."""

import argparse
from pathlib import Path


def build_manifest_entries(repo_root: Path, source_dir: Path) -> list[str]:
    entries = []
    for path in source_dir.rglob("*.sv"):
        rel = path.relative_to(repo_root).as_posix()
        entries.append(rel)
    # Compile type declarations before their consumers. Implementation packages
    # follow the base packages they import (for example csr_impl -> csr).
    entries.sort(
        key=lambda entry: (
            0 if "/type/" in entry else 1,
            1 if entry.endswith("_implementation_pkg.sv") else 0,
            entry,
        )
    )
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate RTL and testbench SystemVerilog manifests."
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
        help="RTL manifest path relative to --repo-root.",
    )
    parser.add_argument(
        "--tb-output",
        type=Path,
        default=Path("testbench/tb_files.f"),
        help="Testbench manifest path relative to --repo-root.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; return non-zero if manifest is out of date.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_path = (repo_root / args.output).resolve()
    tb_output_path = (repo_root / args.tb_output).resolve()
    rtl_dir = (repo_root / "rtl").resolve()
    tb_dir = (repo_root / "testbench").resolve()

    if not rtl_dir.is_dir():
        raise SystemExit(f"RTL directory not found: {rtl_dir}")
    if not tb_dir.is_dir():
        raise SystemExit(f"Testbench directory not found: {tb_dir}")

    entries = build_manifest_entries(repo_root, rtl_dir)
    tb_entries = build_manifest_entries(repo_root, tb_dir)
    manifests = (
        (output_path, "\n".join(entries) + "\n", len(entries)),
        (tb_output_path, "\n".join(tb_entries) + "\n", len(tb_entries)),
    )

    if args.check:
        outdated = False
        for path, generated, _ in manifests:
            existing = path.read_text(encoding="ascii") if path.exists() else ""
            if existing != generated:
                print(f"Manifest is out of date: {path}")
                outdated = True
            else:
                print(f"Manifest is up to date: {path}")
        if outdated:
            return 1
        return 0

    for path, generated, count in manifests:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(generated, encoding="ascii")
        print(f"Updated {path} ({count} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
