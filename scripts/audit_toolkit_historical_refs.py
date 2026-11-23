#!/usr/bin/env python3
"""Read-only audit of historical Toolkit issue-writer source at branches and tags.

An observed source guard or disabled workflow registration is not a server
enforced prohibition on every historical dispatch or independent credential.
The audit intentionally cannot certify exclusive Registry case publication.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from audit_toolkit_issue_writers import EXPECTED, PUBLISHER

# Current inventory is authoritative for workflow names; retain retired
# names because historic branches and tags may still carry runnable YAML.
WORKFLOWS = tuple(sorted({
    *(f".github/workflows/{name}" for name in EXPECTED),
    ".github/workflows/dtg-portfolio-materiality-handoff.yml",
    ".github/workflows/instance-watch.yml",
}))
SHA = re.compile(r"^[0-9a-f]{40}$")
WRITE = re.compile(r"(?m)^\s*issues:\s*write\s*(?:#.*)?$")
MANUAL = re.compile(r"(?m)^\s*workflow_dispatch\s*:")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True,
        capture_output=True, text=True,
    ).stdout


def remote_refs(repo: Path) -> list[tuple[str, str]]:
    """Inspect every available remote branch and tag; incomplete means blocked."""
    lines = git(
        repo, "for-each-ref", "--format=%(refname) %(objectname)",
        "refs/remotes/origin/", "refs/tags/",
    ).splitlines()
    refs = []
    for line in lines:
        name, sep, sha = line.partition(" ")
        if not sep or not SHA.fullmatch(sha):
            raise ValueError("invalid remote branch or tag inventory")
        if name == "refs/remotes/origin/HEAD":
            continue
        if name.startswith("refs/remotes/origin/"):
            ref = "branch:" + name.removeprefix("refs/remotes/origin/")
        elif name.startswith("refs/tags/"):
            ref = "tag:" + name.removeprefix("refs/tags/")
            # Annotated tags point to a tag object, not the tree commit.
            sha = git(repo, "rev-parse", name + "^{commit}").strip()
            if not SHA.fullmatch(sha):
                raise ValueError("unresolvable annotated tag")
        else:
            raise ValueError("unexpected ref namespace")
        refs.append((ref, sha))
    if not refs or not any(ref == "branch:main" for ref, _ in refs):
        raise ValueError("empty or incomplete remote branch/tag inventory")
    if len({ref for ref, _ in refs}) != len(refs):
        raise ValueError("duplicate branch/tag identity")
    return sorted(refs)


def inspect_ref(repo: Path, name: str, sha: str) -> dict:
    if not SHA.fullmatch(sha):
        raise ValueError("branch or tag requires pinned commit")
    rows = []
    for workflow in WORKFLOWS:
        candidate = git(repo, "ls-tree", "--name-only", sha, "--", workflow).strip()
        if candidate not in ("", workflow):
            raise ValueError("historical workflow discovery returned foreign paths")
        if not candidate:
            continue
        source = git(repo, "show", f"{sha}:{workflow}")
        issue_write = bool(WRITE.search(source))
        manual = bool(MANUAL.search(source))
        # The presence of a source-level ledger check does not make a
        # historical manually dispatched workflow non-writable.
        guarded = False
        if issue_write and PUBLISHER in source:
            candidate_script = git(
                repo, "ls-tree", "--name-only", sha, "--", PUBLISHER,
            ).strip()
            if candidate_script != PUBLISHER:
                raise ValueError("publisher called by workflow but missing in ref")
            script = git(repo, "show", f"{sha}:{PUBLISHER}")
            guarded = (
                "enforce_live_transfer_boundary" in script
                and "TRANSFER_LEDGER" in script
            )
        rows.append({
            "workflow": workflow,
            "issues_write_declared": issue_write,
            "manual_dispatch_declared": manual,
            "live_transfer_guard_present": guarded,
            "potential_external_issue_write": issue_write and manual,
        })
    risky = [x["workflow"] for x in rows if x["potential_external_issue_write"]]
    return {
        "ref": name, "commit": sha,
        "workflow_count": len(rows),
        "workflows": rows,
        "unfenced_source_exposure": bool(risky),
        "potentially_writable_workflows": risky,
    }


def audit(repo: Path, refs: list[tuple[str, str]]) -> dict:
    if not refs:
        raise ValueError("empty branch/tag inventory cannot pass")
    rows = [inspect_ref(repo, name, sha) for name, sha in refs]
    exposed = [
        {"ref": row["ref"], "workflows": row["potentially_writable_workflows"]}
        for row in rows if row["unfenced_source_exposure"]
    ]
    return {
        "schema": "rahp-toolkit-historical-writer-ref-audit/v2",
        "scope": "remote_branches_and_tags",
        "ref_count": len(rows),
        "workflows_examined": list(WORKFLOWS),
        "potentially_writable_refs": exposed,
        "unfenced_source_refs": [row["ref"] for row in exposed],
        "refs": rows,
        "scan_complete": True,
        "source_exposure_absent": not exposed,
        "server_enforced_exclusion_verified": False,
        "cutover_authorized": False,
        "limitations": [
            "This audits available refs; deleted refs and in-flight jobs require independent checks.",
            "No GitHub Actions workflow registration, dispatch denial or token permission is established here.",
            "No source-level guard is a cross-repository lock or server-enforced write exclusion.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolkit", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.toolkit, remote_refs(args.toolkit))
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print("HISTORICAL REF AUDIT INCOMPLETE:", exc)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        f"Toolkit branch/tag refs: {result['ref_count']}; "
        f"potentially writable: {len(result['potentially_writable_refs'])}"
    )
    if result["potentially_writable_refs"]:
        print("HISTORICAL WRITER EXPOSURE: Registry cutover not authorized")
        return 1
    print("No historical source exposure found; exclusive writer authority still unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
