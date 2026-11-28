import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_vti_041_replay as replay


class VtiReplayTests(unittest.TestCase):
    def test_exact_required_results(self):
        output = "\n".join(f"test {name} ... ok" for name in sorted(replay.JWT))
        summary = f"\ntest result: ok. {len(replay.JWT)} passed; 0 failed; 0 ignored;"
        replay.verify_output(output + summary, replay.JWT)
        for bad in (summary, output, output + summary.replace("0 ignored", "1 ignored"),
                    output + summary.replace("0 failed", "1 failed"),
                    output.replace("decode_rejects_foreign_signer", "different_test") + summary,
                    output + summary.replace(f"{len(replay.JWT)} passed", "0 passed"),
                    output + "\n" + output + summary, output + summary + summary,
                    output + "\ntest different_test ... ok" + summary):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                replay.verify_output(bad, replay.JWT)

    def test_wrong_or_dirty_checkout_refused(self):
        for result in (["0" * 40], [replay.REVISION, " M Cargo.lock"]):
            with patch.object(replay.subprocess, "check_output", side_effect=result):
                with self.assertRaisesRegex(ValueError, "wrong or modified"):
                    replay.verify_checkout(Path("."))
        with patch.object(replay.subprocess, "check_output", side_effect=[replay.REVISION, ""]):
            replay.verify_checkout(Path("."))

    def test_dependency_edges_and_versions_are_distinct_requirements(self):
        deps = {name: {"version": value} for name, value in replay.DECLARED.items()}
        packages = [{"name": name, "version": version,
                     "dependencies": sorted(replay.EDGES.get(name, []))}
                    for name, versions in replay.RESOLVED.items() for version in versions]
        packages += [{"name": name, "version": "0.0.1", "dependencies": sorted(replay.EDGES[name])}
                     for name in ("vti-common", "vti-trust-task-server")]
        replay.qualify_documents(deps, packages)
        wrong_deps = copy.deepcopy(deps)
        wrong_deps["trust-tasks-rs"]["version"] = "0.39.0"
        with self.assertRaisesRegex(ValueError, "wrong declaration"):
            replay.qualify_documents(wrong_deps, packages)
        wrong = copy.deepcopy(packages)
        next(p for p in wrong if p["name"] == "trust-tasks-rs")["version"] = "0.39.0"
        with self.assertRaisesRegex(ValueError, "wrong resolution"):
            replay.qualify_documents(deps, wrong)
        for name, edge in (("trust-tasks-https", "jsonwebtoken 11.1.0"),
                           ("trust-tasks-rs", "jsonschema 0.60.2"),
                           ("vti-common", "jsonwebtoken 11.1.0")):
            wrong = copy.deepcopy(packages)
            next(p for p in wrong if p["name"] == name)["dependencies"] = [edge]
            with self.assertRaisesRegex(ValueError, "wrong dependency edge"):
                replay.qualify_documents(deps, wrong)

    def test_canonical_record_and_workflow_preserve_evidence_boundary(self):
        record = json.loads((ROOT / "ops/assessments/dtg-spec-dependency-source-materiality-2026-11.json").read_text())
        obs = record["downstream_vti_041_observation"]
        self.assertEqual(obs["revision"], replay.REVISION)
        self.assertEqual(obs["declared_versions"], replay.DECLARED)
        self.assertEqual(obs["lockfile_versions"], replay.RESOLVED)
        self.assertEqual({key: set(value) for key, value in obs["dependency_edges"].items()}, replay.EDGES)
        self.assertTrue(obs["target_native_runtime_reproduced"])
        self.assertTrue(record["target_native_vti_tests_executed"])
        result = obs["native_replay"]
        self.assertTrue(result["executed"])
        self.assertEqual(result["source_revision"], replay.REVISION)
        self.assertEqual(result["registry_tested_revision"], "597725a9209f6f4d2f22a28b17656c96e97acc2d")
        self.assertEqual(result["workflow_job_url"], "https://github.com/sankarshanmukhopadhyay/rahp-assessment-registry/actions/runs/46102841589/job/140848950272")
        self.assertEqual(result["jwt_unit_tests_passed"], len(replay.JWT))
        self.assertEqual(result["trust_task_spine_tests_passed"], len(replay.SPINE))
        self.assertEqual((result["failed_tests"], result["ignored_tests"]), (0, 0))
        self.assertFalse(obs["critical_extension_consumer_reproduced"])
        self.assertEqual(record["group_assurance_determination"], "not_assessed")
        case = json.loads((ROOT / "cases/dtg/spec-dependency-2026-11.json").read_text())
        self.assertEqual(case["assessment"]["determination"], "not_assessed")
        self.assertFalse(case["assessment"]["independent_review"])
        self.assertFalse(case["evidence"]["runtime_reproduced"])
        self.assertIn(result["workflow_job_url"], [source["url"] for source in case["evidence"]["sources"]])
        self.assertTrue(all(residual["status"] == "open" for residual in case["residuals"]))
        workflow = yaml.safe_load((ROOT / ".github/workflows/dtg-88-source-consumer-replay.yml").read_text())
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        job = workflow["jobs"]["vti-041-consumer-reassessment"]
        checkout = next(step for step in job["steps"] if step.get("with", {}).get("path") == "vti")
        self.assertEqual(checkout["with"]["ref"], replay.REVISION)
        self.assertEqual(checkout["with"]["repository"], obs["repository"])
        self.assertIs(checkout["with"]["persist-credentials"], False)
        self.assertIn("python3 scripts/verify_vti_041_replay.py vti", [step.get("run") for step in job["steps"]])
