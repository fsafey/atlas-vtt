"""Validate/derive props briefs, preserve revision locks, inspect raster metadata."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VISUAL_FIELDS = (
    "asset_id",
    "object_id",
    "name",
    "kind",
    "description",
    "materials",
    "viewpoint",
    "orientation",
    "footprint",
    "composition",
    "shadow",
    "output",
)


def reject_constant(value: str) -> Any:
    raise ValueError(f"Non-JSON numeric constant: {value}")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(), parse_constant=reject_constant)


def pointer_parts(path: str) -> list[str]:
    if not path.startswith("/") or path == "/":
        raise ValueError(f"Expected a field JSON Pointer: {path}")
    parts = path[1:].split("/")
    for part in parts:
        for i, char in enumerate(part):
            if char == "~" and (i + 1 == len(part) or part[i + 1] not in "01"):
                raise ValueError(f"Invalid pointer escape: {path}")
    return [part.replace("~1", "/").replace("~0", "~") for part in parts]


def field_at(document: Any, path: str) -> tuple[Any, Any]:
    parts = pointer_parts(path)
    parent = document
    for part in parts[:-1]:
        parent = child_at(parent, part)
    key: Any = parts[-1]
    if isinstance(parent, list):
        key = list_index(key, len(parent))
    child_at(parent, str(key))
    return parent, key


def list_index(value: str, length: int) -> int:
    if not value.isdigit() or str(int(value)) != value or int(value) >= length:
        raise ValueError(f"Invalid existing array index: {value}")
    return int(value)


def child_at(parent: Any, key: str) -> Any:
    if isinstance(parent, list):
        return parent[list_index(key, len(parent))]
    if isinstance(parent, dict) and key in parent:
        return parent[key]
    raise ValueError(f"Missing existing field: {key}")


def overlaps(left: str, right: str) -> bool:
    a, b = pointer_parts(left), pointer_parts(right)
    return a[: len(b)] == b or b[: len(a)] == a


def validate(spec: dict[str, Any]) -> None:
    from jsonschema import Draft202012Validator, ValidationError

    schema = read_json(ROOT / "schemas/props-spec.schema.json")
    try:
        Draft202012Validator(schema).validate(spec)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    for collection, key in (("assets", "asset_id"), ("references", "reference_id")):
        ids = [item[key] for item in spec[collection]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {key}")
    refs = {ref["reference_id"]: ref for ref in spec["references"]}
    for asset in spec["assets"]:
        for rid in asset["reference_ids"]:
            if rid not in refs:
                raise ValueError(f"Unknown reference: {rid}")
            if not asset["gm_only"] and refs[rid]["gm_only"]:
                raise ValueError("Player asset depends on private reference")
        edit = asset.get("edit")
        if edit:
            rid = edit["target_reference_id"]
            if rid not in asset["reference_ids"] or refs[rid]["role"] != "edit_target":
                raise ValueError("Edit target must be a used edit_target reference")
        if (
            asset["shadow"]["mode"] == "cast"
            and asset["shadow"]["direction_deg"] is None
        ):
            raise ValueError("Cast shadow needs a direction")
        if asset["shadow"]["mode"] == "none" and asset["shadow"]["reach_fraction"] != 0:
            raise ValueError("No shadow requires zero reach")
        output = asset["output"]
        if (output["width_px"] is None) != (output["height_px"] is None):
            raise ValueError("Specify both requested dimensions or neither")
    for lock in spec["locks"]:
        if lock == "/revision":
            raise ValueError("Revision is managed and cannot be locked")
        field_at(spec, lock)


def compile_spec(
    spec: dict[str, Any], audience: str = "player", asset_id: str | None = None
) -> dict[str, Any]:
    validate(spec)
    refs = {ref["reference_id"]: ref for ref in spec["references"]}
    briefs = []
    for asset in spec["assets"]:
        if audience == "player" and asset["gm_only"]:
            continue
        if asset_id and asset["asset_id"] != asset_id:
            continue
        brief = {key: copy.deepcopy(asset[key]) for key in VISUAL_FIELDS}
        brief["art_direction"] = copy.deepcopy(spec["art_direction"])
        brief["assumptions"] = copy.deepcopy(spec["assumptions"])
        brief["references"] = []
        unresolved = []
        for rid in asset["reference_ids"]:
            ref = refs[rid]
            if ref["inspection"] != "inspected":
                unresolved.append(
                    {"reference_id": rid, "inspection": ref["inspection"]}
                )
            else:
                brief["references"].append(
                    {
                        key: ref[key]
                        for key in (
                            "reference_id",
                            "locator",
                            "role",
                            "use",
                            "ignore",
                        )
                    }
                )
        brief["unresolved_references"] = unresolved
        missing = []
        if not asset["description"].strip():
            missing.append("description")
        if not spec["art_direction"]["style"].strip():
            missing.append("art_direction.style")
        if any(asset["footprint"][key] is None for key in ("width", "length")):
            missing.append("footprint")
        if asset.get("edit"):
            brief["edit"] = copy.deepcopy(asset["edit"])
            target = refs[asset["edit"]["target_reference_id"]]
            if target["inspection"] != "inspected" or not target["approved"]:
                missing.append("inspected_approved_edit_target")
        brief["missing_requirements"] = missing
        brief["render_ready"] = not missing and not unresolved
        briefs.append(brief)
    if asset_id and not briefs:
        raise ValueError("Requested asset is missing or excluded for this audience")
    return {
        "spec_id": spec["spec_id"],
        "revision": spec["revision"],
        "audience": audience,
        "briefs": briefs,
        "image_status": "not_generated",
        "atlas_status": "not_imported",
    }


def revise(
    spec: dict[str, Any], change: dict[str, Any], allow_locked: list[str] | None = None
) -> dict[str, Any]:
    validate(spec)
    allowed = set(allow_locked or [])
    if not allowed <= set(spec["locks"]):
        raise ValueError("--allow-locked must name an exact existing lock")
    if set(change) != {"expected_revision", "changes"}:
        raise ValueError("Change requires expected_revision and changes only")
    expected = change["expected_revision"]
    if type(expected) is not int or expected != spec["revision"]:
        raise ValueError("Stale or invalid expected revision")
    changes = change["changes"]
    if not isinstance(changes, list) or not changes:
        raise ValueError("Nonempty changes required")
    result = copy.deepcopy(spec)
    paths: list[str] = []
    for item in changes:
        if not isinstance(item, dict) or set(item) != {"path", "value"}:
            raise ValueError("Each change requires path and value only")
        path = item["path"]
        if not isinstance(path, str):
            raise TypeError("Change path must be a string")
        parts = pointer_parts(path)
        if parts[0] in {"schema_version", "spec_id", "revision", "locks"}:
            raise ValueError(
                "Identity/revision/lock definitions need a deliberate master edit"
            )
        if parts[0] in {"assets", "references"} and (
            len(parts) < 3 or parts[2].endswith("_id")
        ):
            raise ValueError(
                "Collection replacement or identity rebinding is protected"
            )
        if any(overlaps(path, old) for old in paths):
            raise ValueError("Duplicate or overlapping changes")
        for lock in spec["locks"]:
            if overlaps(path, lock) and lock not in allowed:
                raise ValueError(f"Locked field: {lock}")
        parent, key = field_at(result, path)
        if parent[key] == item["value"]:
            raise ValueError(f"No-op change: {path}")
        parent[key] = copy.deepcopy(item["value"])
        paths.append(path)
    result["revision"] += 1
    validate(result)
    return result


def inspect_image(path: Path) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as original:
        original.load()
        has_alpha = "A" in original.getbands() or "transparency" in original.info
        alpha = original.convert("RGBA").getchannel("A")
        histogram = alpha.histogram()
        bounds = alpha.getbbox()
        width, height = original.size
        return {
            "file": str(path.resolve()),
            "width_px": width,
            "height_px": height,
            "format": original.format,
            "mode": original.mode,
            "has_alpha_channel": has_alpha,
            "alpha_min": alpha.getextrema()[0],
            "alpha_max": alpha.getextrema()[1],
            "transparent_pixels": histogram[0],
            "partial_alpha_pixels": sum(histogram[1:255]),
            "opaque_pixels": histogram[255],
            "nonempty_cutout": bounds is not None,
            "has_transparent_pixels": histogram[0] > 0,
            "alpha_bounds_xyxy": bounds,
            "clear_margins_px": None
            if bounds is None
            else {
                "left": bounds[0],
                "top": bounds[1],
                "right": width - bounds[2],
                "bottom": height - bounds[3],
            },
            "visual_review": "not_run",
            "placement_review": "not_run",
        }


def write_new(path: Path, content: str) -> None:
    with path.open("x") as stream:
        stream.write(content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "compile", "revise", "inspect-image"):
        sub = commands.add_parser(name)
        sub.add_argument("source", type=Path)
        if name == "compile":
            sub.add_argument("--audience", choices=("player", "gm"), default="player")
            sub.add_argument("--asset")
            sub.add_argument("--text", action="store_true")
            sub.add_argument("-o", "--output", type=Path)
        if name == "revise":
            sub.add_argument("change", type=Path)
            sub.add_argument("--allow-locked", action="append", default=[])
            sub.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, Any]
    try:
        if args.command == "inspect-image":
            result = inspect_image(args.source)
        else:
            source_bytes = args.source.read_bytes()
            spec = json.loads(source_bytes, parse_constant=reject_constant)
            if args.command == "validate":
                validate(spec)
                result = {
                    "valid": True,
                    "assets": len(spec["assets"]),
                    "revision": spec["revision"],
                }
            elif args.command == "revise":
                result = revise(spec, read_json(args.change), args.allow_locked)
            else:
                result = compile_spec(spec, args.audience, args.asset)
                result["source_sha256"] = hashlib.sha256(source_bytes).hexdigest()
        if args.command == "compile" and args.text:
            content = (
                "\n\n".join(
                    json.dumps(b, indent=2, ensure_ascii=False)
                    for b in result["briefs"]
                )
                + "\n"
            )
        else:
            content = (
                json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
            )
        if getattr(args, "output", None):
            write_new(args.output, content)
        else:
            print(content, end="")
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
