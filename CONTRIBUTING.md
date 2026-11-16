# Contributing

Before proposing a case, check whether an existing case already owns the *same proposition, subject, source context and intended decision*. A new upstream commit or release is not by itself a new case.

Use a branch and pull request for changes to `cases/`, validation code, or governance. Include:
- exact source and assessment-context references;
- evidence class, freshness and unresolved limitations;
- proposed administrative disposition and distinct assurance outcome, if any;
- reason a new case is necessary, rather than updating an existing one;
- residual owner and reassessment trigger.

Run:

```sh
python3 scripts/validate_cases.py
python3 -m unittest discover -s tests -v
```

Do not alter upstream issue states, invent reviewer acceptance, or suppress unknown evidence to obtain a passing validator. Keep credentials and sensitive case data out of commits. Respect any active DCO, required review and protection controls. DCO sign-offs certify actual contributions; no contributor may certify another person's authorship without authorization.
