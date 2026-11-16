# Manual registry-native intake pilot

The [Registry intake pilot](../.github/workflows/registry-intake-pilot.yml) executes the normal `registry_intake.py` consumer from the **registry repository**, using GitHub's native repository-scoped Actions token with Issues-write permission. It does not need a Toolkit-to-registry PAT.

The workflow also performs a **no-write dry-run automatically on main when its workflow, intake script or pinned manifest changes**. Only a manual dispatch with `apply=true` can request write mode. Its initial manifest is intentionally restricted to one already reviewed, transferred finding: [the RAHP #1203 → registry #4 pilot](../intake/manifests/network-answer-pilot.json). Both dry-run and explicit apply must return `existing-owner` for issue #4; a create action fails the workflow. It cannot mint a second assurance result or mutate Toolkit issues.

1. Open Actions → **Registry intake pilot (manual)** → Run workflow.
2. Leave `apply=false` for the first dry-run. Inspect the job summary and receipt artifact.
3. If desired, run `apply=true` to test authenticated write-mode reconciliation **without an expected write**. It must still detect registry #4 and return `existing-owner`.
4. If either run fails, inspect the source/ownership error and do not enable wider intake.

The workflow does **not** monitor external repositories on a schedule; it does not create DPIP or Interop Lab examinations and does not implement the RAHP controller. Future broader manifests require reviewed conversion and acceptance criteria; the demonstrated pilot does not justify forwarding arbitrary Toolkit events or updating the current DPIP return-token destination.

All source pins and assessment claims remain bounded to existing registry case evidence; a GitHub workflow success is not RAHP assurance PASS.
