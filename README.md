# RAHP Assessment Registry

A public case-management surface for source-qualified RAHP assessments, evidence
references, accountable disposition and reassessment across trust-system projects.

The Registry records **what is being examined, who owns the case, the
evidentiary basis, what remains unresolved, and when reassessment is required**.
It does not replace the authoritative specification, the assessed implementation,
or the [RAHP Toolkit](https://github.com/sankarshanmukhopadhyay/rahp-toolkit)
method and execution engine.

## Start here

1. Read [governance and authority](GOVERNANCE.md) and the
   [case lifecycle](docs/case-lifecycle.md).
2. Inspect a source-pinned case such as
   [ONDTF-GOV-006](cases/ondtf/emergency-authority-v1.json) and its
   [Registry issue owner](https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/issues/47).
3. Validate case records with `python3 scripts/validate_cases.py` and
   `python3 -m unittest discover -s tests -v`.
4. Use the [assessment-case template](.github/ISSUE_TEMPLATE/assessment-case.md)
   for a genuinely distinct assurance proposition, not merely a new upstream
   commit or release.

## Authority and responsibilities

| Surface | Responsible for | Does not establish |
| --- | --- | --- |
| [DTG Portfolio Monitor](https://github.com/sankarshanmukhopadhyay/dtg-portfolio-monitor) | Observed upstream changes, materiality inputs and source provenance | RAHP assessment results |
| [RAHP Toolkit](https://github.com/sankarshanmukhopadhyay/rahp-toolkit) | Portable method, engine, schemas, validators, execution and result contracts | Authority over external specifications or Registry case admission |
| **This Registry** | Case identity, admission, evidence references, administrative lifecycle, residual ownership, reassessment and referral coordination | Independent conformance certification or invented RAHP results |
| Source and specialist repositories | Their own normative artifacts, implementations, remediation and qualified specialist determinations | Other participants' authority |

Case identity, source revisions, Toolkit execution identifiers, GitHub issue
numbers and specialist referral identifiers remain **separate namespaces**.
An issue close, validated record, successful CI run or specialist acknowledgment
cannot be promoted to RAHP PASS. An assessment determination other than
`not_assessed` must be attributable to an actual RAHP result.

## Case admission and lifecycle

An assessment case describes one materially distinct proposition about a
defined subject and context. Observations of the same proposition should
extend attributable evidence and trigger an explicit reassessment decision
rather than create duplicate issues. The
[case lifecycle](docs/case-lifecycle.md) distinguishes administrative
state, evidence state and RAHP determination.

The [source-controlled intake and replay contract](docs/durable-intake-replay.md)
provides a bounded, reviewed issue-publication path with live owner checks and
replay receipts. Its authorization depends on the provenance and route of the
case; it is not a general-purpose permission to create cases from every
observed change. A missing or ambiguous owner acknowledgment is retained as
unresolved, not treated as successful delivery.

## Monitoring and assurance execution

The [DTG live monitoring shadow](docs/live-shadow-monitoring.md) compares
source-qualified observations and routing without writing assessment issues.
Its outputs are observations and potential admission/reassessment signals, not
assurance determinations.

The [canonical assessment workflow](.github/workflows/registry-canonical-assessment.yml)
invokes a pinned Toolkit execution contract. For example, the
[ONDTF-GOV-006 case](cases/ondtf/emergency-authority-v1.json) has a
source-pinned controller result of `INDETERMINATE / evidence-required`
when target-native evidence is absent. That is a meaningful recorded outcome,
not evidence of conformance.

Where a proposition genuinely requires specialist judgment or executable
evidence, follow [DPIP and Interop Lab referral guidance](docs/specialist-routing.md).
A referral requires an admitted, source-bound target and attributable return.
No specialist result is inferred from an empty referral list.

## Evidence, history and references

Cases reference authoritative source commits, issue threads, evidence and
result artifacts rather than silently copying or rewriting upstream history.
Use the [historical locator](archive/README.md) and
[case succession rules](docs/case-succession.md) to follow provenance across
owners. See the [execution journal](docs/registry-execution-journal.md) for
stable execution and evidence identities.

Operational procedures, source-ownership controls and implementation
limitations are maintained under [docs/](docs/) and [ops/](ops/). They are not
substitutes for the Registry's current case records or actual run evidence.

## Contributing and licensing

See [CONTRIBUTING.md](CONTRIBUTING.md). Code and validation scripts are
Apache-2.0 ([LICENSE](LICENSE)). Source evidence remains subject to its
original ownership, attribution and licensing; a reference does not relicense
external material.
