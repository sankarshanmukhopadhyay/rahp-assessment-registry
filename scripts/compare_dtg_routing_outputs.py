#!/usr/bin/env python3
"""Compare canonical Toolkit and staged Registry DTG router artifacts byte-for-byte."""
import argparse
import hashlib
import json
from pathlib import Path

FILES = ("routing.json", "combined-events.json", "dpip-events.json",
         "unresolved.json", "compositions.txt")


def compare(old_dir: Path, new_dir: Path):
    errors, files = [], {}
    for name in FILES:
        a = old_dir / name
        b = new_dir / name
        if not a.is_file() or not b.is_file():
            errors.append(f"missing required output: {name}")
            continue
        legacy, staged = a.read_bytes(), b.read_bytes()
        if legacy != staged:
            errors.append(f"parity mismatch: {name}")
        files[name] = {
            "old_sha256": hashlib.sha256(legacy).hexdigest(),
            "new_sha256": hashlib.sha256(staged).hexdigest(),
            "identical": legacy == staged,
        }
    if not errors:
        routes = json.loads((new_dir / "routing.json").read_text(encoding="utf-8"))
        if not isinstance(routes, list) or not routes:
            errors.append("empty or non-list routing result does not prove parity")
    return errors, {
        "schema": "rahp-dtg-operational-routing-parity/v1",
        "files": files,
        "unexplained_differences": errors,
        "assurance_determination": "not_assessed",
        "source_case_ownership_changed": False,
        "controller_or_specialist_return_tested": False,
        "qualification": "byte-identical pinned historical routing outputs, not full controller cutover",
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--toolkit", type=Path, required=True)
    p.add_argument("--registry", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    errors, result = compare(args.toolkit, args.registry)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for issue in errors:
        print("FAIL:", issue)
    if errors:
        raise SystemExit(1)
    print("PASS byte-identical DTG routing output parity (not RAHP assurance PASS)")


if __name__ == "__main__":
    main()
