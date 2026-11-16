# Staged DTG operations code relocation

This folder contains **byte-identical** copies from canonical Toolkit commit `70298566dc897669e22bf37759843d6b7c0597d2`, staged for ownership migration:

| Registry staged file | Toolkit source at pinned commit |
| --- | --- |
| `finding_model.py` | `tools/finding_model.py` |
| `dtg_portfolio_routing.py` | `tools/dtg_portfolio_routing.py` |
| `fetch_dtg_portfolio_snapshot.py` | `tools/fetch_dtg_portfolio_snapshot.py` |
| `config/assurance-routing.yaml` | `instances/dtg/assurance-routing.yaml` |
| `config/finding-normalization.yaml` | `instances/dtg/finding-normalization.yaml` |

Each copied Git blob SHA is identical to its Toolkit source. [DTG routing parity CI](../../.github/workflows/dtg-routing-code-parity.yml) compares all five emitted routing/event/composition artifacts against canonical Toolkit execution using the **same immutable 2026-11-13 Monitor source and pinned code**. It rejects any byte-level discrepancy, missing artifact or false empty parity.

**Authority:** These scripts are an instance-specific operational adapter, not a new portable RAHP method or authorized determination engine. Portable RAHP method, schemas and generic assurance/inference engine remain canonical in Toolkit. During migration the source files are temporarily duplicated; **do not** remove Toolkit code or switch production routing until parity, controller integration, DPIP/Lab returns and rollback are proven. No issue writes or new assurance outcomes occur in this staged workflow.

Once the new consumer contract is verified, Registry can use these as its owned implementation and Toolkit can remove the instance-specific operational copies in a separately validated transition. Do not treat a successful historical parity test as a current full-cycle assurance result.
