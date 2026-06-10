#!/usr/bin/env python3
"""
Fix protobuf-generated Python files to use relative imports.

grpc_tools.protoc generates bare imports like:
    import common_pb2 as common__pb2

These fail when the generated files live inside a Python package
(e.g. app/proto_generated/) because Python cannot find the top-level
module. This script rewrites them to relative imports:
    from . import common_pb2 as common__pb2

Usage:
    python scripts/fix_proto_imports.py <path/to/proto_generated>
"""
import re
import sys
from pathlib import Path


BARE_IMPORT_RE = re.compile(
    r'^import ((\w+_pb2\w*)) as (\w+)',
    flags=re.MULTILINE,
)


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    fixed = BARE_IMPORT_RE.sub(r'from . import \1 as \3', original)
    if fixed != original:
        path.write_text(fixed, encoding="utf-8")
        print(f"  Fixed: {path.name}")
        return True
    return False


def fix_directory(target: Path) -> None:
    files = list(target.glob("*_pb2*.py"))
    if not files:
        print(f"  Warning: no *_pb2*.py files found in {target}")
        return
    changed = sum(fix_file(f) for f in files)
    print(f"  {changed}/{len(files)} files updated in {target}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_proto_imports.py <directory>")
        sys.exit(1)
    fix_directory(Path(sys.argv[1]))
