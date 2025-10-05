#!/usr/bin/env python3
"""Detect unresolved merge conflict markers in the repository tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".DS_Store" or path.suffix in {".pyc", ".db"}:
            continue
        if ".git" in path.parts or path.parts[0] == "data":
            continue
        yield path


def contains_conflict_marker(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(line.lstrip().startswith(CONFLICT_MARKERS) for line in text.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (defaults to the project root)",
    )
    args = parser.parse_args()

    root = args.root
    offending_files = [path for path in iter_text_files(root) if contains_conflict_marker(path)]

    if offending_files:
        print("Merge conflict markers detected in the following files:")
        for path in offending_files:
            print(f" - {path.relative_to(root)}")
        return 1

    print("No merge conflict markers found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
