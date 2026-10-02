"""Behavioral invariants for authoring data, not generated-image quality."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import portrait_spec as forge


class PortraitSpecTests(unittest.TestCase):
    def setUp(self):
        self.source = forge.load_json(forge.ROOT / "assets/examples/roadwarden.portrait.json")

    def reference(self, reference_id="identity-01", **overrides):
        ref = {"reference_id": reference_id, "locator": "/test/fixture.png", "role": "identity",
               "inspection": "inspected", "use": ["Preserve face"], "ignore": [],
               "approved_identity": True, "gm_only": False}
        ref.update(overrides)
        return ref

    def test_examples_and_starter_validate_but_starter_is_incomplete(self):
        for path in (forge.ROOT / "assets").rglob("*.portrait.json"):
            self.assertEqual(forge.validate(forge.load_json(path))[0], [], str(path))
        starter = forge.load_json(forge.ROOT / "assets/starter.portrait.json")
        self.assertFalse(forge.compile_source(starter)["briefs"][0]["render_ready"])
        self.assertTrue(forge.compile_source(self.source)["briefs"][0]["render_ready"])

    def test_compile_filters_notes_private_assets_and_unused_references(self):
        hidden = copy.deepcopy(self.source["assets"][0])
        hidden.update(asset_id="private-disguise", title="PRIVATE_FORM_SENTINEL", gm_only=True)
        self.source["assets"].append(hidden)
        self.source["gm_notes"] = ["PRIVATE_ROOT_SENTINEL"]
        self.source["subjects"][0]["gm_notes"] = ["PRIVATE_SUBJECT_SENTINEL"]
        self.source["references"] = [self.reference("unused", locator="UNUSED_REFERENCE_SENTINEL")]
        rendered = forge.compile_source(self.source)
        self.assertEqual(len(rendered["briefs"]), 1)
        self.assertFalse(any(sentinel in json.dumps(rendered) for sentinel in ("PRIVATE_ROOT_SENTINEL", "PRIVATE_SUBJECT_SENTINEL", "PRIVATE_FORM_SENTINEL", "UNUSED_REFERENCE_SENTINEL")))
        gm = forge.compile_source(self.source, "gm")
        self.assertEqual(len(gm["briefs"]), 2)
        self.assertNotIn("PRIVATE_ROOT_SENTINEL", json.dumps(gm))
        with self.assertRaises(ValueError):
            forge.compile_source(self.source, asset_id="private-disguise")

    def test_uninspected_reference_has_no_invented_directives(self):
        self.source["references"] = [self.reference(inspection="unavailable", approved_identity=False, use=[], locator="UNAVAILABLE_LOCATOR_SENTINEL")]
        self.source["subjects"][0]["identity_reference_ids"] = ["identity-01"]
        brief = forge.compile_source(self.source)["briefs"][0]
        self.assertFalse(brief["render_ready"])
        self.assertEqual(brief["unresolved_reference_ids"], ["identity-01"])
        self.assertEqual(brief["references"], [])
        self.assertNotIn("UNAVAILABLE_LOCATOR_SENTINEL", json.dumps(brief))
        self.source["references"][0]["use"] = ["Unobserved appearance"]
        self.assertTrue(forge.validate(self.source)[0])

    def test_public_consumer_cannot_require_private_reference(self):
        self.source["references"] = [self.reference(gm_only=True)]
        self.source["subjects"][0]["identity_reference_ids"] = ["identity-01"]
        self.assertTrue(forge.validate(self.source)[0])

    def test_unique_ids_subject_links_and_dimensions_are_checked(self):
        duplicate = copy.deepcopy(self.source)
        duplicate["assets"].append(copy.deepcopy(duplicate["assets"][0]))
        self.assertTrue(forge.validate(duplicate)[0])
        self.source["assets"][0]["subject_id"] = "missing"
        self.assertTrue(forge.validate(self.source)[0])
        self.source["assets"][0]["subject_id"] = "neris"
        self.source["assets"][0]["output"]["width_px"] = 1500
        self.assertTrue(forge.validate(self.source)[0])

    def test_cloak_change_preserves_identity_and_unrequested_fields(self):
        before = copy.deepcopy(self.source)
        change = forge.load_json(forge.ROOT / "assets/examples/cloak-color.change.json")
        after = forge.revise(self.source, change)
        self.assertEqual(self.source, before)
        self.assertEqual(after["revision"], 2)
        expected = copy.deepcopy(before)
        expected["revision"] = 2
        expected["subjects"][0]["visible_identity"]["clothing"] = change["changes"][0]["value"]
        expected["assets"][0]["art_direction"]["palette"] = change["changes"][1]["value"]
        self.assertEqual(after, expected)

    def test_stale_revision_and_noop_do_not_mutate(self):
        before = copy.deepcopy(self.source)
        for revision in (0, True):
            with self.assertRaises(ValueError):
                forge.revise(self.source, {"expected_revision": revision, "changes": [{"path": "/assets/0/expression", "value": "Smiling"}]})
        with self.assertRaises(ValueError):
            forge.revise(self.source, {"expected_revision": 1, "changes": [{"path": "/assets/0/expression", "value": self.source["assets"][0]["expression"]}]})
        self.assertEqual(self.source, before)

    def test_ancestor_replacement_cannot_bypass_descendant_lock(self):
        identity = copy.deepcopy(self.source["subjects"][0]["visible_identity"])
        identity["face_head"] = "Different face"
        change = {"expected_revision": 1, "changes": [{"path": "/subjects/0/visible_identity", "value": identity}]}
        with self.assertRaisesRegex(ValueError, "Locked field"):
            forge.revise(self.source, change)
        after = forge.revise(self.source, change, ["/subjects/0/visible_identity/face_head"])
        self.assertEqual(after["subjects"][0]["visible_identity"]["face_head"], "Different face")
        with self.assertRaises(ValueError):
            forge.revise(self.source, change, ["/subjects/0/visible_identity"])

    def test_ids_rebinding_and_lock_definitions_require_master_edit(self):
        for path, value in (("/assets/0/asset_id", "renamed"), ("/assets/0/subject_id", "other"), ("/locks", []), ("/revision", 9)):
            with self.assertRaises(ValueError):
                forge.revise(self.source, {"expected_revision": 1, "changes": [{"path": path, "value": value}]})

    def test_managed_revision_cannot_be_locked(self):
        self.source["locks"].append("/revision")
        self.assertTrue(forge.validate(self.source)[0])

    def test_append_set_preserves_old_ids_and_shared_subject(self):
        assets = copy.deepcopy(self.source["assets"])
        variant = copy.deepcopy(assets[0])
        variant.update(asset_id="neris-smiling", expression="Smiling")
        assets.append(variant)
        after = forge.revise(self.source, {"expected_revision": 1, "changes": [{"path": "/assets", "value": assets}]})
        briefs = forge.compile_source(after)["briefs"]
        self.assertEqual([item["asset_id"] for item in briefs], ["neris-bust", "neris-smiling"])
        self.assertEqual(briefs[0]["subject_id"], briefs[1]["subject_id"])
        self.assertEqual(briefs[0]["identity"], briefs[1]["identity"])

    def test_edit_target_requires_role_and_inspected_input(self):
        self.source["assets"][0]["intent"] = "edit"
        self.assertTrue(forge.validate(self.source)[0])
        self.source["references"] = [self.reference(role="edit_target", inspection="uninspected", use=[], approved_identity=False)]
        self.source["assets"][0]["edit_target_ref"] = "identity-01"
        self.assertFalse(forge.compile_source(self.source)["briefs"][0]["render_ready"])
        self.source["references"][0]["inspection"] = "inspected"
        brief = forge.compile_source(self.source)["briefs"][0]
        self.assertTrue(brief["render_ready"])
        self.assertEqual(brief["edit_target_ref"], "identity-01")

    def test_wardrobe_variant_preserves_shared_identity_and_original_outfit(self):
        variant = copy.deepcopy(self.source["assets"][0])
        variant.update(asset_id="neris-blue-cloak", wardrobe={"clothing": ["Navy blue wool cloak", "Charcoal linen tunic"]})
        variant["art_direction"]["palette"][0] = "Navy blue cloak"
        self.source["assets"].append(variant)
        briefs = forge.compile_source(self.source)["briefs"]
        self.assertIn("Moss green wool cloak", briefs[0]["identity"]["clothing"])
        self.assertIn("Navy blue wool cloak", briefs[1]["identity"]["clothing"])
        self.assertEqual(briefs[0]["subject_id"], briefs[1]["subject_id"])
        self.assertNotIn("Moss green", briefs[1]["image_instructions"])
        for field in ("face_head", "anatomy", "distinctive_features", "equipment"):
            self.assertEqual(briefs[0]["identity"][field], briefs[1]["identity"][field])

    def test_handoff_includes_only_relevant_approved_identity_and_style(self):
        self.source["references"] = [self.reference(), self.reference("style-01", role="style", approved_identity=False), self.reference("pose-01", role="pose", approved_identity=False), self.reference("unused", locator="UNUSED_SENTINEL")]
        self.source["subjects"][0]["identity_reference_ids"] = ["identity-01"]
        self.source["assets"][0]["reference_ids"] = ["style-01", "pose-01"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image-fixture.png"
            path.write_bytes(b"file-existence-fixture-not-a-render")
            bundle = forge.handoff(self.source, "neris-bust", str(path))
        self.assertEqual([item["reference_id"] for item in bundle["references"]], ["identity-01", "style-01"])
        self.assertNotIn("UNUSED_SENTINEL", json.dumps(bundle))
        self.assertNotIn("unopened warning", json.dumps(bundle))
        self.assertEqual(bundle["token_status"], "not_created")

    def test_loader_rejects_duplicate_keys_and_nonfinite_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for content in ('{"revision":1,"revision":2}', '{"value":NaN}'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    forge.load_json(path)

    def test_outputs_cannot_clobber_inputs_or_previous_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            path.write_text("original")
            with self.assertRaises(ValueError):
                forge.write_output({}, str(path), [str(path)])
            with self.assertRaises(FileExistsError):
                forge.write_output({}, str(path), [])
            self.assertEqual(path.read_text(), "original")

    def test_cli_compile_revision_and_invalid_text_have_observable_results(self):
        script = str(forge.ROOT / "scripts/portrait_spec.py")
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "player.json"
            run = subprocess.run([sys.executable, script, "compile", str(forge.ROOT / "assets/examples/roadwarden.portrait.json"), "-o", str(result)], capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(result.read_text())["briefs"][0]["asset_id"], "neris-bust")
            revised = Path(directory) / "revised.json"
            run = subprocess.run([sys.executable, script, "revise", str(forge.ROOT / "assets/examples/roadwarden.portrait.json"), str(forge.ROOT / "assets/examples/cloak-color.change.json"), "-o", str(revised)], capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(revised.read_text())["revision"], 2)
            run = subprocess.run([sys.executable, script, "compile", str(forge.ROOT / "assets/starter.portrait.json"), "--text"], capture_output=True, text=True, check=False)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(run.stdout, "")


class ImageMetadataTests(unittest.TestCase):
    def test_real_alpha_differs_from_opaque_rgba_and_checkerboard(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alpha.png"
            image = Image.new("RGBA", (8, 4), (50, 60, 70, 255))
            image.putpixel((0, 0), (50, 60, 70, 0))
            image.save(path)
            metadata = forge.inspect_image(str(path))
            self.assertEqual((metadata["width_px"], metadata["height_px"]), (8, 4))
            self.assertEqual(metadata["nonopaque_pixel_fraction"], 1 / 32)
            self.assertTrue(metadata["has_transparent_pixels"])
            image.putpixel((0, 0), (50, 60, 70, 255))
            image.save(path)
            metadata = forge.inspect_image(str(path))
            self.assertTrue(metadata["has_alpha"])
            self.assertFalse(metadata["has_transparent_pixels"])
            checkerboard = Image.new("RGB", (8, 4), "white")
            for x in range(8):
                for y in range(4):
                    checkerboard.putpixel((x, y), (120, 120, 120) if (x + y) % 2 else (255, 255, 255))
            checkerboard.save(path)
            metadata = forge.inspect_image(str(path))
            self.assertFalse(metadata["has_alpha"])
            self.assertFalse(metadata["has_transparent_pixels"])


if __name__ == "__main__":
    unittest.main()
