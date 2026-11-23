# Toolkit issue archive: first historical baseline

The registry contains a **source-complete issue metadata inventory** for 2026-11-16:
**769 issues, 712 closed and 57 open**, excluding pull requests. All twelve pages of the GitHub Issues endpoint were examined (the twelfth contained 99 raw records). The manifest and two partitioned JSON snapshots retain original issue IDs, URLs, titles, state, timestamps, labels, comment counts, and typed assessment markers, where present.

- [Browse all 769 historical Toolkit issues](issue-index.md): sortable by browser search, ordered by original issue number; each issue links to the authoritative Toolkit thread and displays **snapshot** state/classification.
- [Accepted successor and Registry-native case index](succession-index.md): explicit source issue → accepted Registry owner → case record; no guessed equivalence.
- [Archive manifest](manifest.json) and [post-capture succession ledger](accepted-successors.json): source metadata and separately accepted ownership.
- [Issue snapshot, higher source IDs](snapshots/toolkit-issues-2026-11-16-p1.json)
- [Issue snapshot, lower source IDs](snapshots/toolkit-issues-2026-11-16-p2.json)

This is **not yet a full-fidelity standalone historical archive**. GitHub original issue pages remain authoritative for bodies, comments, events, attachments, reactions and participants. The registry cannot honestly claim to preserve all historical content until those have been exported, integrity-checked and governed for privacy. The snapshot only represents its observation date.

Classes `external-assessment-candidate`, `mixed-review` and `development-or-unclassified` are triage signals, **not disposition or assurance outcomes**. Closed development issues must not be mass-imported as RAHP assessment cases; external assessment issue history must be discoverable in the registry without reopening resolved work or losing original links.

**Rebuild and verify the reference indices** with `python3 scripts/build_archive_reference.py` and `python3 scripts/build_archive_reference.py --check`. The latter is required by Registry CI. The index is derived from the immutable historical snapshot, the accepted-successor overlay and committed case owners; it is not a second registry or an independent source of ownership. The [succession contract](../docs/case-succession.md), [case lifecycle](../docs/case-lifecycle.md) and [execution journal](../docs/registry-execution-journal.md) provide further navigation.

Run: `python3 scripts/validate_toolkit_archive.py`, `python3 scripts/validate_history_locator.py` and `python3 -m unittest discover -s tests -v`.

**Retention decision:** do not bulk-copy issue bodies, comments, events or external attachments into this repository merely to improve reference navigation. The source issue pages remain authoritative; the metadata index and accepted succession ledger are sufficient for the current locator contract. A full-content export is a **separately governed, privacy-reviewed preservation activity** if a specific retention or source-loss risk justifies it. It is neither the default next increment nor necessary to activate Registry case publication, which was switched on 23 November 2026. The historical capture/staging guides describe optional tooling, not an obligation to merge a mirror.
