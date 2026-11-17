# Live Registry-directed DPIP return reader

Run the source-qualified, read-only Registry return reader against an existing
case with a previously accepted DPIP referral:

    GITHUB_TOKEN=... python3 scripts/registry_dpip_live_reconcile.py \
      --case cases/dtg/accepted-example.json --dpip-issue 123 \
      --toolkit toolkit --receipt build/registry-dpip/receipt.json

The Toolkit checkout must match the pinned canonical revision. The reader
uses complete live GitHub issue and comment histories; it invokes Toolkit's
actual portable-result consumer and compares the qualified observation against
the Registry case-scoped persistent epoch journal.

A missing case referral, wrong source/epoch, changed owner, incomplete return,
unavailable history or conflicting persisted disposition fails closed.
No source-controlled case currently has an accepted live Registry-directed
DPIP referral, so this CLI is not an assertion that a live specialist return
has been observed. It never writes GitHub issues or comments, authenticates a
specialist independent of the original transport, imports assurance or
reconciles the Toolkit controller. Operational write/journal activation is
separate and requires the shared serialized publication boundary.
