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
