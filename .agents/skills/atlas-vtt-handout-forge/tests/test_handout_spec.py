"""Behavioral checks for text fidelity, disclosure, revisions, and raster embedding."""

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

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/handout_spec.py"
SPEC = importlib.util.spec_from_file_location("handout_spec", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
forge = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(forge)


class HandoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = json.loads(
            (ROOT / "assets/examples/ferry-letter.handout.json").read_text()
        )

    def patch(self, path: str, value: Any) -> dict[str, Any]:
        return {"expected_revision": 1, "changes": [{"path": path, "value": value}]}

    def test_all_sources_are_valid(self) -> None:
        for path in [
            ROOT / "assets/starter.handout.json",
            *sorted((ROOT / "assets/examples").glob("*.handout.json")),
        ]:
            with self.subTest(path=path):
                forge.validate(json.loads(path.read_text()))

    def test_managed_revision_cannot_be_locked(self) -> None:
        self.source["locks"] = ["/revision"]
        with self.assertRaises(ValueError):
            forge.validate(self.source)
        with self.assertRaises(ValueError):
            forge.revise(
                self.source, self.patch("/documents/0/material", "Cream paper")
            )
        self.assertEqual(self.source["revision"], 1)

    def test_html_metacharacters_and_unicode_are_exact(self) -> None:
        text = '\n  <img src="x" onerror="run()"> & </div><script>evil()</script>\r\n\tÉlan  نور\n'
        self.source["documents"][0]["wording"]["content"] = text
        output = forge.compose(self.source, "letter-01")
        forge.check_text(self.source, "letter-01", output)
        self.assertNotIn('<img src="x"', output)
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)
        self.assertIn("&#13;", output)

    def test_changed_html_text_fails(self) -> None:
        output = forge.compose(self.source, "letter-01").replace(
            "third bell", "fourth bell"
        )
        with self.assertRaisesRegex(ValueError, "differs"):
            forge.check_text(self.source, "letter-01", output)

    def test_duplicate_or_nested_text_container_fails(self) -> None:
        output = forge.compose(self.source, "letter-01")
        for altered in [
            output + '<div id="approved-wording"></div>',
            output.replace("third bell", "<b>third bell</b>"),
        ]:
            with self.subTest(altered=altered[:20]), self.assertRaises(ValueError):
                forge.check_text(self.source, "letter-01", altered)

    def test_draft_and_empty_text_cannot_compose(self) -> None:
        self.source["documents"][0]["wording"]["approval"] = "draft"
        with self.assertRaisesRegex(ValueError, "draft"):
            forge.compose(self.source, "letter-01")
        self.source["documents"][0]["wording"] = {
            "content": "",
            "approval": "approved",
            "basis": "User supplied exact text.",
        }
        with self.assertRaisesRegex(ValueError, "nonempty"):
            forge.validate(self.source)

    def test_starter_is_not_ready_for_render_or_composition(self) -> None:
        source = json.loads((ROOT / "assets/starter.handout.json").read_text())
        doc = forge.brief(source)["documents"][0]
        self.assertFalse(doc["render_ready"])
        self.assertFalse(doc["composition_ready"])

    def test_public_brief_excludes_private_and_unused_data(self) -> None:
        source = json.loads(
            (ROOT / "assets/examples/discovery-set.handout.json").read_text()
        )
        output = forge.brief(source)
        encoded = json.dumps(output)
        self.assertNotIn("PRIVATE", encoded)
        self.assertNotIn("impostor", encoded)
        self.assertNotIn("private-impostor-sketch", encoded)
        self.assertNotIn("guild-seal-not-attached", encoded)
        self.assertNotIn("gm_notes", encoded)
        poster = next(
            doc for doc in output["documents"] if doc["asset_id"] == "poster-01"
        )
        self.assertFalse(poster["render_ready"])
        self.assertEqual(poster["unresolved_reference_ids"], ["guild-seal"])

    def test_required_private_reference_blocks_player_artwork(self) -> None:
        self.source["references"] = [
            {
                "ref_id": "secret",
                "locator": "private/path.png",
                "roles": ["style"],
                "status": "inspected",
                "gm_only": True,
                "use": "PRIVATE SHAPE",
                "ignore": "PRIVATE MARK",
            }
        ]
        self.source["documents"][0]["reference_ids"] = ["secret"]
        public = forge.brief(self.source)
        self.assertFalse(public["documents"][0]["render_ready"])
        self.assertNotIn("PRIVATE", json.dumps(public))
        self.assertNotIn("private/path", json.dumps(public))
        self.assertTrue(forge.brief(self.source, "gm")["documents"][0]["render_ready"])

    def test_private_document_requires_gm_audience(self) -> None:
        self.source["documents"][0]["gm_only"] = True
        with self.assertRaisesRegex(ValueError, "private"):
            forge.compose(self.source, "letter-01")
        forge.check_text(
            self.source,
            "letter-01",
            forge.compose(self.source, "letter-01", audience="gm"),
            "gm",
        )

    def test_wording_is_not_sent_in_background_prompt(self) -> None:
        doc = forge.brief(self.source)["documents"][0]
        self.assertNotIn("The tide remembers", doc["background_prompt"])
        self.assertEqual(
            doc["wording"]["content"], self.source["documents"][0]["wording"]["content"]
        )
        self.assertNotIn("basis", doc["wording"])

    def test_narrow_revision_preserves_every_other_value(self) -> None:
        before = copy.deepcopy(self.source)
        revised = forge.revise(
            self.source, self.patch("/documents/0/material", "Ivory paper.")
        )
        expected = copy.deepcopy(before)
        expected["revision"] = 2
        expected["documents"][0]["material"] = "Ivory paper."
        self.assertEqual(revised, expected)
        self.assertEqual(self.source, before)

    def test_stale_identity_parent_and_approval_changes_fail(self) -> None:
        change = self.patch("/documents/0/material", "Ivory")
        change["expected_revision"] = 0
        with self.assertRaisesRegex(ValueError, "stale"):
            forge.revise(self.source, change)
        for path, value in [
            ("/documents/0/asset_id", "changed"),
            ("/documents/0", {}),
            ("/documents/0/wording/approval", "draft"),
            ("/locks", []),
            ("/documents/0/gm_only", True),
        ]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                forge.revise(self.source, self.patch(path, value))

    def test_locked_wording_requires_exact_authorization_and_resets_approval(
        self,
    ) -> None:
        path = "/documents/0/wording/content"
        change = self.patch(path, "A newly requested sentence.")
        with self.assertRaisesRegex(ValueError, "locked"):
            forge.revise(self.source, change)
        revised = forge.revise(self.source, change, [path])
        self.assertEqual(
            revised["documents"][0]["wording"],
            {
                "content": "A newly requested sentence.",
                "approval": "draft",
                "basis": "",
            },
        )
        with self.assertRaisesRegex(ValueError, "existing exact lock"):
            forge.revise(self.source, change, ["/documents/0/wording"])

    def test_indirect_approval_lock_cannot_be_bypassed(self) -> None:
        self.source["locks"] = ["/documents/0/wording/approval"]
        with self.assertRaisesRegex(ValueError, "indirectly"):
            forge.revise(
                self.source, self.patch("/documents/0/wording/content", "New wording.")
            )

    def test_existing_user_authority_completes_final_wording_revision(self) -> None:
        path = "/documents/0/wording/content"
        basis = "User explicitly delegated choosing final replacement wording."
        revised = forge.revise(
            self.source, self.patch(path, "The ferry waits."), [path], basis
        )
        self.assertEqual(
            revised["documents"][0]["wording"],
            {"content": "The ferry waits.", "approval": "approved", "basis": basis},
        )
        forge.check_text(revised, "letter-01", forge.compose(revised, "letter-01"))

    def test_final_wording_needs_recorded_basis_but_public_output_omits_it(
        self,
    ) -> None:
        self.source["documents"][0]["wording"]["basis"] = ""
        with self.assertRaisesRegex(ValueError, "basis"):
            forge.validate(self.source)
        self.source["documents"][0]["wording"]["basis"] = "PRIVATE operator context"
        self.assertNotIn("PRIVATE", json.dumps(forge.brief(self.source)))
        self.assertNotIn("PRIVATE", forge.compose(self.source, "letter-01"))

    def test_noncanonical_index_cannot_bypass_lock(self) -> None:
        with self.assertRaisesRegex(ValueError, "index"):
            forge.revise(
                self.source, self.patch("/documents/00/wording/content", "New")
            )

    def test_duplicate_changes_and_no_op_fail(self) -> None:
        patch = self.patch("/documents/0/material", "Ivory")
        patch["changes"].append(patch["changes"][0])
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            forge.revise(self.source, patch)
        with self.assertRaisesRegex(ValueError, "no effect"):
            forge.revise(
                self.source,
                self.patch(
                    "/documents/0/material", self.source["documents"][0]["material"]
                ),
            )

    def test_reference_rebinding_resets_observation(self) -> None:
        self.source["references"] = [
            {
                "ref_id": "paper",
                "locator": "old.png",
                "roles": ["material"],
                "status": "inspected",
                "gm_only": False,
                "use": "old grain",
                "ignore": "old border",
            }
        ]
        self.source["documents"][0]["reference_ids"] = ["paper"]
        revised = forge.revise(
            self.source, self.patch("/references/0/locator", "new.png")
        )
        self.assertEqual(revised["references"][0]["status"], "uninspected")
        self.assertEqual(revised["references"][0]["use"], "")
        self.assertFalse(forge.brief(revised)["documents"][0]["render_ready"])

    def test_duplicate_ids_unknown_refs_and_bad_edit_binding_fail(self) -> None:
        for case in ("duplicate", "unknown", "bad_edit"):
            source = copy.deepcopy(self.source)
            if case == "duplicate":
                source["documents"].append(copy.deepcopy(source["documents"][0]))
            elif case == "unknown":
                source["documents"][0]["reference_ids"] = ["missing"]
            else:
                source["documents"][0]["edit_target_id"] = "missing"
            with self.subTest(case=case), self.assertRaises(ValueError):
                forge.validate(source)

    def test_unsupported_text_and_css_values_fail(self) -> None:
        for text in ["a\x00b", "a\x01b", "a\ud800b"]:
            source = copy.deepcopy(self.source)
            source["documents"][0]["wording"]["content"] = text
            with self.subTest(text=repr(text)), self.assertRaises(ValueError):
                forge.validate(source)
        self.source["documents"][0]["typography"]["family"] = "serif; color: red"
        with self.assertRaisesRegex(ValueError, "font"):
            forge.validate(self.source)

    def test_overflowing_layout_is_rejected(self) -> None:
        self.source["documents"][0]["layout"]["reserved_illustration_px"] = 1500
        with self.assertRaisesRegex(ValueError, "no text"):
            forge.validate(self.source)

    def test_observations_require_inspection(self) -> None:
        self.source["references"] = [
            {
                "ref_id": "paper",
                "locator": "missing.png",
                "roles": ["material"],
                "status": "unavailable",
                "gm_only": False,
                "use": "imagined appearance",
                "ignore": "",
            }
        ]
        with self.assertRaisesRegex(ValueError, "observations"):
            forge.validate(self.source)

    def test_embedded_raster_is_verified_and_self_contained(self) -> None:
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo

        metadata_fields = PngInfo()
        metadata_fields.add_text("prompt", "PRIVATE GENERATED PROMPT")
        self.source["documents"][0]["layout"] = {
            "width_px": 20,
            "height_px": 30,
            "margin_px": 1,
            "reserved_illustration_px": 0,
        }
        self.source["documents"][0]["typography"].update(font_px=1, line_height=1)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.png"
            Image.new("RGBA", (20, 30), (1, 2, 3, 0)).save(
                path, pnginfo=metadata_fields
            )
            metadata = forge.inspect_image(path)
            self.assertEqual(
                (metadata["width_px"], metadata["height_px"], metadata["alpha_min"]),
                (20, 30, 0),
            )
            output = forge.compose(self.source, "letter-01", path)
            forge.check_text(self.source, "letter-01", output)
            self.assertIn("data:image/png;base64,", output)
            self.assertNotIn(str(path), output)
            import base64
            import io
            import re

            encoded = re.search(r"data:image/png;base64,([^']+)", output)
            assert encoded is not None
            embedded = base64.b64decode(encoded.group(1))
            self.assertNotIn(b"PRIVATE", embedded)
            with Image.open(io.BytesIO(embedded)) as clean:
                self.assertNotIn("prompt", clean.info)
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')
            with self.assertRaises(OSError):
                forge.compose(self.source, "letter-01", path)

    def test_background_dimensions_and_animation_are_not_silently_changed(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mismatch.png"
            Image.new("RGB", (2, 3)).save(path)
            with self.assertRaisesRegex(ValueError, "dimensions"):
                forge.compose(self.source, "letter-01", path)
            animation = Path(folder) / "animated.gif"
            Image.new("RGB", (2, 3), "red").save(
                animation,
                save_all=True,
                append_images=[Image.new("RGB", (2, 3), "blue")],
                duration=100,
                loop=0,
            )
            with self.assertRaisesRegex(ValueError, "static"):
                forge.compose(self.source, "letter-01", animation)

    def test_output_never_overwrites_and_text_bytes_are_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "exact.txt"
            text = "\r\nA & B\t\n"
            forge.write_new(path, text)
            self.assertEqual(path.read_bytes(), text.encode("utf-8"))
            with self.assertRaises(FileExistsError):
                forge.write_new(path, "overwritten")
            self.assertEqual(path.read_bytes(), text.encode("utf-8"))

    def test_cli_full_flow_and_failure_exit(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "letter.html"
            cmd = [sys.executable, str(MODULE_PATH)]
            source = str(ROOT / "assets/examples/ferry-letter.handout.json")
            for args in [
                ["compose", source, "--asset", "letter-01", "-o", str(output)],
                ["check-text", source, "--asset", "letter-01", "--html", str(output)],
            ]:
                result = subprocess.run(
                    cmd + args, capture_output=True, text=True, check=False
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(
                cmd + ["compose", source, "--asset", "letter-01", "-o", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
