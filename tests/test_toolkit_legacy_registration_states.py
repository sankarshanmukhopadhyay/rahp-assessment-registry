import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_toolkit_legacy_registration_states",
    ROOT / "scripts/verify_toolkit_legacy_registration_states.py",
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class LegacyRegistrationStateTests(unittest.TestCase):
    def setUp(self):
        self.replacements = [
            {"id": index + 1, "path": path, "state": "active"}
            for index, path in enumerate(module.REPLACEMENTS)
        ]
        self.legacy = {
            ident: {"id": ident, "path": path, "state": "disabled_manually"}
            for ident, path in module.LEGACY
        }

    def verify(self, inventory=None, lookup=None):
        return module.verify(
            {"workflows": self.replacements} if inventory is None else inventory,
            (lambda workflow_id: self.legacy[workflow_id])
            if lookup is None else lookup,
        )

    def test_exact_old_registration_retirement_and_new_replacements(self):
        evidence = self.verify()
        self.assertTrue(evidence["legacy_registration_retirement_verified"])
        self.assertFalse(evidence["historical_dispatch_denial_observed"])
        self.assertFalse(evidence["registry_cutover_authorized"])
        self.assertFalse(evidence["toolkit_external_case_publication_exclusive"])
        self.assertEqual(len(evidence["retired_legacy_registrations"]), 2)

    def test_missing_duplicate_or_disabled_replacement_fails(self):
        for inventory in (
            {"workflows": self.replacements[:1]},
            {"workflows": self.replacements + [self.replacements[0].copy()]},
            {"workflows": [dict(self.replacements[0], state="disabled_manually"),
                           self.replacements[1]]},
            {"workflows": None},
        ):
            with self.subTest(inventory=inventory), self.assertRaises(module.RegistrationError):
                self.verify(inventory=inventory)

    def test_reenabled_or_substituted_old_registration_fails(self):
        for index, (identity, path) in enumerate(module.LEGACY):
            for prop, value in (("id", identity + 1),
                                ("path", ".github/workflows/foreign.yml"),
                                ("state", "active"),
                                ("state", "disabled_inactivity")):
                record = dict(self.legacy[identity], **{prop: value})
                lookup = lambda ident, target=identity, record=record: (
                    record if ident == target else self.legacy[ident])
                with self.subTest(index=index, prop=prop), self.assertRaises(module.RegistrationError):
                    self.verify(lookup=lookup)

    def test_failed_read_never_yields_green(self):
        with self.assertRaises(KeyError):
            self.verify(lookup=lambda identity: {} if identity == module.LEGACY[0][0]
                        else self.legacy[identity])


if __name__ == "__main__":
    unittest.main()
