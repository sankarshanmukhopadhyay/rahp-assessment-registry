# Toolkit issue archive: first historical baseline

The registry contains a **source-complete issue metadata inventory** for 2026-11-16:
**769 issues, 712 closed and 57 open**, excluding pull requests. All twelve pages of the GitHub Issues endpoint were examined (the twelfth contained 99 raw records). The manifest and two partitioned JSON snapshots retain original issue IDs, URLs, titles, state, timestamps, labels, comment counts, and typed assessment markers, where present.

- [Archive manifest](manifest.json)
- [Issue snapshot, higher source IDs](snapshots/toolkit-issues-2026-11-16-p1.json)
- [Issue snapshot, lower source IDs](snapshots/toolkit-issues-2026-11-16-p2.json)

This is **not yet a full-fidelity standalone historical archive**. GitHub original issue pages remain authoritative for bodies, comments, events, attachments, reactions and participants. The registry cannot honestly claim to preserve all historical content until those have been exported, integrity-checked and governed for privacy. The snapshot only represents its observation date.

Classes `external-assessment-candidate`, `mixed-review` and `development-or-unclassified` are triage signals, **not disposition or assurance outcomes**. Closed development issues must not be mass-imported as RAHP assessment cases; external assessment issue history must be discoverable in the registry without reopening resolved work or losing original links.

Run: `python3 scripts/validate_toolkit_archive.py` and `python3 -m unittest discover -s tests -p 'test_toolkit_archive.py'`.

The next archival increment is to export actual source bodies, paginated comments, timeline and attached evidence references, classify and reconcile cases, and prove a reversible durable transfer/alias contract. A historical index does not by itself stop the Toolkit publisher.
