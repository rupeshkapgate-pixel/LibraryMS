#!/usr/bin/env python3
"""
Fix protobuf-generated Python files to use relative imports.

grpc_tools.protoc generates:
    import common_pb2 as common__pb2

But when the stubs live in a package (e.g. app/proto_generated/),
Python cannot find them as bare module names. This script rewrites to:
    from . import common_pb2 as common__pb2
"""
import re
import sys
from pathlib import Path


def fix_file(path: Path) -> bool:
    original = path.read_text()
    # Match bare: import foo_pb2 as foo__pb2
    # but NOT: from . import ...  (already fixed)
    # and NOT: from google.protobuf import ...  (leave google imports alone)
    fixed = re.sub(
        r'^import ((\w+_pb2\w*)) as (\w+)',
        r'from . import \1 as \3',
        original,
        flags=re.MULTILINE,
    )
    if fixed != original:
        path.write_text(fixed)
        print(f"  Fixed: {path.name}")
        return True
    return False


if __name__ == "__main__":
    target_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    files = list(target_dir.glob("*_pb2*.py"))
    print(f"Fixing imports in {len(files)} files in {target_dir}...")
    changed = sum(fix_file(f) for f in files)
    print(f"Done — {changed}/{len(files)} files updated.")
