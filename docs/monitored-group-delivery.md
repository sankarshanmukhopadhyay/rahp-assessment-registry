# Monitored group owner delivery

The candidate for Toolkit #272 has an authenticated, source-digest-bound
maintainer scope acceptance at Registry #11. The approval is **not** a
publisher fence or a claim of independent assurance.

Use the guarded delivery entry point only when all are true:

* The canonical pinned Monitor/Tookit router reproduces the exact four-finding
  group event and Registry's candidate qualifier rechecks unique live #272.
* The current GitHub #11 maintainer scope comment matches those receipts.
* Toolkit main contains one exact \`reserved_group\` entry referencing the
  already committed pending Registry intent, matching the actual original
  event digest and all source finding IDs.
* No competing Registry owner exists, and GitHub main branches remain stable.

The main-only delivery command takes the exact combined events, live
candidate receipt and source-controlled Registry manifest as inputs. It
creates only the administrative Registry successor and performs a complete
authoritative issue reread before acknowledging a POST; timeout-after-commit
can therefore resolve without creating a second case on replay.

This entry point does **not** assert that all Toolkit workflow producers are
fenced, that the current observation is durably delivered, that specialist
consumers have migrated, or that rollback has been executed. It does not
alter Toolkit's group reservation or authorize the final writer switch.
An empty transfer ledger rejects the write. A live activation must be
coordinated with Toolkit publication and validated through the complete
source/owner pipeline, not by invoking this module with fixture receipts.
