#!/usr/bin/env python3
"""Build a deterministic, non-authoritative browse index from committed locator data.

No network access; no mutation of the 2026-11-16 source snapshots. The existing
history-locator validator remains the ownership/collision guard.
"""
import argparse
import json
import sys
from pathlib import Path

from validate_history_locator import verify

ROOT = Path(__file__).resolve().parents[1]
ISSUES = ROOT / "archive/issue-index.md"
SUCCESSION = ROOT / "archive/succession-index.md"


def cell(value):
    return str(value or "").replace("|", r"\|").replace("\n", " ").replace("\r", " ")


def render(root=ROOT):
    root = Path(root)
    verify(root)
    manifest = json.loads((root / "archive/manifest.json").read_text(encoding="utf-8"))
    records = {}
    for part in manifest["partitions"]:
        for record in json.loads((root / part["path"]).read_text(encoding="utf-8")):
            records[record["number"]] = record
    overlay_path = root / "archive/accepted-successors.json"
    if overlay_path.exists():
        json.loads(overlay_path.read_text(encoding="utf-8"))  # locator verifies exact mapping

    accepted = {}
    direct = []
    for path in sorted((root / "cases").rglob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        owners = case.get("owners", {})
        case_link = "../" + path.relative_to(root).as_posix()
        if owners.get("handoff") == "accepted":
            accepted[owners["historical_source_issue"]] = (
                case["case_id"], owners["current_active_issue"], case_link)
        elif owners.get("admission") == "direct":
            direct.append((case["case_id"], owners.get("current_active_issue"), case_link))

    lines = [
        "# Toolkit issue metadata locator (16 November 2026)",
        "",
        "Generated from [manifest](manifest.json), the two immutable snapshots,",
        "[accepted successor assignments](accepted-successors.json), and current",
        "[case records](../cases/). Rebuild with",
        "`python3 scripts/build_archive_reference.py`; verify with `--check`.",
        "",
        "**Historical snapshot, not live issue state.** Triage classifications are",
        "neither acceptance of an external case nor RAHP determinations. Original",
        "Toolkit GitHub issues remain canonical for bodies, comments and events.",
        "A dash means no *accepted* administrative succession in the committed",
        "case records; it does not prove that no related Registry case exists.",
        "",
        "| Toolkit issue | Snapshot title | Snapshot state | Triage class | Accepted Registry successor |",
        "| --- | --- | --- | --- | --- |",
    ]
    for number in sorted(records, reverse=True):
        row = records[number]
        source = row["url"]
        owned = accepted.get(source)
        if owned:
            cid, current, case_link = owned
            successor = f"[{cell(cid)}]({case_link}) · [Registry #{current.rsplit('/', 1)[-1]}]({current})"
        else:
            successor = "—"
        lines.append(
            f"| [#{number}]({source}) | {cell(row['title'])} | "
            f"{row['state']} | `{row['classification']}` | {successor} |"
        )

    succession = [
        "# Accepted case succession and Registry-native cases",
        "",
        "Generated from committed accepted [case records](../cases/), with",
        "[source snapshot](manifest.json) and",
        "[post-capture accepted-successor overlay](accepted-successors.json)",
        "validated by `scripts/validate_history_locator.py`.",
        "It is **not** a current-GitHub-state poll or an independent authority check.",
        "A source issue may have other related propositions; only explicit",
        "accepted handoffs appear below. No successor is inferred from a title,",
        "finding marker, label, or shared evidence.",
        "",
        "## Accepted Toolkit-to-Registry administrative succession",
        "",
        "| Case | Historical Toolkit issue | Registry administrative owner | Case record |",
        "| --- | --- | --- | --- |",
    ]
    for source in sorted(accepted, key=lambda x: int(x.rsplit("/", 1)[-1])):
        cid, current, path = accepted[source]
        succession.append(
            f"| `{cell(cid)}` | [Toolkit #{source.rsplit('/', 1)[-1]}]({source}) | "
            f"[Registry #{current.rsplit('/', 1)[-1]}]({current}) | [Record]({path}) |"
        )
    succession += [
        "",
        "Accepted succession changes *administrative coordination only*, not",
        "Toolkit execution ownership, historical GitHub identity, specialist",
        "authority, or assurance determination.",
        "",
        "## Registry-originated direct cases without Toolkit predecessor",
        "",
        "| Case | Registry owner | Case record |",
        "| --- | --- | --- |",
    ]
    for cid, current, path in sorted(direct):
        link = f"[Registry #{current.rsplit('/', 1)[-1]}]({current})" if current else "Not recorded"
        succession.append(f"| `{cell(cid)}` | {link} | [Record]({path}) |")
    succession += [
        "",
        "Unaccepted or other admission routes are **not** automatically classed",
        "as direct. Consult their own case records and controlled intake receipts.",
        "For assessment executions and residual evidence follow the linked case",
        "record and [execution journal](../docs/registry-execution-journal.md).",
    ]
    return {"archive/issue-index.md": "\n".join(lines) + "\n",
            "archive/succession-index.md": "\n".join(succession) + "\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on stale generated indices")
    args = parser.parse_args()
    try:
        outputs = render()
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print("INVALID archive locator:", exc, file=sys.stderr)
        return 1
    stale = []
    for rel, content in outputs.items():
        path = ROOT / rel
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(rel)
        else:
            path.write_text(content, encoding="utf-8")
    if stale:
        print("STALE generated indices: " + ", ".join(stale), file=sys.stderr)
        return 1
    print(("PASS" if args.check else "GENERATED") + ": " + ", ".join(outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
