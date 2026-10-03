"""Focused behavioral checks for disclosure, identity continuity, and revisions."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MODULE = importlib.util.spec_from_file_location("heraldry_spec", ROOT / "scripts/heraldry_spec.py")
assert MODULE and MODULE.loader
forge = importlib.util.module_from_spec(MODULE)
MODULE.loader.exec_module(forge)


def reference(ref_id: str = "reviewed-emblem", **overrides: Any) -> dict[str, Any]:
    result = {"reference_id": ref_id, "locator": "/example-only/not-a-real-render.png", "role": "emblem",
              "inspection": "inspected", "approval": "not_requested", "use": ["Keep the three beacon rays"],
              "ignore": [], "gm_only": False, "gm_notes": "PRIVATE_REFERENCE_NOTE"}
    result.update(overrides)
    return result


def change(path: str, value: Any) -> dict[str, Any]:
    return {"expected_revision": 1, "changes": [{"path": path, "value": value}]}


class HeraldryBehavior(unittest.TestCase):
    def setUp(self) -> None:
        self.single = forge.load_json(ROOT / "assets/examples/lantern-watch.heraldry.json")
        self.collection = forge.load_json(ROOT / "assets/examples/harbor-covenant.heraldry.json")

    def test_examples_and_sparse_starter_are_valid(self) -> None:
        for path in (ROOT / "assets").rglob("*.heraldry.json"):
            self.assertEqual(forge.validate(forge.load_json(path))[0], [], str(path))
        starter = forge.load_json(ROOT / "assets/starter.heraldry.json")
        self.assertFalse(forge.compile_source(starter)["briefs"][0]["render_ready"])

    def test_anchor_first_then_same_emblem_for_every_carrier(self) -> None:
        initial = forge.compile_source(self.collection)["briefs"]
        self.assertEqual([b["render_ready"] for b in initial], [True, False, False])
        self.assertEqual(initial[1]["dependency_asset_id"], "covenant-emblem")
        self.collection["references"].append(reference())
        self.collection["factions"][0]["emblem_reference_id"] = "reviewed-emblem"
        updated = forge.compile_source(self.collection)["briefs"]
        self.assertTrue(all(b["render_ready"] for b in updated))
        self.assertEqual({b["references"][0]["reference_id"] for b in updated}, {"reviewed-emblem"})
        self.assertEqual(updated[1]["identity"], updated[2]["identity"])
        self.assertEqual(updated[1]["references"][0]["approval"], "not_requested")

    def test_set_cannot_skip_consistency_anchor(self) -> None:
        self.collection["factions"][0]["consistency_anchor_asset_id"] = None
        self.assertTrue(all(not b["render_ready"] for b in forge.compile_source(self.collection)["briefs"]))

    def test_text_export_requires_ready_brief_without_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            output = Path(directory) / "flag.prompt.txt"
            source.write_text(json.dumps(self.collection), encoding="utf-8")
            original = source.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                status = forge.main(["compile", str(source), "--asset", "covenant-flag", "--text", "-o", str(output)])
            self.assertEqual(status, 1)
            self.assertIn("render-ready brief", errors.getvalue())
            self.assertFalse(output.exists())
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(forge.main(["compile", str(source), "--asset", "covenant-emblem", "--text", "-o", str(output)]), 0)
            self.assertTrue(output.read_text(encoding="utf-8").strip())

    def test_seal_and_flag_set_uses_requested_carrier_as_anchor(self) -> None:
        self.collection["assets"] = self.collection["assets"][1:]
        self.collection["locks"] = ["/factions/0/identity"]
        self.collection["factions"][0]["consistency_anchor_asset_id"] = "covenant-seal"
        self.assertEqual(forge.validate(self.collection)[0], [])
        briefs = forge.compile_source(self.collection)["briefs"]
        self.assertEqual([b["render_ready"] for b in briefs], [True, False])
        self.assertEqual(briefs[1]["dependency_asset_id"], "covenant-seal")
        self.assertEqual(len(briefs), 2)
        self.collection["references"].append(reference())
        self.collection["factions"][0]["emblem_reference_id"] = "reviewed-emblem"
        updated = forge.compile_source(self.collection)["briefs"]
        self.assertTrue(all(b["render_ready"] for b in updated))
        self.assertEqual(updated[1]["identity"]["palette"], self.collection["factions"][0]["identity"]["palette"])

    def test_monochrome_seal_preserves_shared_identity(self) -> None:
        briefs = forge.compile_source(self.collection)["briefs"]
        self.assertEqual(briefs[0]["identity"], briefs[1]["identity"])
        self.assertIn("monochrome", briefs[1]["carrier"]["material"])

    def test_player_filter_excludes_private_assets_refs_and_all_notes(self) -> None:
        self.single["gm_notes"] = "PRIVATE_MASTER_NOTE"
        self.single["factions"][0]["gm_notes"] = "PRIVATE_FACTION_NOTE"
        self.single["assets"][0]["gm_notes"] = "PRIVATE_ASSET_NOTE"
        secret = copy.deepcopy(self.single["assets"][0])
        secret.update({"asset_id": "private-variant", "gm_only": True, "title": "SECRET_ASSET_TITLE", "reference_ids": ["hidden-mark"]})
        self.single["assets"].append(secret)
        self.single["references"] += [reference("hidden-mark", gm_only=True, locator="SECRET_LOCATOR", use=["SECRET_MOTIF"]), reference("unused-ref", locator="UNUSED_LOCATOR")]
        public_brief = forge.compile_source(self.single)
        self.assertTrue(public_brief["briefs"][0]["render_ready"])
        player = json.dumps(public_brief)
        for marker in ("PRIVATE_", "SECRET_", "UNUSED_LOCATOR", "hidden-mark", "unused-ref"):
            self.assertNotIn(marker, player)
        gm = json.dumps(forge.compile_source(self.single, "gm"))
        self.assertIn("SECRET_ASSET_TITLE", gm)
        self.assertNotIn("PRIVATE_", gm)

    def test_private_faction_governs_assets_and_selection(self) -> None:
        self.single["factions"][0]["gm_only"] = True
        with self.assertRaisesRegex(ValueError, "No selected"):
            forge.compile_source(self.single, "player", "watch-emblem")
        self.assertEqual(len(forge.compile_source(self.single, "gm")["briefs"]), 1)

    def test_public_reference_cannot_be_private(self) -> None:
        self.single["references"].append(reference(gm_only=True))
        self.single["factions"][0]["reference_ids"] = ["reviewed-emblem"]
        self.assertTrue(any("public consumer" in e for e in forge.validate(self.single)[0]))

    def test_uninspected_reference_omits_locator_and_directives(self) -> None:
        self.single["references"].append(reference("unknown-style", role="style", locator="UNINSPECTED_LOCATOR", inspection="unavailable", use=[]))
        self.single["assets"][0]["reference_ids"] = ["unknown-style"]
        compiled = forge.compile_source(self.single)
        self.assertFalse(compiled["briefs"][0]["render_ready"])
        self.assertEqual(compiled["briefs"][0]["unresolved_reference_ids"], ["unknown-style"])
        self.assertNotIn("UNINSPECTED_LOCATOR", json.dumps(compiled))
        self.single["references"][0]["use"] = ["invented visual observation"]
        self.assertTrue(forge.validate(self.single)[0])
        self.single["references"][0].update({"use": [], "approval": "user_approved"})
        self.assertTrue(forge.validate(self.single)[0])

    def test_canonical_emblem_requires_inspected_role_and_not_rejected(self) -> None:
        self.single["references"].append(reference(role="style"))
        self.single["factions"][0]["emblem_reference_id"] = "reviewed-emblem"
        self.assertTrue(forge.validate(self.single)[0])
        self.single["references"][0].update({"role": "emblem", "approval": "rejected"})
        self.assertTrue(forge.validate(self.single)[0])

    def test_edit_needs_actual_declared_target_and_inspection(self) -> None:
        asset = self.single["assets"][0]
        asset["intent"] = "edit"
        self.assertTrue(forge.validate(self.single)[0])
        self.single["references"].append(reference("base-image", role="edit_target", inspection="uninspected", use=[]))
        asset["edit_target_ref"] = "base-image"
        self.assertEqual(forge.validate(self.single)[0], [])
        self.assertFalse(forge.compile_source(self.single)["briefs"][0]["render_ready"])
        self.single["references"][0]["inspection"] = "inspected"
        self.assertTrue(forge.compile_source(self.single)["briefs"][0]["render_ready"])
        self.single["references"][0]["role"] = "style"
        self.assertTrue(forge.validate(self.single)[0])

    def test_ids_dependencies_and_output_geometry_fail_loud(self) -> None:
        cases = [("/assets/0/faction_id", "missing"), ("/assets/0/output/width_px", None),
                 ("/assets/0/output/aspect_ratio", [3, 2]), ("/assets/0/output/width_px", True),
                 ("/factions/0/consistency_anchor_asset_id", "missing")]
        for path, value in cases:
            source = copy.deepcopy(self.single)
            tokens = forge.parts(path)
            parent = source
            for token in tokens[:-1]:
                parent = parent[forge.key(parent, token)]
            parent[forge.key(parent, tokens[-1])] = value
            self.assertTrue(forge.validate(source)[0], path)
        self.single["assets"].append(copy.deepcopy(self.single["assets"][0]))
        self.assertTrue(any("Duplicate asset_id" in e for e in forge.validate(self.single)[0]))

    def test_exact_text_composition_preserves_string_outside_image_prompt(self) -> None:
        wording = 'Hold fast: "A&B"\nNorth / South'
        self.collection["assets"][2]["lettering"]["wording"] = wording
        brief = forge.compile_source(self.collection, asset_id="covenant-flag")["briefs"][0]
        self.assertEqual(brief["lettering"]["wording"], wording)
        self.assertNotIn("North / South", brief["image_instructions"])
        self.assertIn("Leave it blank", brief["image_instructions"])
        self.collection["assets"][2]["lettering"]["mode"] = "raster_verify"
        prompt = forge.compile_source(self.collection, asset_id="covenant-flag")["briefs"][0]["image_instructions"]
        self.assertIn(json.dumps(wording), prompt)
        self.collection["assets"][2]["lettering"]["mode"] = "none"
        self.assertTrue(forge.validate(self.collection)[0])

    def test_carrier_revision_changes_only_requested_field_and_revision(self) -> None:
        original = copy.deepcopy(self.collection)
        revised = forge.revise(self.collection, forge.load_json(ROOT / "assets/examples/flag-cloth.change.json"))
        expected = copy.deepcopy(original)
        expected["revision"] = 2
        expected["assets"][2]["carrier"]["material"] = revised["assets"][2]["carrier"]["material"]
        self.assertEqual(revised, expected)
        self.assertEqual(self.collection, original)

    def test_lock_intersections_require_exact_authorized_lock(self) -> None:
        for request in (change("/factions/0/identity/motif", "Different motif"), change("/factions/0/identity", self.collection["factions"][0]["identity"])):
            with self.assertRaisesRegex(ValueError, "Locked field"):
                forge.revise(self.collection, request)
        revised = forge.revise(self.collection, change("/factions/0/identity/motif", "Different motif"), ["/factions/0/identity"])
        self.assertEqual(revised["factions"][0]["identity"]["motif"], "Different motif")
        with self.assertRaisesRegex(ValueError, "exact existing locks"):
            forge.revise(self.collection, change("/assets/2/carrier/material", "Linen"), ["/factions/0/identity/motif"])

    def test_managed_revision_cannot_be_locked(self) -> None:
        self.single["locks"].append("/revision")
        self.assertTrue(any("managed" in e for e in forge.validate(self.single)[0]))
        with self.assertRaises(ValueError):
            forge.revise(self.single, change("/assets/0/carrier/material", "Ink"))

    def test_revision_protects_ids_order_bindings_and_lock_list(self) -> None:
        for request in (change("/spec_id", "other"), change("/revision", 8), change("/assets/0/asset_id", "other"),
                        change("/assets/0/faction_id", "other"), change("/locks", []),
                        change("/assets", list(reversed(self.collection["assets"])))):
            with self.assertRaises(ValueError):
                forge.revise(self.collection, request)

    def test_stale_overlap_bad_pointer_and_unknown_changes_fail(self) -> None:
        request = change("/assets/0/carrier/material", "Ink")
        request["expected_revision"] = 2
        with self.assertRaisesRegex(ValueError, "Stale"):
            forge.revise(self.single, request)
        for bad_path in ("", "/assets/01/title", "/assets/0/no-field", "/assets/0/~2"):
            with self.assertRaises(ValueError):
                forge.revise(self.single, change(bad_path, "bad"))
        request = {"expected_revision": 1, "changes": [{"path": "/assets/0/carrier", "value": self.single["assets"][0]["carrier"]}, {"path": "/assets/0/carrier/material", "value": "Ink"}]}
        with self.assertRaisesRegex(ValueError, "overlapping"):
            forge.revise(self.single, request)

    def test_duplicate_keys_nonfinite_values_and_existing_outputs_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for raw in ('{"value":1,"value":2}', '{"value":NaN}'):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    forge.load_json(path)
            path.write_text("preserve me")
            with self.assertRaises(FileExistsError):
                forge.write_output({"replacement": True}, str(path))
            self.assertEqual(path.read_text(), "preserve me")

    def test_image_metadata_measures_alpha_without_claiming_visual_review(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.png"
            img = Image.new("RGBA", (3, 1), (10, 20, 30, 255))
            img.putpixel((0, 0), (10, 20, 30, 0))
            img.putpixel((1, 0), (10, 20, 30, 128))
            img.save(path)
            result = forge.inspect_image(path)
            self.assertEqual((result["width_px"], result["height_px"]), (3, 1))
            self.assertEqual((result["transparent_pixels"], result["partial_alpha_pixels"]), (1, 1))
            self.assertEqual(result["visual_review"], "not_run")
            Image.new("RGB", (2, 2), "white").save(path)
            result = forge.inspect_image(path)
            self.assertFalse(result["alpha_channel"])
            self.assertEqual(result["transparent_pixels"], 0)


if __name__ == "__main__":
    unittest.main()
