#!/usr/bin/env python3

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a flat binary into one 32-bit little-endian word per line."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = args.input.read_bytes()

    if len(data) % 4:
        data += bytes(4 - len(data) % 4)

    with args.output.open("w", encoding="ascii") as f:
        for offset in range(0, len(data), 4):
            word = int.from_bytes(data[offset : offset + 4], byteorder="little")
            f.write(f"{word:08x}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
