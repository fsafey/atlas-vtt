"""Meaningful disclosure, revision, dependency, and raster measurement cases."""

from __future__ import annotations

import copy
import hashlib
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
SCRIPT = ROOT / "scripts/props_spec.py"
module_spec = importlib.util.spec_from_file_location("props_spec", SCRIPT)
assert module_spec and module_spec.loader
props = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(props)


class PropsSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = props.read_json(
            ROOT / "assets/examples/waystation-table.props.json"
        )
        self.terrain = props.read_json(ROOT / "assets/examples/mossbank-set.props.json")

    def test_examples_and_starter_validate(self) -> None:
        for path in [
            ROOT / "assets/starter.props.json",
            *sorted((ROOT / "assets/examples").glob("*.props.json")),
        ]:
            with self.subTest(path=path):
                props.validate(props.read_json(path))

    def test_managed_revision_cannot_be_locked(self) -> None:
        self.table["locks"] = ["/revision"]
        with self.assertRaises(ValueError):
            props.validate(self.table)
        with self.assertRaises(ValueError):
            props.revise(
                self.table,
                {
                    "expected_revision": 1,
                    "changes": [
                        {"path": "/assets/0/description", "value": "A weathered table"}
                    ],
                },
            )
        self.assertEqual(self.table["revision"], 1)

    def test_starter_incomplete_not_render_ready(self) -> None:
        brief = props.compile_spec(props.read_json(ROOT / "assets/starter.props.json"))[
            "briefs"
        ][0]
        self.assertFalse(brief["render_ready"])
        self.assertEqual(
            set(brief["missing_requirements"]),
            {"description", "art_direction.style", "footprint"},
        )

    def test_player_filters_private_variant_and_notes(self) -> None:
        result = props.compile_spec(self.terrain)
        encoded = json.dumps(result)
        self.assertEqual(len(result["briefs"]), 4)
        self.assertNotIn("roof-secret-01", encoded)
        self.assertNotIn("concealed hatch", encoded)
        self.assertNotIn("gm_notes", encoded)
        self.assertEqual(len(props.compile_spec(self.terrain, "gm")["briefs"]), 5)

    def test_unused_and_uninspected_references_filtered(self) -> None:
        reference = {
            "reference_id": "wood-reference",
            "locator": "/private/reference.png",
            "role": "material",
            "inspection": "uninspected",
            "use": ["private directive"],
            "ignore": [],
            "approved": False,
            "gm_only": False,
        }
        self.table["references"] = [reference]
        self.assertNotIn("wood-reference", json.dumps(props.compile_spec(self.table)))
        self.table["assets"][0]["reference_ids"] = ["wood-reference"]
        result = props.compile_spec(self.table)
        encoded = json.dumps(result)
        self.assertIn("wood-reference", encoded)
        self.assertNotIn("/private/reference.png", encoded)
        self.assertNotIn("private directive", encoded)
        self.assertFalse(result["briefs"][0]["render_ready"])
        reference["inspection"] = "inspected"
        self.assertIn(
            "/private/reference.png", json.dumps(props.compile_spec(self.table))
        )

    def test_private_reference_dependency_rejected(self) -> None:
        spec = props.read_json(ROOT / "assets/examples/table-edit.props.json")
        spec["references"][0]["gm_only"] = True
        with self.assertRaisesRegex(ValueError, "private reference"):
            props.compile_spec(spec)

    def test_missing_base_and_unapproved_edit_not_ready(self) -> None:
        spec = props.read_json(ROOT / "assets/examples/table-edit.props.json")
        self.assertFalse(props.compile_spec(spec)["briefs"][0]["render_ready"])
        spec["references"][0].update(inspection="inspected", approved=False)
        self.assertFalse(props.compile_spec(spec)["briefs"][0]["render_ready"])
        spec["references"][0]["approved"] = True
        self.assertTrue(props.compile_spec(spec)["briefs"][0]["render_ready"])

    def test_duplicate_asset_and_reference_ids_rejected(self) -> None:
        self.table["assets"].append(copy.deepcopy(self.table["assets"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate asset_id"):
            props.validate(self.table)
        spec = props.read_json(ROOT / "assets/examples/table-edit.props.json")
        spec["references"].append(copy.deepcopy(spec["references"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate reference_id"):
            props.validate(spec)

    def test_unknown_reference_and_private_selection_rejected(self) -> None:
        self.table["assets"][0]["reference_ids"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "Unknown reference"):
            props.validate(self.table)
        with self.assertRaisesRegex(ValueError, "excluded"):
            props.compile_spec(self.terrain, asset_id="roof-secret-01")

    def test_revision_changes_only_requested_source(self) -> None:
        original = copy.deepcopy(self.terrain)
        change = props.read_json(ROOT / "assets/examples/roof-color.change.json")
        result = props.revise(self.terrain, change)
        expected = copy.deepcopy(original)
        expected["assets"][2]["description"] = change["changes"][0]["value"]
        expected["revision"] = 2
        self.assertEqual(result, expected)
        self.assertEqual(self.terrain, original)

    def test_stale_revision_and_noop_rejected(self) -> None:
        change: dict[str, Any] = {
            "expected_revision": 2,
            "changes": [{"path": "/assets/0/name", "value": "Changed"}],
        }
        with self.assertRaisesRegex(ValueError, "Stale"):
            props.revise(self.table, change)
        change["expected_revision"] = 1
        change["changes"][0]["value"] = self.table["assets"][0]["name"]
        with self.assertRaisesRegex(ValueError, "No-op"):
            props.revise(self.table, change)

    def test_lock_parent_child_and_authorized_override(self) -> None:
        change = {
            "expected_revision": 1,
            "changes": [{"path": "/assets/0/footprint/width", "value": 4}],
        }
        with self.assertRaisesRegex(ValueError, "Locked"):
            props.revise(self.table, change)
        updated = props.revise(self.table, change, ["/assets/0/footprint"])
        self.assertEqual(updated["assets"][0]["footprint"]["width"], 4)
        with self.assertRaisesRegex(ValueError, "exact existing lock"):
            props.revise(self.table, change, ["/assets"])
        self.table["locks"] = ["/assets/0/footprint/width"]
        change["changes"] = [
            {
                "path": "/assets/0/footprint",
                "value": {"width": 4, "length": 6, "unit": "ft"},
            }
        ]
        with self.assertRaisesRegex(ValueError, "Locked"):
            props.revise(self.table, change)

    def test_identity_collection_and_invalid_paths_protected(self) -> None:
        for path, value in [
            ("/assets", []),
            ("/assets/0/object_id", "changed"),
            ("/locks", []),
            ("/assets/00/name", "changed"),
            ("/assets/0/missing", "changed"),
        ]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                props.revise(
                    self.table,
                    {
                        "expected_revision": 1,
                        "changes": [{"path": path, "value": value}],
                    },
                )

    def test_overlapping_changes_rejected(self) -> None:
        change = {
            "expected_revision": 1,
            "changes": [
                {"path": "/art_direction/style", "value": "Changed style"},
                {"path": "/art_direction", "value": self.table["art_direction"]},
            ],
        }
        with self.assertRaisesRegex(ValueError, "overlapping"):
            props.revise(self.table, change)

    def test_geometry_and_shadow_requirements(self) -> None:
        self.table["assets"][0]["shadow"].update(mode="cast", direction_deg=None)
        with self.assertRaisesRegex(ValueError, "direction"):
            props.validate(self.table)
        self.table["assets"][0]["shadow"].update(mode="none", reach_fraction=0.02)
        with self.assertRaisesRegex(ValueError, "zero reach"):
            props.validate(self.table)
        self.table["assets"][0]["shadow"]["reach_fraction"] = 0
        self.table["assets"][0]["output"]["width_px"] = None
        with self.assertRaisesRegex(ValueError, "both requested dimensions"):
            props.validate(self.table)

    def test_actual_alpha_and_margin_measurements(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cutout.png"
            image = Image.new("RGBA", (10, 8), (0, 0, 0, 0))
            for x in range(2, 8):
                for y in range(1, 7):
                    image.putpixel((x, y), (100, 100, 100, 255))
            image.putpixel((2, 1), (100, 100, 100, 128))
            image.save(path)
            result = props.inspect_image(path)
            self.assertEqual((result["width_px"], result["height_px"]), (10, 8))
            self.assertEqual(result["transparent_pixels"], 44)
            self.assertEqual(result["partial_alpha_pixels"], 1)
            self.assertEqual(
                result["clear_margins_px"],
                {"left": 2, "top": 1, "right": 2, "bottom": 1},
            )
            self.assertEqual(result["visual_review"], "not_run")
            image.putpixel((0, 0), (10, 10, 10, 1))
            image.save(path)
            self.assertEqual(props.inspect_image(path)["clear_margins_px"]["left"], 0)

    def test_opaque_rgba_empty_alpha_and_palette_alpha(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.png"
            Image.new("RGBA", (5, 5), (10, 10, 10, 255)).save(path)
            result = props.inspect_image(path)
            self.assertTrue(result["has_alpha_channel"])
            self.assertFalse(result["has_transparent_pixels"])
            Image.new("RGBA", (5, 5), (0, 0, 0, 0)).save(path)
            result = props.inspect_image(path)
            self.assertFalse(result["nonempty_cutout"])
            self.assertIsNone(result["clear_margins_px"])
            image = Image.new("P", (5, 5), 0)
            image.putpixel((2, 2), 1)
            image.save(path, transparency=0)
            self.assertEqual(props.inspect_image(path)["transparent_pixels"], 24)

    def test_non_json_nan_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.json"
            path.write_text('{"width": NaN}')
            with self.assertRaisesRegex(ValueError, "Non-JSON"):
                props.read_json(path)

    def test_cli_output_exclusive_and_invalid_revision_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "compiled.json"
            command = [
                sys.executable,
                str(SCRIPT),
                "compile",
                str(ROOT / "assets/examples/waystation-table.props.json"),
                "-o",
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = output.read_bytes()
            self.assertEqual(
                json.loads(before)["source_sha256"],
                hashlib.sha256(
                    (ROOT / "assets/examples/waystation-table.props.json").read_bytes()
                ).hexdigest(),
            )
            second = subprocess.run(
                command, capture_output=True, text=True, check=False
            )
            self.assertEqual(second.returncode, 1)
            self.assertEqual(output.read_bytes(), before)
            change = Path(folder) / "stale.change.json"
            change.write_text(json.dumps({"expected_revision": 999, "changes": []}))
            invalid_output = Path(folder) / "invalid.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "revise",
                    str(ROOT / "assets/examples/waystation-table.props.json"),
                    str(change),
                    "-o",
                    str(invalid_output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertFalse(invalid_output.exists())


if __name__ == "__main__":
    unittest.main()
