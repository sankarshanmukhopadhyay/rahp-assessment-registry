#!/usr/bin/env python3
"""Read-only source audit of Toolkit branches. Not a server-side writer fence."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

WORKFLOW = ".github/workflows/dtg-portfolio-materiality-handoff.yml"
PUBLISHER = "tools/publish_assessment_issues.py"
SHA = re.compile(r"^[0-9a-f]{40}$")
WRITE = re.compile(r"(?m)^\s*issues:\s*write\s*(?:#.*)?$")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def remote_refs(repo: Path) -> list[tuple[str, str]]:
    lines = git(repo, "for-each-ref", "--format=%(refname) %(objectname)",
                "refs/remotes/origin/").splitlines()
    refs = []
    for line in lines:
        name, _, sha = line.partition(" ")
        if name == "refs/remotes/origin/HEAD":
            continue
        if not name.startswith("refs/remotes/origin/") or not SHA.fullmatch(sha):
            raise ValueError("invalid remote branch inventory")
        refs.append((name.removeprefix("refs/remotes/origin/"), sha))
    if not refs:
        raise ValueError("no remote branches found")
    return sorted(refs)


def inspect_ref(repo: Path, name: str, sha: str) -> dict:
    if not SHA.fullmatch(sha):
        raise ValueError("branch requires pinned commit")
    # Missing *workflow path* after default-branch entrypoint rotation is
    # expected. An invalid/unavailable commit remains a Git error and fails.
    candidate = git(repo, "ls-tree", "--name-only", sha, "--", WORKFLOW).strip()
    if candidate not in ("", WORKFLOW):
        raise ValueError("historical workflow discovery returned foreign paths")
    if not candidate:
        return {"ref": name, "commit": sha, "historical_workflow_present": False,
                "issues_write_declared": False, "manual_dispatch_declared": False,
                "live_transfer_guard_present": None, "unfenced_source_exposure": False}
    workflow = git(repo, "show", f"{sha}:{WORKFLOW}")
    publisher = git(repo, "show", f"{sha}:{PUBLISHER}")
    issue_write = bool(WRITE.search(workflow))
    manual = bool(re.search(r"(?m)^\s*workflow_dispatch\s*:", workflow))
    guarded = ("enforce_live_transfer_boundary" in publisher
               and "TRANSFER_LEDGER" in publisher)
    return {"ref": name, "commit": sha, "historical_workflow_present": True,
            "issues_write_declared": issue_write,
            "manual_dispatch_declared": manual,
            "live_transfer_guard_present": guarded,
            "unfenced_source_exposure": issue_write and manual and not guarded}


def audit(repo: Path, refs: list[tuple[str, str]]) -> dict:
    if not refs:
        raise ValueError("empty branch inventory cannot pass")
    rows = [inspect_ref(repo, name, sha) for name, sha in refs]
    risks = [r["ref"] for r in rows if r["unfenced_source_exposure"]]
    return {
        "schema": "rahp-toolkit-historical-writer-ref-audit/v1",
        "scope": "remote_branches_only",
        "ref_count": len(rows),
        "unfenced_source_refs": risks,
        "refs": rows,
        "scan_complete": True,
        "source_exposure_absent": not risks,
        "server_enforced_exclusion_verified": False,
        "cutover_authorized": False,
        "limitations": [
            "Excludes tags, deleted refs, in-flight jobs and other writer workflows.",
            "Does not verify token permissions, registered workflow status or real historic dispatch denial.",
            "Source guard presence does not prove atomic or server-enforced write exclusion."
        ]
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--toolkit", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    try:
        result = audit(args.toolkit, remote_refs(args.toolkit))
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"HISTORICAL REF AUDIT INCOMPLETE: {exc}")
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Historical refs: {result['ref_count']}; unfenced: {len(result['unfenced_source_refs'])}")
    if result["unfenced_source_refs"]:
        print("UNFENCED SOURCES; Registry cutover not authorized")
        return 1
    print("No branch source exposure found; server-enforced exclusion still unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
