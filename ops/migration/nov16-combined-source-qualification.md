# November 16 DTG combined-group source qualification

The source is Monitor commit `7e2813c8daf867a21e4064513cc83612726aeb44`,
`data/findings/2026/11/16.json`. Seven findings in the two combined
groups have directly observed same-repository commit URLs. The six
remaining findings reference annotated release tags. The committed
`nov16-annotated-tags.json` enumerates the six original finding IDs,
tag object SHAs and target commit SHAs established by GitHub's tag-reference
and tag-object API. The existing read-only verifier re-reads every tag
reference and tag object during the pinned routing-parity workflow.

The added group coverage verifier fails if any group member is missing,
duplicated, changed, relabeled as a direct commit, or covered by supplemental
tag evidence that does not match the exact source-observed release URL. It
checks **all** members of both original groups; it does not quietly filter out
unresolved members. The verification receipt is retained alongside the two
router parity outputs.

The tag target is **supplemental** immutable provenance: the original
Monitor observation did *not* include a commit URL for those six findings.
A verified tag does not itself establish the responsible assessor, permission
to use a grouped owner, Registry observation delivery, Toolkit consumer
migration or independent acceptance. An annotated tag may be retargeted
after a successful check; future qualifying runs must re-read the tag ref.

No Toolkit transfer ledger entry, case, reviewer assignment or publisher
is changed by this tranche. Group source evidence is necessary but
insufficient for an operational cutover.
