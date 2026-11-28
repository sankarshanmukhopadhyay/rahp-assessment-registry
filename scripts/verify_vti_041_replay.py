"""Qualify the VTI 0.41 subject and reject vacuous native test results."""
import argparse
import re
import subprocess
import tomllib
from pathlib import Path

REVISION = "0366ad0b3ce4604d2b4cd634cb93486c12dcff03"
DECLARED = {"trust-tasks-rs": "0.41.0", "trust-tasks-https": "0.41",
            "jsonwebtoken": "12.0.0", "jsonschema": "0.61"}
RESOLVED = {"trust-tasks-rs": ["0.41.2"], "trust-tasks-https": ["0.41.0"],
            "jsonwebtoken": ["11.1.0", "12.0.0"], "jsonschema": ["0.60.2", "0.61.2"]}
EDGES = {"trust-tasks-https": {"jsonwebtoken 12.0.0", "trust-tasks-rs"},
         "trust-tasks-rs": {"jsonschema 0.61.2"},
         "vti-common": {"jsonwebtoken 12.0.0", "trust-tasks-rs"},
         "vti-trust-task-server": {"trust-tasks-https", "trust-tasks-rs"}}
JWT = {"auth::jwt::tests::" + name for name in (
    "test_jwt_roundtrip", "for_audience_tokens_are_refused_across_audiences",
    "decode_rejects_expired_token", "decode_rejects_tampered_signature",
    "decode_rejects_alg_none_header", "decode_rejects_foreign_signer",
    "decode_rejects_missing_required_claims", "jti_defaults_empty_and_round_trips_when_set",
    "test_jwt_tee_attested_true", "test_jwt_tee_attested_false_omitted",
    "test_jwt_audience_parameterized", "decode_rejects_empty_token",
    "decode_rejects_malformed_structure")}
SPINE = {"a_fresh_document_is_dispatched_and_its_answer_signed",
         "a_stale_issued_at_is_refused_before_dispatch", "a_document_for_another_recipient_is_refused",
         "a_required_proof_that_is_missing_is_refused", "a_tampered_proof_is_refused",
         "a_messaging_document_must_be_signed_by_its_sender",
         "a_duplicate_is_answered_with_the_first_result_and_not_run_again",
         "a_refused_dispatch_releases_its_id", "a_missing_issued_at_is_refused",
         "a_valid_proof_reaches_the_handler_as_the_verified_signer",
         "an_unsigned_public_document_over_messaging_runs_anonymous_where_accepted",
         "an_unrecorded_response_is_not_handed_to_a_redelivery",
         "an_unsupported_version_names_the_served_versions",
         "an_oversized_document_is_refused_before_it_is_parsed",
         "a_body_that_is_not_a_document_is_refused", "the_https_route_serves_the_spine"}


def qualify(root):
    deps = tomllib.loads((root / "Cargo.toml").read_text())["workspace"]["dependencies"]
    packages = tomllib.loads((root / "Cargo.lock").read_text())["package"]
    qualify_documents(deps, packages)


def qualify_documents(deps, packages):
    for name, expected in DECLARED.items():
        if deps[name]["version"] != expected:
            raise ValueError(f"wrong declaration: {name}")
    for name, expected in RESOLVED.items():
        if sorted(p["version"] for p in packages if p["name"] == name) != expected:
            raise ValueError(f"wrong resolution: {name}")
    for name, expected in EDGES.items():
        matches = [p for p in packages if p["name"] == name]
        if len(matches) != 1 or not expected <= set(matches[0].get("dependencies", [])):
            raise ValueError(f"wrong dependency edge: {name}")


def verify_output(output, required):
    passed = re.findall(r"^test (\S+) \.\.\. ok$", output, re.M)
    summaries = re.findall(r"^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;", output, re.M)
    if (len(summaries) != 1 or set(passed) != required or
            len(passed) != len(required) or
            summaries[0] != (str(len(required)), "0", "0")):
        raise ValueError("missing, ignored, failed, duplicated or unaccounted native tests")


def verify_checkout(root):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if head != REVISION or subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip():
        raise ValueError("wrong or modified VTI checkout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    verify_checkout(root)
    qualify(root)
    for command, required in [
        (["-p", "vti-common", "--lib", "auth::jwt::tests"], JWT),
        (["-p", "vti-trust-task-server", "--test", "spine"], SPINE),
    ]:
        result = subprocess.run(["cargo", "test", "--locked", *command, "--", "--test-threads=1"],
                                cwd=root, text=True, stdout=subprocess.PIPE)
        print(result.stdout, flush=True)
        result.check_returncode()
        verify_output(result.stdout, required)
    verify_checkout(root)
    print("Bounded VTI JWT and receiver-spine replay only; no extCritical or case PASS claim.")


if __name__ == "__main__":
    main()
