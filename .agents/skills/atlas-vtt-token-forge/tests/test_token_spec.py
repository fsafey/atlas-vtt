"""Focused source and pixel-metadata checks. Synthetic images are not campaign approvals."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def module_at(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


token = module_at(ROOT / "scripts/token_spec.py")
portrait = module_at(ROOT.parent / "atlas-vtt-portrait-forge/scripts/portrait_spec.py")


class TokenSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = token.load_json(ROOT / "assets/examples/roadwarden-pair.token.json")

    def change(self, path: str, value: Any) -> dict[str, Any]:
        return {"expected_revision": 1, "changes": [{"path": path, "value": value}]}

    def reference(self, ref_id: str = "anchor", **overrides: Any) -> dict[str, Any]:
        return {"reference_id": ref_id, "locator": "synthetic-fixture-not-an-inspected-image", "role": "identity",
                "inspection": "uninspected", "use": [], "ignore": [], "approved_identity": False,
                "gm_only": False, **overrides}

    def handoff(self, directory: str) -> dict[str, Any]:
        image = Path(directory) / "synthetic-portrait.png"
        Image.new("RGBA", (8, 8), (30, 90, 40, 255)).save(image)
        source = portrait.load_json(ROOT.parent / "atlas-vtt-portrait-forge/assets/examples/roadwarden.portrait.json")
        return portrait.handoff(source, "neris-bust", str(image))

    def test_all_examples_and_starter_are_structurally_valid(self) -> None:
        files = [ROOT / "assets/starter.token.json", *sorted((ROOT / "assets/examples").glob("*.token.json"))]
        self.assertEqual(len(files), 3)
        for path in files:
            with self.subTest(path=path):
                self.assertEqual(token.validate(token.load_json(path))[0], [])

    def test_starter_stays_incomplete(self) -> None:
        source = token.load_json(ROOT / "assets/starter.token.json")
        brief = token.compile_source(source)["briefs"][0]
        self.assertFalse(brief["render_ready"])
        self.assertGreater(len(brief["readiness_issues"]), 0)

    def test_private_variants_and_notes_are_filtered(self) -> None:
        self.source["gm_notes"] = ["PRIVATE_MASTER"]
        self.source["subjects"][0]["gm_notes"] = ["PRIVATE_SUBJECT"]
        self.source["assets"][1]["gm_only"] = True
        self.source["assets"][1]["title"] = "PRIVATE_VARIANT"
        self.source["references"] = [self.reference("unused-private", gm_only=True, locator="PRIVATE_LOCATOR")]
        public = token.compile_source(self.source)
        encoded = json.dumps(public)
        for secret in ("PRIVATE_MASTER", "PRIVATE_SUBJECT", "PRIVATE_VARIANT", "PRIVATE_LOCATOR"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(len(public["briefs"]), 1)
        private = json.dumps(token.compile_source(self.source, "gm"))
        self.assertIn("PRIVATE_VARIANT", private)
        self.assertNotIn("PRIVATE_SUBJECT", private)
        with self.assertRaises(ValueError):
            token.compile_source(self.source, "player", "neris-top-down")

    def test_private_identity_dependencies_fail_instead_of_disappearing(self) -> None:
        self.source["references"] = [self.reference(gm_only=True)]
        self.source["subjects"][0]["identity_reference_ids"] = ["anchor"]
        self.assertTrue(token.validate(self.source)[0])
        with self.assertRaises(ValueError):
            token.compile_source(self.source)

    def test_unknown_subject_and_reference_fail(self) -> None:
        self.source["assets"][0]["subject_id"] = "unknown"
        self.source["assets"][1]["reference_ids"] = ["missing"]
        errors = token.validate(self.source)[0]
        self.assertGreaterEqual(len(errors), 2)

    def test_uninspected_traits_and_approval_fail(self) -> None:
        trait_changes: list[dict[str, Any]] = [{"use": ["invented trait"]}, {"ignore": ["invented ignored trait"]}, {"approved_identity": True}]
        for change in trait_changes:
            self.source["references"] = [self.reference(**change)]
            with self.subTest(change=change):
                self.assertTrue(token.validate(self.source)[0])

    def test_unavailable_reference_never_exports_locator(self) -> None:
        self.source["references"] = [self.reference(locator="UNAVAILABLE_SECRET_LOCATOR", inspection="unavailable")]
        self.source["subjects"][0]["identity_reference_ids"] = ["anchor"]
        compiled = token.compile_source(self.source)
        self.assertNotIn("UNAVAILABLE_SECRET_LOCATOR", json.dumps(compiled))
        self.assertFalse(compiled["briefs"][0]["render_ready"])
        self.assertEqual(compiled["briefs"][0]["unresolved_reference_ids"], ["anchor"])

    def test_duplicate_ids_fail_in_every_collection(self) -> None:
        for collection in ("subjects", "assets", "references"):
            source = copy.deepcopy(self.source)
            if collection == "references":
                source[collection] = [self.reference()]
            source[collection].append(copy.deepcopy(source[collection][0]))
            with self.subTest(collection=collection):
                self.assertTrue(token.validate(source)[0])

    def test_explicit_top_down_base_shadow_and_border_are_supported(self) -> None:
        asset = self.source["assets"][1]
        asset["background"] = {"mode": "solid", "description": "Requested sandstone disc and soft shadow"}
        asset["border"] = {"mode": "baked", "description": "Requested thin navy perimeter"}
        self.assertEqual(token.validate(self.source)[0], [])
        brief = token.compile_source(self.source, asset_id="neris-top-down")["briefs"][0]
        self.assertIn("sandstone disc", brief["image_instructions"])
        self.assertFalse(brief["atlas_display_hint"]["showRing"])

    def test_framing_dimensions_and_ratio_conflicts_fail(self) -> None:
        for output in ({"width_px": 1024, "height_px": 768, "aspect_ratio": [4, 3]},
                       {"width_px": 1024, "height_px": None, "aspect_ratio": None},
                       {"width_px": 1024, "height_px": 1024, "aspect_ratio": [3, 2]}):
            self.source["assets"][0]["output"].update(output)
            with self.subTest(output=output):
                self.assertTrue(token.validate(self.source)[0])

    def test_top_down_is_overhead(self) -> None:
        self.source["assets"][1]["viewpoint"] = "isometric"
        self.assertTrue(token.validate(self.source)[0])

    def test_narrow_revision_changes_only_requested_field_and_revision(self) -> None:
        result = token.revise(self.source, token.load_json(ROOT / "assets/examples/border-color.change.json"))
        expected = copy.deepcopy(self.source)
        expected["assets"][0]["border"]["description"] = "A plain deep blue circular border with a dark inner edge"
        expected["revision"] = 2
        self.assertEqual(result, expected)
        self.assertEqual(self.source["revision"], 1)

    def test_stale_boolean_and_noop_revisions_fail(self) -> None:
        for revision in (0, 2, True, 1.0):
            change = self.change("/assets/0/title", "Revised title")
            change["expected_revision"] = revision
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                token.revise(self.source, change)
        with self.assertRaises(ValueError):
            token.revise(self.source, self.change("/assets/0/title", self.source["assets"][0]["title"]))

    def test_ancestor_replacement_cannot_bypass_lock(self) -> None:
        replacement = copy.deepcopy(self.source["subjects"][0]["visible_identity"])
        replacement["face_head"] = "Different face"
        with self.assertRaises(ValueError):
            token.revise(self.source, self.change("/subjects/0/visible_identity", replacement))

    def test_exact_lock_override_keeps_other_locks(self) -> None:
        path = "/subjects/0/visible_identity/face_head"
        result = token.revise(self.source, self.change(path, "Requested new face"), [path])
        self.assertEqual(result["subjects"][0]["visible_identity"]["face_head"], "Requested new face")
        with self.assertRaises(ValueError):
            token.revise(self.source, self.change(path, "Requested new face"), ["/subjects/0"])

    def test_existing_ids_order_and_bindings_are_stable(self) -> None:
        changes = [self.change("/subjects/0/subject_id", "other"),
                   self.change("/assets/0/asset_id", "other"),
                   self.change("/assets", list(reversed(self.source["assets"]))),
                   self.change("/assets/0/subject_id", "other")]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                token.revise(self.source, change)

    def test_portrait_provenance_cannot_be_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = token.from_handoff(self.handoff(directory), "token-study", "token-01", "portrait_circle")
            with self.assertRaises(ValueError):
                token.revise(source, self.change("/subjects/0/portrait_origin/source_revision", 2))

    def test_malformed_overlapping_and_missing_revision_paths_fail(self) -> None:
        changes = [self.change("revision", 2), self.change("/assets/03/title", "bad"), self.change("/missing", "bad"), self.change("/revision", 2),
                   {"expected_revision": 1, "changes": [{"path": "/assets/0", "value": self.source["assets"][0]}, {"path": "/assets/0/title", "value": "bad"}]}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                token.revise(self.source, change)

    def test_actual_portrait_export_roundtrips_without_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handoff = self.handoff(directory)
            for kind in ("portrait_circle", "top_down", "creature_cutout"):
                with self.subTest(kind=kind):
                    source = token.from_handoff(handoff, "token-study", "matching-token", kind)
                    self.assertEqual(token.validate(source)[0], [])
                    self.assertEqual(source["subjects"][0]["subject_id"], handoff["subject_id"])
                    self.assertEqual(source["subjects"][0]["visible_identity"], handoff["identity"])
                    self.assertEqual(source["assets"][0]["art_direction"], handoff["art_direction"])
                    self.assertEqual(source["subjects"][0]["portrait_origin"]["source_sha256"], handoff["source_sha256"])

    def test_handoff_rejects_extra_private_or_malformed_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handoff = self.handoff(directory)
            mutations = [{**handoff, "gm_notes": ["PRIVATE"]}, {**handoff, "references": ["bad"]},
                         {**handoff, "source_sha256": "invented"}, {**handoff, "token_status": "created"},
                         {**handoff, "subject_id": "Not Stable"}, {**handoff, "source_revision": True}]
            for mutation in [None, [], *mutations]:
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    token.from_handoff(mutation, "token-study", "token-01", "portrait_circle")

    def test_missing_handoff_image_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handoff = self.handoff(directory)
            Path(handoff["approved_image"]).unlink()
            with self.assertRaises(ValueError):
                token.from_handoff(handoff, "token-study", "token-01", "portrait_circle")

    def test_handoff_never_fabricates_receiving_inspection_or_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            handoff = self.handoff(directory)
            handoff["references"] = [{"reference_id": "old-style", "locator": handoff["approved_image"], "role": "style", "use": ["Prior claimed brushwork"], "ignore": ["Prior claimed background"], "approved_identity": False}]
            source = token.from_handoff(handoff, "token-study", "token-01", "portrait_circle")
            for reference in source["references"]:
                self.assertEqual(reference["inspection"], "uninspected")
                self.assertEqual(reference["use"], [])
                self.assertFalse(reference["approved_identity"])
            brief = token.compile_source(source)["briefs"][0]
            self.assertFalse(brief["render_ready"])
            self.assertEqual(brief["references"], [])
            for reference in source["references"]:
                reference["inspection"] = "inspected"
            self.assertFalse(token.compile_source(source)["briefs"][0]["render_ready"])
            source["references"][0]["approved_identity"] = True
            self.assertTrue(token.compile_source(source)["briefs"][0]["render_ready"])

    def test_actual_alpha_and_bounds_measurement_distinguishes_opaque_images(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.png"
            image = Image.new("RGBA", (10, 8), (0, 0, 0, 0))
            image.putpixel((4, 3), (80, 90, 20, 255))
            image.save(path)
            result = token.inspect_image(str(path))
            self.assertEqual((result["width_px"], result["height_px"]), (10, 8))
            self.assertEqual(result["nontransparent_bounds_px"], [4, 3, 5, 4])
            self.assertEqual(result["fully_transparent_pixel_fraction"], 79 / 80)
            self.assertEqual(result["visual_review"], "not_run")
            for mode in ("RGB", "RGBA"):
                Image.new(mode, (10, 8), (50, 60, 70)).save(path)
                opaque = token.inspect_image(str(path))
                self.assertFalse(opaque["has_transparent_pixels"])
                self.assertEqual(opaque["has_alpha"], mode == "RGBA")
            Image.new("RGBA", (10, 8), (0, 0, 0, 0)).save(path)
            self.assertIsNone(token.inspect_image(str(path))["nontransparent_bounds_px"])
            indexed = Image.new("P", (10, 8), 0)
            indexed.putpalette([0, 0, 0, 90, 80, 50] + [0] * 762)
            indexed.putpixel((4, 3), 1)
            indexed.save(path, transparency=0)
            palette_result = token.inspect_image(str(path))
            self.assertTrue(palette_result["has_alpha"])
            self.assertTrue(palette_result["has_transparent_pixels"])
            self.assertEqual(palette_result["nontransparent_bounds_px"], [4, 3, 5, 4])

    def test_outputs_never_overwrite_source_or_previous_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.json"
            source_path.write_text("original")
            with self.assertRaises(ValueError):
                token.write_output({}, str(source_path), [str(source_path)])
            output_path = Path(directory) / "output.json"
            token.write_output({"value": 1}, str(output_path), [])
            with self.assertRaises(FileExistsError):
                token.write_output({"value": 2}, str(output_path), [])
            self.assertEqual(source_path.read_text(), "original")
            self.assertEqual(json.loads(output_path.read_text()), {"value": 1})

    def test_duplicate_keys_nonfinite_and_fractional_revision_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for content in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
                path.write_text(content)
                with self.subTest(content=content), self.assertRaises(ValueError):
                    token.load_json(path)
        self.source["revision"] = 1.0
        self.assertTrue(token.validate(self.source)[0])

    def test_cli_text_and_revision_roundtrips_and_bad_handoff_fail_loudly(self) -> None:
        script = str(ROOT / "scripts/token_spec.py")
        source = str(ROOT / "assets/examples/roadwarden-pair.token.json")
        commands = (["compile", source, "--text"], ["compile", source, "--asset", "neris-circle", "--text"])
        results = [subprocess.run([sys.executable, script, *args], capture_output=True, text=True, check=False) for args in commands]
        self.assertEqual(results[0].returncode, 1)
        self.assertEqual(results[1].returncode, 0, results[1].stderr)
        self.assertIn("portrait_circle", results[1].stdout)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "v2.json"
            result = subprocess.run([sys.executable, script, "revise", source, str(ROOT / "assets/examples/border-color.change.json"), "-o", str(path)], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(token.load_json(path)["revision"], 2)
            malformed = Path(directory) / "invalid-handoff.json"
            malformed.write_text("[]")
            result = subprocess.run([sys.executable, script, "from-handoff", str(malformed), "--spec-id", "study", "--asset-id", "token-01"], capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
