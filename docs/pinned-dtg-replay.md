# Registry-executed pinned DTG routing replay

[The non-publishing replay workflow](../.github/workflows/pinned-dtg-routing-replay.yml) executes **existing canonical Toolkit routing logic from inside the Registry CI runner** using immutable source checkouts:

- RAHP Toolkit: `70298566dc897669e22bf37759843d6b7c0597d2`
- DTG Portfolio Monitor: `1a1982212bce36d79a5fb9dc6d58bec7b7d9e01a`
- Observed Monitor snapshot: `data/findings/2026/11/13.json`

It installs the pinned Toolkit dependencies, executes the existing `dtg_portfolio_routing.py` with canonical DTG policy and normalization, validates the provenance and source finding identity of all output classes, and retains the full event/routing JSON results and canonical source digest as an artifact. It issues **no GitHub issue writes** and does not promote any source judgment to RAHP PASS.

The replay is **historical**, not a fresh DTG monitor run. The observed Toolkit monitoring failure on 2026-11-16 (no two-day-fresh snapshot) remains a real freshness blocker. Pinned code executes inside the Registry runner without forking the Toolkit method or inference semantics. This establishes that the deployment boundary can move; it does **not** yet demonstrate old/new parity of controller state, DPIP durable returns, Interop Lab producer execution, archived issue migration or production cutover. For those gates, see [execution migration plan](execution-migration-plan.md).
