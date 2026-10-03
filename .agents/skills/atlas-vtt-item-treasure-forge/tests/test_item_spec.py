"""Focused behavior checks; no image generation, inspection, or Atlas execution."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "item_spec", ROOT / "scripts/item_spec.py"
)
assert SPEC is not None and SPEC.loader is not None
helper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(helper)


def source(name="tideglass-saber.item.json"):
    return json.loads((ROOT / "assets/examples" / name).read_text())


def change(path, value, revision=1):
    return {"expected_revision": revision, "changes": [{"path": path, "value": value}]}


def reference(identifier="base", inspection="inspected", private=False):
    return {
        "reference_id": identifier,
        "locator": "/fixture/not-an-inspected-image.png",
        "role": "edit_target",
        "inspection": inspection,
        "use": [],
        "ignore": [],
        "gm_only": private,
    }


class ItemSpecTests(unittest.TestCase):
    def test_examples_validate_and_starter_stays_incomplete(self):
        for example in (ROOT / "assets/examples").glob("*.item.json"):
            helper.validate(json.loads(example.read_text()))
        starter = json.loads((ROOT / "assets/starter.item.json").read_text())
        brief = helper.compile_spec(starter)["briefs"][0]
        self.assertFalse(brief["render_ready"])
        self.assertTrue(brief["readiness_issues"])

    def test_saber_has_one_ready_item_and_no_render_claim(self):
        result = helper.compile_spec(source())
        self.assertEqual(len(result["briefs"]), 1)
        self.assertEqual(
            [i["item_id"] for i in result["briefs"][0]["items"]], ["tideglass-saber"]
        )
        self.assertTrue(result["briefs"][0]["render_ready"])
        self.assertEqual(result["image"], "not_generated")
        self.assertEqual(result["atlas"], "not_imported")

    def test_set_preserves_separate_assets_and_shared_style(self):
        result = helper.compile_spec(source("wayfarer-cache.item.json"))
        self.assertEqual(len(result["briefs"]), 3)
        self.assertEqual(len({b["asset_id"] for b in result["briefs"]}), 3)
        self.assertTrue(all(len(b["items"]) == 1 for b in result["briefs"]))
        self.assertTrue(
            all(
                b["art_direction"] == result["briefs"][0]["art_direction"]
                for b in result["briefs"]
            )
        )

    def test_group_display_preserves_each_requested_item(self):
        value = source("wayfarer-cache.item.json")
        value["assets"] = value["assets"][:1]
        value["assets"][0]["item_ids"] = [i["item_id"] for i in value["items"]]
        value["assets"][0]["presentation"]["arrangement"] = (
            "Three separated objects in a row"
        )
        brief = helper.compile_spec(value)["briefs"][0]
        self.assertEqual(len(brief["items"]), 3)
        self.assertTrue(brief["render_ready"])

    def test_private_art_and_notes_are_filtered(self):
        value = source()
        private_item = deepcopy(value["items"][0])
        private_item.update(
            {"item_id": "secret-relic", "name": "SECRET RELIC", "gm_only": True}
        )
        private_asset = deepcopy(value["assets"][0])
        private_asset.update(
            {"asset_id": "secret-image", "item_ids": ["secret-relic"], "gm_only": True}
        )
        value["items"].append(private_item)
        value["assets"].append(private_asset)
        value["references"].append(reference("secret-reference", private=True))
        player = helper.compile_spec(value)
        serialized = json.dumps(player)
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("PRIVATE EXAMPLE", serialized)
        self.assertNotIn("secret-reference", serialized)
        gm = helper.compile_spec(value, "gm")
        self.assertEqual(len(gm["briefs"]), 2)
        self.assertNotIn("PRIVATE EXAMPLE", json.dumps(gm))
        with self.assertRaises(helper.SpecError):
            helper.compile_spec(value, "player", "secret-image")

    def test_public_asset_cannot_depend_on_private_reference_or_item(self):
        value = source()
        value["references"] = [reference(private=True)]
        value["assets"][0]["reference_ids"] = ["base"]
        with self.assertRaises(helper.SpecError):
            helper.validate(value)
        value = source()
        value["items"][0]["gm_only"] = True
        with self.assertRaises(helper.SpecError):
            helper.validate(value)

    def test_uninspected_reference_does_not_export_locator(self):
        value = source()
        value["references"] = [reference(inspection="unavailable")]
        value["assets"][0]["reference_ids"] = ["base"]
        brief = helper.compile_spec(value)["briefs"][0]
        self.assertFalse(brief["render_ready"])
        self.assertEqual(brief["unresolved_reference_ids"], ["base"])
        self.assertEqual(brief["references"], [])
        self.assertNotIn("/fixture/", json.dumps(brief))

    def test_uninspected_reference_cannot_claim_observations(self):
        value = source()
        value["references"] = [reference(inspection="uninspected")]
        value["references"][0]["use"] = ["An invented blue hilt"]
        with self.assertRaises(helper.SpecError):
            helper.validate(value)

    def test_edit_requires_role_matched_inspected_target(self):
        value = source()
        value["assets"][0]["intent"] = "edit"
        with self.assertRaises(helper.SpecError):
            helper.validate(value)
        value["assets"][0]["edit_target_ref"] = "base"
        value["references"] = [reference(inspection="uninspected")]
        self.assertFalse(helper.compile_spec(value)["briefs"][0]["render_ready"])
        value["references"][0]["inspection"] = "inspected"
        brief = helper.compile_spec(value)["briefs"][0]
        self.assertTrue(brief["render_ready"])
        self.assertEqual(brief["references"][0]["reference_id"], "base")
        value["references"][0]["role"] = "style"
        with self.assertRaises(helper.SpecError):
            helper.validate(value)

    def test_exact_lettering_preserved_outside_generation_prompt(self):
        value = source()
        text = "Élan & Tide <III>\nKeep “this” exact."
        value["items"][0]["inscriptions"][0]["text"] = text
        brief = helper.compile_spec(value)["briefs"][0]
        self.assertEqual(brief["lettering_plan"][0]["text"], text)
        self.assertEqual(brief["lettering_plan"][0]["status"], "pending")
        self.assertNotIn(text, brief["image_prompt"])
        self.assertNotIn("Keep", brief["image_prompt"])
        value["items"][0]["inscriptions"][0]["handling"] = "render_and_verify"
        brief = helper.compile_spec(value)["briefs"][0]
        self.assertIn(json.dumps(text, ensure_ascii=False), brief["image_prompt"])
        self.assertEqual(brief["lettering_plan"][0]["status"], "pending")

    def test_duplicate_identity_ids_and_unknown_links_rejected(self):
        for group in ["items", "assets", "references"]:
            value = source()
            if group == "references":
                value[group] = [reference()]
            value[group].append(deepcopy(value[group][0]))
            with self.subTest(group=group), self.assertRaises(helper.SpecError):
                helper.validate(value)
        value = source()
        value["items"][0]["inscriptions"].append(
            deepcopy(value["items"][0]["inscriptions"][0])
        )
        with self.assertRaises(helper.SpecError):
            helper.validate(value)
        value = source()
        value["assets"][0]["item_ids"] = ["missing"]
        with self.assertRaises(helper.SpecError):
            helper.validate(value)

    def test_output_dimensions_are_requests_with_consistent_ratio(self):
        value = source()
        output = value["assets"][0]["presentation"]["output"]
        output.update({"width_px": 900, "height_px": None})
        with self.assertRaises(helper.SpecError):
            helper.validate(value)
        output["height_px"] = 600
        helper.validate(value)
        brief = helper.compile_spec(value)["briefs"][0]
        self.assertEqual(brief["presentation"]["output"]["width_px"], 900)
        self.assertNotIn("actual_width_px", brief)
        output["height_px"] = 900
        with self.assertRaises(helper.SpecError):
            helper.validate(value)

    def test_narrow_revision_preserves_unspecified_values(self):
        value = source()
        patch = json.loads(
            (ROOT / "assets/examples/grip-color.change.json").read_text()
        )
        result = helper.revise(value, patch)
        expected = deepcopy(value)
        expected["items"][0]["appearance"]["colors"][2] = "Deep blue grip"
        expected["art_direction"]["palette"][4] = "Deep blue"
        expected["revision"] = 2
        self.assertEqual(result, expected)
        self.assertEqual(value, source())

    def test_ancestor_lock_change_requires_exact_authorization(self):
        value = source()
        appearance = deepcopy(value["items"][0]["appearance"])
        appearance["shape"] = "A deliberately changed blade silhouette"
        patch = change("/items/0/appearance", appearance)
        with self.assertRaises(helper.SpecError):
            helper.revise(value, patch)
        result = helper.revise(value, patch, ["/items/0/appearance/shape"])
        self.assertEqual(result["items"][0]["appearance"]["shape"], appearance["shape"])
        appearance["distinctive_marks"] = ["A new mark"]
        with self.assertRaises(helper.SpecError):
            helper.revise(
                value,
                change("/items/0/appearance", appearance),
                ["/items/0/appearance/shape"],
            )
        with self.assertRaises(helper.SpecError):
            helper.revise(value, patch, ["/items/0/appearance"])

    def test_stale_and_managed_metadata_changes_rejected(self):
        value = source()
        with self.assertRaises(helper.SpecError):
            helper.revise(value, change("/art_direction/mood", "Quiet", revision=2))
        for path, new_value in [
            ("/revision", 4),
            ("/spec_id", "other"),
            ("/locks", []),
            ("/schema_version", 2),
        ]:
            with self.subTest(path=path), self.assertRaises(helper.SpecError):
                helper.revise(value, change(path, new_value))

    def test_revision_and_managed_metadata_cannot_be_locked(self):
        for path in ["/revision", "/schema_version", "/spec_id", "/locks/0"]:
            value = source()
            value["locks"] = [path]
            with self.subTest(path=path), self.assertRaises(helper.SpecError):
                helper.validate(value)

    def test_narrow_revision_protects_identity_bindings_and_inscriptions(self):
        value = source("wayfarer-cache.item.json")
        for path, new_value in [
            ("/items/0/item_id", "other"),
            ("/items", value["items"][1:]),
            ("/items", list(reversed(value["items"]))),
            ("/assets/0/item_ids", ["sun-cup"]),
        ]:
            with self.subTest(path=path), self.assertRaises(helper.SpecError):
                helper.revise(value, change(path, new_value))
        value = source()
        with self.assertRaises(helper.SpecError):
            helper.revise(
                value,
                change("/items/0/inscriptions/0/inscription_id", "other"),
                ["/items/0/inscriptions"],
            )

    def test_append_set_member_preserves_previous_assets(self):
        value = source("wayfarer-cache.item.json")
        item = deepcopy(value["items"][0])
        item["item_id"] = "vial-02"
        asset = deepcopy(value["assets"][0])
        asset.update({"asset_id": "vial-02-closeup", "item_ids": ["vial-02"]})
        patch = {
            "expected_revision": 1,
            "changes": [
                {"path": "/items", "value": value["items"] + [item]},
                {"path": "/assets", "value": value["assets"] + [asset]},
            ],
        }
        result = helper.revise(value, patch)
        self.assertEqual(result["assets"][:3], value["assets"])
        self.assertEqual(len(helper.compile_spec(result)["briefs"]), 4)
        with self.assertRaises(helper.SpecError):
            helper.revise(result, patch)

    def test_overlapping_unknown_and_malformed_paths_rejected(self):
        value = source()
        patch = {
            "expected_revision": 1,
            "changes": [
                {"path": "/art_direction", "value": value["art_direction"]},
                {"path": "/art_direction/mood", "value": "Bright"},
            ],
        }
        with self.assertRaises(helper.SpecError):
            helper.revise(value, patch)
        for path in [
            "/items/01/name",
            "/items/0/unknown",
            "/items/~3/name",
            "/",
            "items/0/name",
        ]:
            with self.subTest(path=path), self.assertRaises(helper.SpecError):
                helper.revise(value, change(path, "New"))

    def test_cli_roundtrip_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            command = [
                sys.executable,
                str(ROOT / "scripts/item_spec.py"),
                "compile",
                str(ROOT / "assets/examples/tideglass-saber.item.json"),
                "-o",
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = output.read_bytes()
            self.assertEqual(json.loads(original)["source_revision"], 1)
            second = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), original)

    def test_cli_revision_and_text_set_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "revised.json"
            command = [
                sys.executable,
                str(ROOT / "scripts/item_spec.py"),
                "revise",
                str(ROOT / "assets/examples/tideglass-saber.item.json"),
                str(ROOT / "assets/examples/grip-color.change.json"),
                "-o",
                str(output),
            ]
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["revision"], 2)
            command[-1] = command[3]
            result = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(result.returncode, 2)
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/item_spec.py"),
                "compile",
                str(ROOT / "assets/examples/wayfarer-cache.item.json"),
                "--text",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
