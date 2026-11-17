#!/usr/bin/env bash
set -euo pipefail
mkdir -p build/group
python3 toolkit/tools/dtg_portfolio_routing.py \
  --findings monitor/data/findings/2026/11/16.json \
  --policy toolkit/instances/dtg/assurance-routing.yaml \
  --normalization-policy toolkit/instances/dtg/finding-normalization.yaml \
  --snapshot-date 2026-11-16 --out-dir build/group
python3 scripts/verify_release_tag_pins.py \
  --evidence ops/migration/nov16-annotated-tags.json \
  --findings monitor/data/findings/2026/11/16.json \
  --combined-events build/group/combined-events.json \
  --out build/group/source-evidence.json
python3 scripts/qualify_monitored_owner.py \
  --candidate ops/migration/spec-dependency-owner-candidate.json \
  --combined build/group/combined-events.json \
  --evidence build/group/source-evidence.json \
  --out build/group/owner-candidate.json
python3 scripts/verify_maintainer_cutover_acceptance.py \
  --candidate-receipt build/group/owner-candidate.json \
  --out build/group/maintainer-scope.json --require-accepted
python3 scripts/qualify_monitored_group_intent.py \
  --manifest outbox/pending/spec-dependency-2026-11-16.json \
  --combined build/group/combined-events.json \
  --owner-candidate build/group/owner-candidate.json \
  --maintainer-status build/group/maintainer-scope.json \
  --out build/group/group-intent.json
python3 scripts/registry_monitored_group_delivery.py \
  --manifest outbox/pending/spec-dependency-2026-11-16.json \
  --combined build/group/combined-events.json \
  --candidate build/group/owner-candidate.json \
  --receipt build/group/owner-delivery.json "$@"
