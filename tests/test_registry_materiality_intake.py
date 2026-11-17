import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_materiality_intake as materiality
import registry_intake as intake
import registry_outbox as outbox

MANIFEST = json.loads((ROOT / "outbox/pending/network-answer-pilot.json").read_text())
EVENT = MANIFEST["event"]
PIN = EVENT["source_revision"]
FINDING = {
    "finding_id": EVENT["finding_id"],
    "repository": EVENT["source_repository"],
    "evidence_urls": [EVENT["source_url"],
                      f"https://github.com/{EVENT['source_repository']}/commit/{PIN}"],
    "materiality": "high", "assurance_impact": "potentially-breaking",
    "review_status": "unreviewed", "state": "open",
}
OTHER = {**FINDING, "finding_id": "another-material-finding"}
ROUTED = [{"finding": FINDING, "outcome": "covered"}]
OWNER = {
    "number": 4, "state": "open",
    "html_url": f"https://github.com/{intake.REGISTRY}/issues/4",
    "body": f"<!-- rahp-registry-case:RAHP-AR-DTG-0001 -->\n{PIN}\n{EVENT['finding_id']}",
}


class MaterialityIntakeTests(unittest.TestCase):
    def test_exact_reviewed_current_finding_reconciles_existing_case(self):
        receipt = materiality.plan([FINDING, OTHER], ROUTED, MANIFEST, [OWNER])
        self.assertEqual(receipt["state"], "existing_owner")
        self.assertEqual(receipt["owner_number"], 4)
        self.assertEqual(receipt["unadmitted_routed_count"], 0)
        self.assertFalse(receipt["existing_issue_mutated"])
        self.assertEqual(len(receipt["monitored_source_sha256"]), 64)
        self.assertEqual(len(receipt["router_output_sha256"]), 64)
        self.assertEqual(len(receipt["approved_manifest_sha256"]), 64)

    def test_unapproved_current_route_is_not_created(self):
        receipt = materiality.plan([OTHER], [{"finding": OTHER, "outcome": "combined"}],
                                    MANIFEST, [OWNER])
        self.assertEqual(receipt["state"], "outside_observed_materiality")
        self.assertFalse(receipt["approved_source_observed"])
        self.assertEqual(receipt["unadmitted_routed_count"], 1)
        self.assertFalse(receipt["new_issue_created"])

    def test_new_reviewed_material_case_can_only_be_pending(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["event"]["assessment_key"] = "dtg:case:approved-new-001"
        manifest["event"]["finding_id"] = "another-material-finding"
        receipt = materiality.plan([OTHER], [{"finding": OTHER, "outcome": "combined"}],
                                   manifest, [])
        self.assertEqual(receipt["state"], "pending_reviewed_creation")
        self.assertIsNone(receipt["owner_number"])
        self.assertFalse(receipt["new_issue_created"])
        self.assertFalse(receipt["toolkit_issue_written"])

    def test_covered_or_no_action_cannot_mint_new_case(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["event"]["assessment_key"] = "dtg:case:approved-covered-001"
        manifest["event"]["finding_id"] = "another-material-finding"
        for outcome in ("covered", "no-action"):
            with self.subTest(outcome=outcome):
                receipt = materiality.plan(
                    [OTHER], [{"finding": OTHER, "outcome": outcome}], manifest, []
                )
                self.assertEqual(receipt["state"], "no_new_case_for_covered_route")
                self.assertFalse(receipt["new_issue_created"])

    def test_new_revision_under_existing_proposition_never_creates_duplicate(self):
        new = copy.deepcopy(FINDING)
        new["finding_id"] = "changed-source-finding"
        new["evidence_urls"] = [EVENT["source_url"],
                                f"https://github.com/{EVENT['source_repository']}/commit/{'b'*40}"]
        manifest = copy.deepcopy(MANIFEST)
        manifest["event"]["finding_id"] = new["finding_id"]
        manifest["event"]["source_revision"] = "b" * 40
        receipt = materiality.plan([new], [{"finding": new, "outcome": "combined"}],
                                   manifest, [OWNER])
        self.assertEqual(receipt["state"], "reassessment_required")
        self.assertFalse(receipt["source_reassessment_applied"])
        self.assertFalse(receipt["new_issue_created"])

    def test_reviewed_new_case_continues_through_actual_outbox_consumer(self):
        manifest = copy.deepcopy(MANIFEST)
        manifest["event"]["assessment_key"] = "dtg:case:approved-new-001"
        manifest["event"]["finding_id"] = "another-material-finding"
        planned = materiality.plan(
            [OTHER], [{"finding": OTHER, "outcome": "combined"}], manifest, []
        )
        self.assertEqual(planned["state"], "pending_reviewed_creation")
        # The real delivery consumer is exercised; only GitHub HTTP is injected.
        ev = manifest["event"]
        issue = {
            "number": 31, "state": "open",
            "html_url": f"https://github.com/{intake.REGISTRY}/issues/31",
            "body": intake.render_body(ev),
        }
        remote = [[], [issue]]
        posts = []
        receipt = outbox.deliver(
            manifest, "test-token", apply=True, allow_new_case=True,
            load_issues=lambda: remote.pop(0),
            post=lambda payload: (
                posts.append(payload),
                {"number": 31, "html_url": issue["html_url"]}
            )[1],
        )
        self.assertEqual(receipt["state"], "owner_observed")
        self.assertEqual(receipt["owner_number"], 31)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["body"], intake.render_body(ev))
        self.assertIsNone(receipt["assurance_determination"])

    def test_reviewed_reassessment_cannot_become_outbox_create(self):
        newer = copy.deepcopy(FINDING)
        newer["finding_id"] = "changed-source-finding"
        newer["evidence_urls"] = [
            EVENT["source_url"],
            f"https://github.com/{EVENT['source_repository']}/commit/{'b'*40}",
        ]
        manifest = copy.deepcopy(MANIFEST)
        manifest["event"]["finding_id"] = newer["finding_id"]
        manifest["event"]["source_revision"] = "b" * 40
        planned = materiality.plan(
            [newer], [{"finding": newer, "outcome": "combined"}], manifest, [OWNER]
        )
        self.assertEqual(planned["state"], "reassessment_required")
        posts = []
        with self.assertRaisesRegex(outbox.DeliveryError, "reassessment required"):
            outbox.deliver(
                manifest, "test-token", apply=True,
                load_issues=lambda: [OWNER],
                post=lambda payload: posts.append(payload),
            )
        self.assertEqual(posts, [])


    def test_reviewed_batch_does_not_count_pending_creation_as_owner(self):
        second = copy.deepcopy(MANIFEST)
        second["event"]["assessment_key"] = "dtg:case:second-proposition"
        second["event"]["finding_id"] = OTHER["finding_id"]
        result = materiality.plan_many(
            [FINDING, OTHER], [{"finding": FINDING, "outcome": "covered"},
                              {"finding": OTHER, "outcome": "combined"}],
            {"first.json": MANIFEST, "second.json": second}, [OWNER])
        self.assertEqual(result["reviewed_intent_count"], 2)
        self.assertEqual(result["unreviewed_routed_count"], 0)
        self.assertEqual(result["without_confirmed_registry_owner_count"], 1)
        self.assertEqual([x["decision"]["state"] for x in result["intents"]],
                         ["existing_owner", "pending_reviewed_creation"])
        self.assertFalse(result["cutover_authorized"])

    def test_batch_outside_snapshot_does_not_infer_admission(self):
        result = materiality.plan_many(
            [OTHER], [{"finding": OTHER, "outcome": "combined"}],
            {"pilot.json": MANIFEST}, [OWNER])
        self.assertEqual(result["unreviewed_routed_count"], 1)
        self.assertEqual(result["without_confirmed_registry_owner_count"], 1)
        self.assertEqual(result["intents"][0]["decision"]["state"],
                         "outside_observed_materiality")

    def test_batch_duplicate_key_or_finding_fails(self):
        for field, value in (("assessment_key", "dtg:case:other"),
                             ("finding_id", OTHER["finding_id"])):
            second = copy.deepcopy(MANIFEST)
            second["event"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    materiality.MaterialityError, "duplicate reviewed"):
                materiality.plan_many(
                    [FINDING, OTHER], ROUTED,
                    {"a.json": MANIFEST, "b.json": second}, [OWNER])

    def test_batch_empty_or_malformed_intent_fails(self):
        with self.assertRaisesRegex(materiality.MaterialityError, "at least one"):
            materiality.plan_many([FINDING], ROUTED, {}, [OWNER])
        with self.assertRaises(outbox.DeliveryError):
            materiality.plan_many([FINDING], ROUTED,
                                  {"bad.json": {"schema": "unknown"}}, [OWNER])

    def test_batch_reused_owner_across_keys_fails(self):
        other = copy.deepcopy(MANIFEST)
        other["event"]["assessment_key"] = "dtg:case:other"
        other["event"]["finding_id"] = OTHER["finding_id"]
        modified_owner = copy.deepcopy(OWNER)
        modified_owner["body"] += "\n" + intake.marker(other["event"]["assessment_key"]) + "\n" + OTHER["finding_id"]
        with self.assertRaisesRegex(materiality.MaterialityError, "ambiguous Registry owner"):
            materiality.plan_many(
                [FINDING, OTHER],
                [{"finding": FINDING, "outcome": "covered"},
                 {"finding": OTHER, "outcome": "combined"}],
                {"a.json": MANIFEST, "b.json": other}, [modified_owner])

    def test_duplicate_source_findings_rejected(self):
        with self.assertRaisesRegex(materiality.MaterialityError, "duplicate monitored"):
            materiality.plan([FINDING, FINDING], ROUTED, MANIFEST, [OWNER])

    def test_duplicate_routing_rejected(self):
        with self.assertRaisesRegex(materiality.MaterialityError, "duplicate routed"):
            materiality.plan([FINDING], ROUTED + ROUTED, MANIFEST, [OWNER])

    def test_routed_source_substitution_rejected(self):
        changed = copy.deepcopy(FINDING)
        changed["title"] = "replaced source"
        with self.assertRaisesRegex(materiality.MaterialityError, "does not match"):
            materiality.plan([FINDING], [{"finding": changed, "outcome": "covered"}],
                            MANIFEST, [OWNER])

    def test_missing_commit_pin_fails(self):
        f = {**FINDING, "evidence_urls": [EVENT["source_url"]]}
        with self.assertRaisesRegex(materiality.MaterialityError, "immutable commit"):
            materiality.plan([f], [{"finding": f, "outcome": "combined"}], MANIFEST, [OWNER])

    def test_wrong_revision_commit_fails(self):
        f = {**FINDING, "evidence_urls": [EVENT["source_url"],
                                        f"https://github.com/{EVENT['source_repository']}/commit/{'b'*40}"]}
        with self.assertRaisesRegex(materiality.MaterialityError, "reviewed source pin"):
            materiality.plan([f], [{"finding": f, "outcome": "combined"}], MANIFEST, [OWNER])

    def test_wrong_repository_fails(self):
        f = {**FINDING, "repository": "other/repository"}
        with self.assertRaisesRegex(materiality.MaterialityError, "source repository"):
            materiality.plan([f], [{"finding": f, "outcome": "combined"}], MANIFEST, [OWNER])

    def test_source_url_not_observed_fails(self):
        f = {**FINDING, "evidence_urls": [
            f"https://github.com/{EVENT['source_repository']}/commit/{PIN}"]}
        with self.assertRaisesRegex(materiality.MaterialityError, "source URL"):
            materiality.plan([f], [{"finding": f, "outcome": "combined"}], MANIFEST, [OWNER])

    def test_spoofed_owner_fails(self):
        o = dict(OWNER, body="<!-- unrelated-case -->")
        with self.assertRaisesRegex(materiality.MaterialityError, "owner reconciliation"):
            materiality.plan([FINDING], ROUTED, MANIFEST, [o])

    def test_duplicate_key_owners_fail(self):
        o2 = dict(OWNER, number=8,
                  body=intake.marker(EVENT["assessment_key"]))
        with self.assertRaisesRegex(materiality.MaterialityError, "owner reconciliation"):
            materiality.plan([FINDING], ROUTED, MANIFEST, [OWNER, o2])

    def test_closed_owner_does_not_reopen(self):
        o = dict(OWNER, state="closed")
        with self.assertRaisesRegex(materiality.MaterialityError, "owner reconciliation"):
            materiality.plan([FINDING], ROUTED, MANIFEST, [o])

    def test_unreviewed_assurance_pass_rejected(self):
        bad = copy.deepcopy(MANIFEST)
        bad["event"]["assurance_determination"] = "PASS"
        with self.assertRaises(intake.IntakeError):
            materiality.plan([FINDING], ROUTED, bad, [OWNER])

    def test_unreviewed_invalid_router_outcome_rejected(self):
        with self.assertRaisesRegex(materiality.MaterialityError, "unsupported"):
            materiality.plan([FINDING], [{"finding": FINDING, "outcome": "PASS"}],
                            MANIFEST, [OWNER])

    def test_nonmaterial_or_closed_route_rejected(self):
        for changed in (dict(FINDING, materiality="low"),
                        dict(FINDING, materiality="medium"),
                        dict(FINDING, assurance_impact="none"),
                        dict(FINDING, state="closed"),
                        dict(FINDING, review_status="accepted")):
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(materiality.MaterialityError, "unsupported"):
                    materiality.plan([changed], [{"finding": changed, "outcome": "covered"}],
                                    MANIFEST, [OWNER])

    def test_valid_router_unmapped_is_not_assurance(self):
        receipt = materiality.plan([FINDING],
                                   [{"finding": FINDING, "outcome": "UNMAPPED"}],
                                   MANIFEST, [OWNER])
        self.assertEqual(receipt["state"], "existing_owner")
        self.assertFalse(receipt["assurance_determination_imported"])


if __name__ == "__main__":
    unittest.main()
