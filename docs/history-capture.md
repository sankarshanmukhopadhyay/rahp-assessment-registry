# Full-content source history capture: bounded exporter

The registry's historical [metadata baseline](../archive/README.md) indexes all 769 Toolkit issues on 2026-11-16. The new `scripts/capture_toolkit_history.py` can **retrieve and retain** original issue JSON (including issue body), all repository-wide issue comments and issue events, filtering out pull requests and other repositories. It fully paginates each list and rejects duplicate/missing issue identities, mismatched canonical links and a discrepancy between each issue's GitHub-declared comment count and captured comments. It preserves verbatim GitHub API records, source timestamps and authorship without altering original issues.

Use [the manual export workflow](../.github/workflows/capture-toolkit-history.yml). The export creates `issues.jsonl`, `comments.jsonl`, `events.jsonl` and a JSON manifest with per-file SHA-256 digests and original API page counts. These are downloadable **short-lived GitHub Actions artifacts (30-day retention)**. A successful artifact is a portable evidence/continuity *candidate*, not yet a permanent historical archive in the Registry repository.

**Scope limits:** repository-wide issue events do not necessarily include every issue-specific timeline-only event class, hidden/removed external attachments or source code/evidence behind links. Completeness and privacy require subsequent review and persistent, governed storage. A full archive must not be claimed until every case's complete source record, export integrity, participant privacy, live transfer and compatibility are verified. An export is not an authority migration and cannot convert unknown or incomplete assurance to PASS.

No automatic issue creation, reassessment or source closure occurs during capture. This is intentionally an independent read-only job, not a source-monitor scheduled process. Report HTTP errors without echoing sensitive response bodies. Do not store GitHub tokens in artifacts.

## Coverage correction (2026-11-16)

Initial export [Actions run 43874479910](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/actions/runs/43874479910) contained only 57 source issue bodies because the GitHub Issues collection defaults to `state=open`. Its success **did not** qualify complete history. The exporter now explicitly requests `state=all` and refuses to complete below the independently observed 769-source-issue baseline or without closed pilot #1203. No earlier artifact should be labelled a complete archive. Additional regression tests prohibit silently reverting to the open-only query.
