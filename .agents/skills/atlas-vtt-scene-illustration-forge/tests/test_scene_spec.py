"""Focused behavior checks for source filtering, coherent variants, and revisions."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import scene_spec as scene


def example(name: str = "basalt-gate-set.scene.json") -> dict:
    return scene.read_json(ROOT / "assets/examples" / name)


def reference(ref_id: str, inspection: str = "inspected", role: str = "style", private: bool = False) -> dict:
    return {"reference_id": ref_id, "locator": f"/unavailable-test-data/{ref_id}.png", "role": role,
            "inspection": inspection, "use": ["Broad watercolor washes"] if inspection == "inspected" else [],
            "ignore": [], "gm_only": private}


class SceneSourceTests(unittest.TestCase):
    def test_examples_and_incomplete_starter(self) -> None:
        for name in ("ferry-hall.scene.json", "basalt-gate-set.scene.json"):
            source = example(name)
            self.assertEqual(scene.validate(source), [])
            self.assertTrue(all(brief["render_ready"] for brief in scene.compile_source(source)["briefs"]))
        starter = scene.read_json(ROOT / "assets/starter.scene.json")
        self.assertEqual(scene.validate(starter), [])
        self.assertFalse(scene.compile_source(starter)["briefs"][0]["render_ready"])

    def test_schema_rejects_unrecognized_visual_fields_and_bad_types(self) -> None:
        source = example()
        source["assets"][0]["gm_notes"] = ["SECRET"]
        self.assertTrue(scene.validate(source))
        source = example()
        source["schema_version"] = 1.0
        self.assertTrue(scene.validate(source))
        source = example()
        source["revision"] = True
        self.assertTrue(scene.validate(source))

    def test_unique_ids_and_known_locations(self) -> None:
        for collection, id_name in scene.COLLECTIONS[:2]:
            source = example()
            source[collection].append(copy.deepcopy(source[collection][0]))
            self.assertTrue(scene.validate(source), id_name)
        source = example()
        source["references"] = [reference("same"), reference("same")]
        self.assertTrue(scene.validate(source))
        source = example()
        source["assets"][0]["location_id"] = "missing"
        self.assertTrue(scene.validate(source))

    def test_reference_bindings_roles_and_privacy(self) -> None:
        source = example()
        source["assets"][0]["reference_ids"] = ["missing"]
        self.assertTrue(scene.validate(source))
        source["references"] = [reference("missing", private=True)]
        self.assertTrue(scene.validate(source))
        source["assets"][0]["gm_only"] = True
        self.assertEqual(scene.validate(source), [])
        source = example()
        source["references"] = [reference("wrong-role")]
        source["locations"][0]["identity_reference_ids"] = ["wrong-role"]
        self.assertTrue(scene.validate(source))

    def test_uninspected_references_cannot_assert_traits(self) -> None:
        source = example()
        ref = reference("unseen", "unavailable")
        ref["use"] = ["Invented tower shape"]
        source["references"] = [ref]
        self.assertTrue(scene.validate(source))
        ref["use"] = []
        ref["ignore"] = ["Invented foreground"]
        self.assertTrue(scene.validate(source))

    def test_unavailable_reference_blocks_readiness_and_hides_locator(self) -> None:
        source = example()
        source["references"] = [reference("needed", "unavailable")]
        source["assets"][0]["reference_ids"] = ["needed"]
        output = scene.compile_source(source, asset_id="gate-dawn")
        brief = output["briefs"][0]
        self.assertFalse(brief["render_ready"])
        self.assertEqual(brief["unresolved_reference_ids"], ["needed"])
        self.assertEqual(brief["references"], [])
        self.assertNotIn("/unavailable-test-data", scene.canonical(output))

    def test_identity_references_are_used_and_unused_records_are_excluded(self) -> None:
        source = example()
        source["references"] = [reference("gate-id", role="location_identity"), reference("used-style"),
                                reference("unused-private", private=True)]
        source["locations"][0]["identity_reference_ids"] = ["gate-id"]
        source["assets"][0]["reference_ids"] = ["used-style", "gate-id"]
        output = scene.compile_source(source, asset_id="gate-dawn")
        self.assertEqual([ref["reference_id"] for ref in output["briefs"][0]["references"]],
                         ["gate-id", "used-style"])
        self.assertNotIn("unused-private", scene.canonical(output))

    def test_private_assets_locations_and_notes_are_filtered(self) -> None:
        source = example()
        source["locations"][0]["gm_notes"] = ["PRIVATE-LOCATION-NOTE"]
        source["gm_notes"] = ["PRIVATE-MASTER-NOTE"]
        source["references"] = [reference("private-base", role="composition", private=True)]
        source["assets"][2]["reference_ids"] = ["private-base"]
        player = scene.compile_source(source)
        self.assertEqual([brief["asset_id"] for brief in player["briefs"]], ["gate-dawn", "gate-evening"])
        public_text = scene.canonical(player)
        for private in ("gate-private-siege", "private-base", "PRIVATE-LOCATION-NOTE", "PRIVATE-MASTER-NOTE", "gm_notes"):
            self.assertNotIn(private, public_text)
        gm = scene.compile_source(source, "gm")
        self.assertEqual(len(gm["briefs"]), 3)
        self.assertNotIn("PRIVATE-LOCATION-NOTE", scene.canonical(gm))
        source["locations"][0]["gm_only"] = True
        self.assertEqual(scene.compile_source(source)["briefs"], [])

    def test_asset_selection_and_invalid_audiences_fail(self) -> None:
        for asset_id in ("gate-private-siege", "unknown"):
            with self.assertRaises(ValueError):
                scene.compile_source(example(), asset_id=asset_id)
        with self.assertRaises(ValueError):
            scene.compile_source(example(), "public-ish")

    def test_edit_target_is_required_inspected_and_typed(self) -> None:
        source = example()
        asset = source["assets"][0]
        asset["intent"] = "edit"
        self.assertTrue(scene.validate(source))
        source["references"] = [reference("base", "uninspected", "edit_target")]
        asset["edit_target_ref"] = "base"
        asset["edit_scope"] = {"change": "Warm only the twilight light", "preserve": ["Architecture and camera"]}
        self.assertEqual(scene.validate(source), [])
        self.assertFalse(scene.compile_source(source, asset_id="gate-dawn")["briefs"][0]["render_ready"])
        source["references"][0]["inspection"] = "inspected"
        self.assertTrue(scene.compile_source(source, asset_id="gate-dawn")["briefs"][0]["render_ready"])
        source["references"][0]["role"] = "style"
        self.assertTrue(scene.validate(source))
        source["references"][0]["role"] = "edit_target"
        asset["intent"] = "generate"
        self.assertTrue(scene.validate(source))

    def test_dimensions_are_paired_and_ratio_matches(self) -> None:
        source = example()
        source["assets"][0]["output"]["height_px"] = None
        self.assertTrue(scene.validate(source))
        source["assets"][0]["output"]["height_px"] = 1000
        self.assertTrue(scene.validate(source))
        source["assets"][0]["output"] = {"width_px": None, "height_px": None, "aspect_ratio": [3, 4]}
        self.assertEqual(scene.validate(source), [])

    def test_explicit_viewpoint_style_background_and_text_are_preserved(self) -> None:
        source = example("ferry-hall.scene.json")
        asset = source["assets"][0]
        asset["composition"]["viewpoint"] = "Overhead schematic perspective requested by the user"
        asset["art_direction"]["medium"] = "Flat monochrome woodcut"
        asset["background"] = {"mode": "transparent", "description": "Vignette with clear exterior margins"}
        asset["output"] = {"width_px": 900, "height_px": 1200, "aspect_ratio": [3, 4]}
        asset["lettering"] = ["REED FERRY"]
        brief = scene.compile_source(source)["briefs"][0]
        for name in ("composition", "art_direction", "background", "output", "lettering"):
            self.assertEqual(brief[name], asset[name])
        self.assertEqual(brief["location"], {name: source["locations"][0][name]
                                           for name in ("location_id", "name", "description", "architecture", "landmarks")})

    def test_dramatic_readiness_needs_visible_moment(self) -> None:
        source = example()
        source["assets"][2]["moment"] = ""
        self.assertFalse(scene.compile_source(source, "gm", "gate-private-siege")["briefs"][0]["render_ready"])

    def test_narrow_revision_preserves_other_variants_and_source(self) -> None:
        source = example()
        before = scene.canonical(source)
        change = scene.read_json(ROOT / "assets/examples/evening-light.change.json")
        result = scene.revise(source, change)
        self.assertEqual(result["revision"], 2)
        self.assertEqual(scene.canonical(source), before)
        self.assertEqual(result["assets"][0], source["assets"][0])
        self.assertEqual(result["assets"][2], source["assets"][2])
        self.assertEqual(result["locations"], source["locations"])
        expected_asset = copy.deepcopy(source["assets"][1])
        expected_asset["atmosphere"]["lighting"] = change["changes"][0]["value"]
        self.assertEqual(result["assets"][1], expected_asset)

    def test_stale_empty_or_malformed_change_is_rejected(self) -> None:
        source = example()
        for change in ({"expected_revision": 0, "changes": []}, {"expected_revision": True, "changes": []},
                       {"expected_revision": 1, "changes": []}, {"expected_revision": 1, "changes": [], "approved": True},
                       {"expected_revision": 1, "changes": [{"path": "/assets/0/title"}]},
                       {"expected_revision": 1, "changes": [{"path": None, "value": "Invalid"}]}):
            with self.assertRaises((ValueError, TypeError)):
                scene.revise(source, change)

    def test_ancestor_replacement_honors_each_descendant_lock(self) -> None:
        source = example()
        location = copy.deepcopy(source["locations"][0])
        location["architecture"] = ["Requested new towers"]
        location["landmarks"] = ["An unrelated new lake"]
        change = {"expected_revision": 1, "changes": [{"path": "/locations/0", "value": location}]}
        with self.assertRaises(ValueError):
            scene.revise(source, change)
        with self.assertRaises(ValueError):
            scene.revise(source, change, ("/locations/0/architecture",))
        location["landmarks"] = source["locations"][0]["landmarks"]
        result = scene.revise(source, change, ("/locations/0/architecture",))
        self.assertEqual(result["locations"][0]["architecture"], ["Requested new towers"])
        with self.assertRaises(ValueError):
            scene.revise(source, change, ("/locations/0",))

    def test_existing_ids_order_and_bindings_cannot_change(self) -> None:
        source = example()
        for path, value in (("/assets/0/asset_id", "other"), ("/assets/0/location_id", "other"),
                            ("/assets", list(reversed(source["assets"]))), ("/assets", source["assets"][:1]),
                            ("/locations/0/location_id", "other")):
            with self.assertRaises(ValueError):
                scene.revise(source, {"expected_revision": 1, "changes": [{"path": path, "value": value}]})

    def test_append_new_entries_preserves_existing_identity(self) -> None:
        source = example()
        new_location = copy.deepcopy(source["locations"][0])
        new_location["location_id"] = "second-gate"
        new_asset = copy.deepcopy(source["assets"][0])
        new_asset.update(asset_id="second-reveal", location_id="second-gate", reference_ids=["second-style"])
        change = {"expected_revision": 1, "changes": [
            {"path": "/locations", "value": source["locations"] + [new_location]},
            {"path": "/assets", "value": source["assets"] + [new_asset]},
            {"path": "/references", "value": [reference("second-style")]}]}
        result = scene.revise(source, change)
        self.assertEqual(result["assets"][:3], source["assets"])
        self.assertEqual(len(scene.compile_source(result)["briefs"]), 3)

    def test_managed_overlapping_missing_and_invalid_pointer_changes_fail(self) -> None:
        source = example()
        for path in ("/revision", "/locks", "/spec_id", "/schema_version", "/assets/01/title",
                     "/assets/0/missing", "/assets/0/title~2", ""):
            with self.assertRaises(ValueError):
                scene.revise(source, {"expected_revision": 1, "changes": [{"path": path, "value": 1}]})
        with self.assertRaises(ValueError):
            scene.revise(source, {"expected_revision": 1, "changes": [
                {"path": "/assets/0/atmosphere", "value": source["assets"][0]["atmosphere"]},
                {"path": "/assets/0/atmosphere/mood", "value": "Calm"}]})
        source["locks"].append("/revision")
        self.assertTrue(scene.validate(source))
        source["locks"] = ["/missing"]
        self.assertTrue(scene.validate(source))

    def test_json_reader_rejects_duplicate_and_nonfinite_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            for content in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    scene.read_json(path)


class SceneCliTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "scripts/scene_spec.py"), *args],
                              capture_output=True, text=True, check=False)

    def test_cli_roundtrip_and_exclusive_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "revised.json"
            result = self.run_cli("revise", str(ROOT / "assets/examples/basalt-gate-set.scene.json"),
                                  str(ROOT / "assets/examples/evening-light.change.json"), "-o", str(destination))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(scene.read_json(destination)["revision"], 2)
            check = self.run_cli("validate", str(destination))
            self.assertEqual(check.returncode, 0, check.stderr)
            saved = destination.read_bytes()
            repeated = self.run_cli("compile", str(destination), "-o", str(destination))
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(destination.read_bytes(), saved)
            out = Path(directory) / "player.json"
            built = self.run_cli("compile", str(destination), "-o", str(out))
            self.assertEqual(built.returncode, 0, built.stderr)
            saved = out.read_bytes()
            repeated = self.run_cli("compile", str(destination), "-o", str(out))
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(out.read_bytes(), saved)

    def test_text_requires_one_ready_asset_and_preserves_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            path.write_text(json.dumps(example()))
            original = path.read_bytes()
            self.assertNotEqual(self.run_cli("compile", str(path), "--text").returncode, 0)
            result = self.run_cli("compile", str(path), "--asset", "gate-evening", "--text")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("gate-private-siege", result.stdout)
            incomplete = self.run_cli("compile", str(ROOT / "assets/starter.scene.json"), "--text")
            self.assertNotEqual(incomplete.returncode, 0)
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
