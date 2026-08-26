#!/usr/bin/env python3
"""Conservative, deterministic checks for the RV32 RTL naming contract."""

import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys


IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"


def report(path, line, column, rule, message):
    print(f"{path}:{line}:{column}: [{rule}] {message}")


def source_without_comments(text):
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.DOTALL)


def core_prefix_required(path, policy, repo_root):
    try:
        relative_path = path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return False

    return any(
        relative_path == pathlib.Path(root)
        or pathlib.Path(root) in relative_path.parents
        for root in policy["core_rtl_roots"]
    )


def check_file(path, policy, repo_root):
    errors = 0
    text = path.read_text(encoding="utf-8")
    source = source_without_comments(text)
    lines = source.splitlines()

    syntax = shutil.which("verible-verilog-syntax")
    if syntax:
        result = subprocess.run(
            [syntax, str(path)], capture_output=True, text=True, check=False
        )
        if result.returncode:
            print(result.stderr, end="")
            return 1

    prefix_required = core_prefix_required(path, policy, repo_root)
    core_prefix = policy["core_rtl_prefix"]

    if (
        prefix_required
        and path.suffix == ".sv"
        and not path.name.startswith(core_prefix)
    ):
        report(path, 1, 1, "RVNAME001", "Core RTL filenames must use the rv32_ prefix")
        errors += 1

    for line_number, line in enumerate(lines, 1):
        module = re.search(rf"\bmodule\s+({IDENTIFIER})", line)
        if prefix_required and module and not module.group(1).startswith(core_prefix):
            report(
                path,
                line_number,
                module.start(1) + 1,
                "RVNAME002",
                "Core module names must use the rv32_ prefix",
            )
            errors += 1

        typedef = re.search(
            rf"\btypedef\s+(struct|union)\b.*?\}}\s*({IDENTIFIER})\s*;", line
        )
        if typedef and not typedef.group(2).endswith("_t"):
            report(
                path,
                line_number,
                typedef.start(2) + 1,
                "RVNAME003",
                "struct and union typedefs must end in _t",
            )
            errors += 1

        active_low = re.search(rf"\b({IDENTIFIER}_n)\b", line)
        if active_low and not re.search(r"\b(?:input|output|logic|wire)\b", line):
            report(
                path,
                line_number,
                active_low.start(1) + 1,
                "RVNAME004",
                "_n is reserved for active-low signals",
            )
            errors += 1

    for enum in re.finditer(
        rf"typedef\s+enum\b.*?\}}\s*({IDENTIFIER})\s*;", source, re.DOTALL
    ):
        enum_type = enum.group(1)
        line_number = source[: enum.start(1)].count("\n") + 1
        if not enum_type.endswith("_e"):
            report(path, line_number, 1, "RVNAME005", "enum typedefs must end in _e")
            errors += 1
            continue
        prefix = policy["enum_prefixes"].get(enum_type)
        if not prefix:
            continue
        body = enum.group(0).split("{", 1)[1].rsplit("}", 1)[0]
        for member in re.finditer(
            rf"(?:^|,)\s*({IDENTIFIER})\s*(?:=|,|$)", body, re.MULTILINE
        ):
            name = member.group(1)
            if name.startswith(prefix):
                continue
            member_line = source[: enum.start() + member.start(1)].count("\n") + 1
            report(
                path,
                member_line,
                member.start(1) + 1,
                "RVNAME006",
                f"{enum_type} members must start with {prefix}",
            )
            errors += 1

    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=pathlib.Path)
    parser.add_argument("--repo-root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--version", action="store_true")
    parser.add_argument("files", nargs="*")
    args = parser.parse_args()
    if args.version:
        print("check_rtl_naming.py 1.0")
        return 0
    if not args.policy:
        parser.error("--policy is required")
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    return (
        1
        if sum(
            check_file(pathlib.Path(name), policy, args.repo_root)
            for name in args.files
        )
        else 0
    )


if __name__ == "__main__":
    sys.exit(main())
