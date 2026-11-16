# Persistent source-history staging

The [stage-history workflow](../.github/workflows/stage-toolkit-history.yml) reruns the read-only full Toolkit public issue/comment/event capture, verifies the historical baseline and SHA-256 manifest, and compresses JSONL deterministically into a **new Git branch**, not protected `main`.

The workflow uses `contents:write` only to push that bounded `archive/toolkit-history-<run-id>` branch. It does not create a pull request, bypass rulesets, close source issues or change assurance outcomes. Its commit is signed off by the actual `github-actions[bot]` author; it must not impersonate a human maintainer.

A maintainer or authorized tool must examine the staged content, provenance, source counts, retention/privacy and false completeness risks and create an ordinary PR. Full source issue bodies, comments and repo-wide issue events are included; **per-issue timeline-only event types and linked external artifact bytes remain out of scope**. A merge only establishes a durable archival snapshot, not conformance or source authority transfer. New snapshots should be added only after material changes, not per monitoring tick.

Retain the original issue GitHub URLs, never reopen closed cases merely because an archive has been produced, and preserve Toolkit development history in the Toolkit repository.
