import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_release_tag_pins as tags


def fixture():
    repo = "OpenVTC/verifiable-trust-infrastructure"
    name = "vti-rooms-v0.36.0"
    fid = "a" * 20
    item = {"finding_id": fid, "repository": repo, "tag_name": name,
            "tag_object_sha": "b" * 40, "target_commit_sha": "c" * 40}
    source = [{"finding_id": fid, "repository": repo,
               "evidence_urls": ["https://github.com/" + repo + "/releases/tag/" + name]}]
    manifest = {"schema": "rahp-registry-annotated-tag-evidence/v1", "items": [item]}
    def fetch(url):
        if "/ref/tags/" in url:
            return {"object": {"type": "tag", "sha": "b" * 40}}
        if "/tags/" in url:
            return {"tag": name, "object": {"type": "commit", "sha": "c" * 40}}
        raise AssertionError("unexpected URL")
    return manifest, source, fetch


class ReleaseEvidenceTests(unittest.TestCase):
    def test_verified_tag_is_separate_from_source_commit_pin(self):
        r = tags.qualify(*fixture())
        self.assertEqual(r["qualified_count"], 1)
        self.assertFalse(r["supplemental_verified"][0]["source_observed_commit_url"])
        self.assertFalse(r["ownership_transfer_accepted"])

    def test_complete_group_requires_exact_observed_and_supplemental_pin(self):
        manifest, source, fetch = fixture()
        source.append({"finding_id": "b"*20, "repository": source[0]["repository"],
                       "evidence_urls": [
                         "https://github.com/" + source[0]["repository"] + "/commit/" + "d"*40]})
        group = {
            "assessment_key": "dtg:portfolio:combined:bounded",
            "source_observations": [
                {"finding_id": "a"*20, "repository": source[0]["repository"],
                 "revisions": [], "source_pin_status": "unresolved"},
                {"finding_id": "b"*20, "repository": source[0]["repository"],
                 "revisions": ["d"*40], "source_pin_status": "commit-evidence"}],
            "source_pins": [{"repository": source[0]["repository"], "revision": "d"*40}],
            "unanchored_finding_ids": ["a"*20],
        }
        checked = tags.qualify_combined_groups(tags.qualify(manifest, source, fetch), source, [group])
        self.assertEqual((checked["finding_count"], checked["supplemental_tag_findings"]), (2, 1))
        self.assertFalse(checked["cutover_authorized"])
        corrupted = copy.deepcopy(group)
        corrupted["source_observations"][1]["revisions"] = ["f"*40]
        with self.assertRaisesRegex(tags.TagPinError, "differs"):
            tags.qualify_combined_groups(tags.qualify(manifest, source, fetch), source, [corrupted])
        corrupted = copy.deepcopy(group)
        corrupted["unanchored_finding_ids"] = []
        with self.assertRaisesRegex(tags.TagPinError, "coverage"):
            tags.qualify_combined_groups(tags.qualify(manifest, source, fetch), source, [corrupted])
        missing = tags.qualify(manifest, source, fetch)
        missing["supplemental_verified"] = []
        with self.assertRaisesRegex(tags.TagPinError, "unresolved"):
            tags.qualify_combined_groups(missing, source, [group])
        changed_source = copy.deepcopy(source)
        changed_source[0]["evidence_urls"] = ["https://github.com/different/repo/commit/"+"e"*40]
        with self.assertRaisesRegex(tags.TagPinError, "unresolved"):
            tags.qualify_combined_groups(tags.qualify(manifest, source, fetch), changed_source, [group])

    def test_retargeted_tag_fails(self):
        manifest, source, fetch = fixture()
        def changed(url):
            if "/ref/tags/" in url:
                return {"object": {"type": "tag", "sha": "d" * 40}}
            return fetch(url)
        with self.assertRaisesRegex(tags.TagPinError, "retargeted"):
            tags.qualify(manifest, source, changed)

    def test_nonannotated_tag_fails(self):
        manifest, source, fetch = fixture()
        with self.assertRaisesRegex(tags.TagPinError, "not annotated"):
            tags.qualify(manifest, source,
                         lambda u: {"object": {"type": "commit", "sha": "c" * 40}})

    def test_wrong_object_target_fails(self):
        manifest, source, fetch = fixture()
        def forged(url):
            if "/tags/" in url and "/ref/tags/" not in url:
                return {"tag": "vti-rooms-v0.36.0",
                        "object": {"type": "commit", "sha": "e" * 40}}
            return fetch(url)
        with self.assertRaisesRegex(tags.TagPinError, "conflicting"):
            tags.qualify(manifest, source, forged)

    def test_unobserved_release_url_fails_before_network(self):
        manifest, source, fetch = fixture()
        source[0]["evidence_urls"] = ["https://github.com/example/other/releases/tag/v0"]
        with self.assertRaisesRegex(tags.TagPinError, "absent"):
            tags.qualify(manifest, source, lambda _: self.fail("unexpected network"))

    def test_duplicate_reviewed_finding_fails(self):
        manifest, source, fetch = fixture()
        manifest["items"].append(copy.deepcopy(manifest["items"][0]))
        with self.assertRaisesRegex(tags.TagPinError, "duplicate tagged"):
            tags.qualify(manifest, source, fetch)


if __name__ == "__main__":
    unittest.main()
