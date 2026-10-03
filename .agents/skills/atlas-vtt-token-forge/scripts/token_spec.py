"""Validate token sources, compile filtered briefs, revise, consume handoffs, and measure images.

Never renders/edits images, downloads references, or writes native Atlas data.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COLLECTIONS = (("subjects", "subject_id"), ("assets", "asset_id"), ("references", "reference_id"))


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def load_json(path: str | Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in items:
            if name in result:
                raise ValueError(f"Duplicate JSON key: {name}")
            result[name] = value
        return result

    def constant(value: str) -> None:
        raise ValueError(f"Nonfinite JSON value: {value}")

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)


def tokens(pointer: str) -> list[str]:
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ValueError(f"Invalid nonroot JSON Pointer: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def index(container: Any, token: str) -> str | int:
    if isinstance(container, list):
        if not re.fullmatch(r"0|[1-9][0-9]*", token) or int(token) >= len(container):
            raise ValueError(f"Invalid existing array index: {token}")
        return int(token)
    if not isinstance(container, dict) or token not in container:
        raise ValueError(f"Missing field: {token}")
    return token


def pointer_value(source: Any, pointer: str) -> Any:
    value = source
    for token in tokens(pointer):
        value = value[index(value, token)]
    return value


def schema_errors(value: Any, definition: str | None = None) -> list[str]:
    from jsonschema import Draft202012Validator

    schema = load_json(ROOT / "schemas/token-spec.schema.json")
    if definition:
        schema = {"$defs": schema["$defs"], "$ref": f"#/$defs/{definition}"}
    failures = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: str(error.path))
    return [f"/{'/'.join(map(str, error.path))}: {error.message}" for error in failures]


def validate(source: Any) -> tuple[list[str], list[str]]:
    errors, warnings = schema_errors(source), []
    if errors:
        return errors, warnings
    if type(source["schema_version"]) is not int or type(source["revision"]) is not int:
        errors.append("schema_version and revision must be integers")
    for collection, field in COLLECTIONS:
        ids = [item[field] for item in source[collection]]
        if len(ids) != len(set(ids)):
            errors.append(f"Duplicate {field}")
    subjects = {item["subject_id"]: item for item in source["subjects"]}
    references = {item["reference_id"]: item for item in source["references"]}

    def check_refs(ids: list[str], private: bool, owner: str, identity: bool = False) -> None:
        for ref_id in ids:
            ref = references.get(ref_id)
            if ref is None:
                errors.append(f"{owner}: unknown reference {ref_id}")
            elif not private and ref["gm_only"]:
                errors.append(f"{owner}: public consumer requires private reference {ref_id}")
            elif identity and ref["role"] != "identity":
                errors.append(f"{owner}: identity anchor must use identity role")

    for subject in subjects.values():
        check_refs(subject["identity_reference_ids"], subject["gm_only"], subject["subject_id"], True)
        anatomy = [entry["feature"].strip().casefold() for entry in subject["visible_identity"]["anatomy"]]
        if len(anatomy) != len(set(anatomy)):
            errors.append(f"{subject['subject_id']}: duplicate anatomy feature")
        origin = subject["portrait_origin"]
        if origin and origin["approved_image_ref"] not in subject["identity_reference_ids"]:
            errors.append(f"{subject['subject_id']}: portrait origin must identify a required identity reference")
    for ref in references.values():
        if ref["inspection"] != "inspected":
            if ref["use"] or ref["ignore"] or ref["approved_identity"]:
                errors.append(f"{ref['reference_id']}: uninspected reference has traits or identity approval")
            warnings.append(f"{ref['reference_id']}: reference {ref['inspection']}")
        if ref["approved_identity"] and ref["role"] not in ("identity", "edit_target"):
            errors.append(f"{ref['reference_id']}: identity approval requires an identity or edit_target role")
    for asset in source["assets"]:
        subject = subjects.get(asset["subject_id"])
        if subject is None:
            errors.append(f"{asset['asset_id']}: unknown subject {asset['subject_id']}")
            continue
        private = asset["gm_only"] or subject["gm_only"]
        check_refs(asset["reference_ids"], private, asset["asset_id"])
        target = asset["edit_target_ref"]
        if (asset["intent"] == "edit") != (target is not None):
            errors.append(f"{asset['asset_id']}: edit requires a target and generate must not have one")
        if target:
            check_refs([target], private, asset["asset_id"])
            if target in references and references[target]["role"] != "edit_target":
                errors.append(f"{asset['asset_id']}: edit target requires edit_target role")
        output = asset["output"]
        width, height, ratio = output["width_px"], output["height_px"], output["aspect_ratio"]
        if (width is None) != (height is None):
            errors.append(f"{asset['asset_id']}: specify both dimensions or neither")
        if width and height and ratio and width * ratio[1] != height * ratio[0]:
            errors.append(f"{asset['asset_id']}: dimensions conflict with aspect_ratio")
        circular = asset["kind"] == "portrait_circle" or asset["border"]["mode"] == "atlas_ring"
        if circular and ((width and height and width != height) or (ratio and ratio[0] != ratio[1])):
            errors.append(f"{asset['asset_id']}: circular framing source must be square")
        if asset["kind"] == "top_down" and asset["viewpoint"] != "orthographic_top_down":
            errors.append(f"{asset['asset_id']}: top-down viewpoint must be orthographic_top_down")
    for lock in source["locks"]:
        if lock == "/revision":
            errors.append("Revision is managed and cannot be locked")
        try:
            pointer_value(source, lock)
        except ValueError as error:
            errors.append(f"Lock {lock}: {error}")
    return errors, warnings


def require_valid(source: Any) -> None:
    errors, _ = validate(source)
    if errors:
        raise ValueError("Invalid source: " + "; ".join(errors))


def prompt_for(brief: dict[str, Any]) -> str:
    lines = [f"Asset: {brief['title']} - {brief['presentation']['kind']} tabletop token.",
             f"Intended use: {brief['intended_use']}", f"Subject: {brief['subject_name']}",
             "Visible identity: " + json.dumps(brief["identity"], ensure_ascii=False),
             "Presentation: " + json.dumps(brief["presentation"], ensure_ascii=False),
             "Art direction: " + json.dumps(brief["art_direction"], ensure_ascii=False)]
    if brief["presentation"]["border"]["mode"] == "atlas_ring":
        lines.append("Produce unbordered square artwork for an Atlas circular crop; Atlas supplies the ring separately.")
    if brief["intent"] == "edit":
        lines.append("Edit the supplied approved token target. Apply only the requested change and preserve all other visible identity and presentation details.")
    for ref in brief["references"]:
        lines.append(f"Reference {ref['reference_id']} ({ref['role']}): use {json.dumps(ref['use'], ensure_ascii=False)}; ignore {json.dumps(ref['ignore'], ensure_ascii=False)}.")
    return "\n".join(lines)


def compile_source(source: Any, audience: str = "player", asset_id: str | None = None) -> dict[str, Any]:
    require_valid(source)
    if audience not in ("player", "gm"):
        raise ValueError("Audience must be player or gm")
    subjects = {item["subject_id"]: item for item in source["subjects"]}
    references = {item["reference_id"]: item for item in source["references"]}
    briefs = []
    for asset in source["assets"]:
        subject = subjects[asset["subject_id"]]
        if asset_id is not None and asset["asset_id"] != asset_id:
            continue
        if audience == "player" and (asset["gm_only"] or subject["gm_only"]):
            continue
        used = list(dict.fromkeys(subject["identity_reference_ids"] + asset["reference_ids"] + ([asset["edit_target_ref"]] if asset["edit_target_ref"] else [])))
        visible_refs, unresolved, issues = [], [], []
        for ref_id in used:
            ref = references[ref_id]
            if audience == "player" and ref["gm_only"]:
                raise ValueError("Private reference reached public compilation")
            if ref["inspection"] != "inspected":
                unresolved.append(ref_id)
            else:
                visible_refs.append({field: copy.deepcopy(ref[field]) for field in ("reference_id", "locator", "role", "use", "ignore", "approved_identity")})
        identity = subject["visible_identity"]
        if not identity["form"].strip() or (not identity["face_head"].strip() and not identity["anatomy"]):
            issues.append("Subject appearance is unspecified")
        if not asset["intended_use"].strip() or not asset["viewpoint"].strip():
            issues.append("Intended use or viewpoint is unspecified")
        if asset["background"]["mode"] == "unspecified":
            issues.append("Background treatment is unspecified")
        issues.extend(f"Reference {ref_id} has not been inspected and supplied" for ref_id in unresolved)
        origin = subject["portrait_origin"]
        if origin and not references[origin["approved_image_ref"]]["approved_identity"]:
            issues.append("Portrait identity approval has not been confirmed in this task")
        brief = {"asset_id": asset["asset_id"], "subject_id": subject["subject_id"], "title": asset["title"],
                 "subject_name": subject["name"], "intended_use": asset["intended_use"], "intent": asset["intent"],
                 "identity": copy.deepcopy(identity),
                 "presentation": {field: copy.deepcopy(asset[field]) for field in ("kind", "viewpoint", "pose", "background", "border", "composition", "output", "constraints")},
                 "art_direction": copy.deepcopy(asset["art_direction"]), "references": visible_refs,
                 "edit_target_ref": asset["edit_target_ref"], "unresolved_reference_ids": unresolved,
                 "readiness_issues": issues, "render_ready": not issues,
                 "atlas_display_hint": {"showRing": asset["border"]["mode"] == "atlas_ring", "status": "not_imported"}}
        brief["image_instructions"] = prompt_for(brief)
        briefs.append(brief)
    if not briefs:
        raise ValueError("No selected tokens are visible to this audience")
    return {"schema_version": 1, "source_id": source["spec_id"], "source_revision": source["revision"],
            "source_sha256": hashlib.sha256(canonical(source).encode()).hexdigest(), "audience": audience, "briefs": briefs}


def revise(source: Any, change: Any, allow_locked: list[str] | None = None) -> dict[str, Any]:
    require_valid(source)
    if not isinstance(change, dict) or set(change) != {"expected_revision", "changes"}:
        raise ValueError("Change requires only expected_revision and changes")
    if type(change["expected_revision"]) is not int or change["expected_revision"] != source["revision"]:
        raise ValueError("Stale or invalid expected_revision")
    if not isinstance(change["changes"], list) or not change["changes"]:
        raise ValueError("changes must be a nonempty replacement list")
    allowed = set(allow_locked or [])
    if not allowed.issubset(source["locks"]):
        raise ValueError("--allow-locked must name exact existing locks")
    result, paths = copy.deepcopy(source), []
    for entry in change["changes"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "value"} or not isinstance(entry["path"], str):
            raise ValueError("Each change requires only a string path and value")
        parts = tokens(entry["path"])
        if parts[0] in ("schema_version", "spec_id", "revision", "locks"):
            raise ValueError("Source identity, revision, and lock definitions require a deliberate master edit")
        if any(parts[:len(other)] == other or other[:len(parts)] == parts for other in paths):
            raise ValueError("Overlapping change paths")
        paths.append(parts)
        parent = result
        for part in parts[:-1]:
            parent = parent[index(parent, part)]
        parent[index(parent, parts[-1])] = copy.deepcopy(entry["value"])
    for lock in source["locks"]:
        if lock not in allowed:
            try:
                same = canonical(pointer_value(source, lock)) == canonical(pointer_value(result, lock))
            except ValueError:
                same = False
            if not same:
                raise ValueError(f"Locked field changed: {lock}")
    for collection, field in COLLECTIONS:
        before = [entry[field] for entry in source[collection]]
        after = [entry.get(field) for entry in result[collection]] if isinstance(result[collection], list) and all(isinstance(item, dict) for item in result[collection]) else []
        if after[:len(before)] != before:
            raise ValueError(f"Existing {field} positions cannot change")
    for before, after in zip(source["assets"], result["assets"]):
        if before["subject_id"] != after.get("subject_id"):
            raise ValueError("Existing asset cannot be rebound")
    for before, after in zip(source["subjects"], result["subjects"]):
        if before["portrait_origin"] != after.get("portrait_origin"):
            raise ValueError("Portrait origin cannot be rewritten through a narrow revision")
    if canonical(result) == canonical(source):
        raise ValueError("No source change; revision was not incremented")
    result["revision"] += 1
    require_valid(result)
    return result


def from_handoff(handoff: Any, spec_id: str, asset_id: str, kind: str) -> dict[str, Any]:
    required = {"subject_id", "asset_id", "source_revision", "source_sha256", "approved_image", "identity", "art_direction", "references", "approval_basis", "token_status", "atlas_status"}
    if not isinstance(handoff, dict) or set(handoff) != required:
        raise ValueError("Expected the exact public Portrait Forge handoff shape")
    failures = schema_errors(handoff["identity"], "identity") + schema_errors(handoff["art_direction"], "style")
    for field in ("subject_id", "asset_id"):
        failures.extend(schema_errors(handoff[field], "id"))
    if type(handoff["source_revision"]) is not int or handoff["source_revision"] < 1:
        failures.append("Invalid portrait source revision")
    if not isinstance(handoff["source_sha256"], str) or not re.fullmatch("[a-f0-9]{64}", handoff["source_sha256"]):
        failures.append("Invalid portrait source hash")
    if not isinstance(handoff["approval_basis"], str) or not handoff["approval_basis"].strip():
        failures.append("Portrait approval assertion is missing")
    if handoff["token_status"] != "not_created" or handoff["atlas_status"] != "not_imported":
        failures.append("Handoff must describe an uncreated token and no import")
    if not isinstance(handoff["references"], list):
        failures.append("Handoff references must be an array")
    if not isinstance(handoff["approved_image"], str):
        failures.append("Approved portrait path must be a string")
    if failures:
        raise ValueError("Invalid handoff: " + "; ".join(failures))
    image_path = Path(handoff["approved_image"]).expanduser().resolve()
    if not image_path.is_file() or image_path.stat().st_size == 0:
        raise ValueError("Approved portrait must be a nonempty available local file")
    source = load_json(ROOT / "assets/starter.token.json")
    source["spec_id"] = spec_id
    subject, asset = source["subjects"][0], source["assets"][0]
    subject.update({"subject_id": handoff["subject_id"], "name": handoff["subject_id"], "visible_identity": copy.deepcopy(handoff["identity"])})
    anchor_id = "portrait-approved-image"
    refs = []
    for ref in handoff["references"]:
        fields = {"reference_id", "locator", "role", "use", "ignore", "approved_identity"}
        if not isinstance(ref, dict) or set(ref) != fields:
            raise ValueError("Invalid portrait handoff reference shape")
        if ref["role"] != "style" and not (ref["role"] in ("identity", "edit_target") and ref["approved_identity"] is True):
            raise ValueError("Handoff contains an unapproved or unrelated reference")
        candidate = {**copy.deepcopy(ref), "inspection": "inspected", "gm_only": False}
        if schema_errors(candidate, "reference"):
            raise ValueError("Invalid portrait handoff reference fields")
        # Claimed traits and inspection are not observations by the receiving workflow.
        candidate.update({"role": "identity" if ref["role"] == "edit_target" else ref["role"], "inspection": "uninspected", "use": [], "ignore": [], "approved_identity": False})
        refs.append(candidate)
    while anchor_id in {ref["reference_id"] for ref in refs}:
        anchor_id += "-new"
    refs.insert(0, {"reference_id": anchor_id, "locator": str(image_path), "role": "identity", "inspection": "uninspected", "use": [], "ignore": [], "approved_identity": False, "gm_only": False})
    subject["identity_reference_ids"] = [ref["reference_id"] for ref in refs if ref["role"] == "identity"]
    subject["portrait_origin"] = {"portrait_asset_id": handoff["asset_id"], "source_revision": handoff["source_revision"], "source_sha256": handoff["source_sha256"], "approved_image_ref": anchor_id, "approval_basis": handoff["approval_basis"]}
    asset.update({"asset_id": asset_id, "subject_id": subject["subject_id"], "title": f"{subject['name']} token", "kind": kind, "intended_use": "Movable tabletop token matching the approved portrait", "viewpoint": "Eye level portrait" if kind == "portrait_circle" else "orthographic_top_down" if kind == "top_down" else "Whole creature three-quarter view", "art_direction": copy.deepcopy(handoff["art_direction"]), "reference_ids": [ref["reference_id"] for ref in refs if ref["role"] == "style"]})
    asset["background"] = {"mode": "transparent", "description": "Preserve clean alpha around the subject"}
    if kind != "portrait_circle":
        asset["border"] = {"mode": "none", "description": "Whole unframed artwork with Atlas ring off"}
        asset["output"]["aspect_ratio"] = None
    source["references"] = refs
    source["locks"] = ["/subjects/0/visible_identity"]
    source["assumptions"] = ["Handoff asserts prior user approval. Receiving workflow must inspect every used image and confirm approval from trusted task context."]
    require_valid(source)
    return source


def inspect_image(path: str) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as image:
        alpha = image.convert("RGBA").getchannel("A")
        histogram = alpha.histogram()
        pixels = image.width * image.height
        bounds = alpha.getbbox()
        return {"file": str(Path(path).resolve()), "format": image.format, "width_px": image.width,
                "height_px": image.height, "has_alpha": "A" in image.getbands() or "transparency" in image.info,
                "alpha_extrema": list(alpha.getextrema()), "has_transparent_pixels": sum(histogram[:255]) > 0,
                "nonopaque_pixel_fraction": sum(histogram[:255]) / pixels,
                "fully_transparent_pixel_fraction": histogram[0] / pixels,
                "nontransparent_bounds_px": list(bounds) if bounds else None,
                "visual_review": "not_run", "tabletop_review": "not_run", "identity_approval": "not_verified"}


def write_output(value: Any, path: str | None, inputs: list[str], text_output: bool = False) -> None:
    content = value if text_output else json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
    if path is None:
        print(content)
        return
    output = Path(path).expanduser().resolve()
    if output in [Path(item).expanduser().resolve() for item in inputs]:
        raise ValueError("Output cannot overwrite an input")
    with output.open("x") as handle:
        handle.write(content + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "compile", "revise", "from-handoff", "inspect-image"):
        command = commands.add_parser(name)
        command.add_argument("input")
        command.add_argument("-o", "--output")
        if name == "compile":
            command.add_argument("--audience", choices=("player", "gm"), default="player")
            command.add_argument("--asset")
            command.add_argument("--text", action="store_true")
        elif name == "revise":
            command.add_argument("change")
            command.add_argument("--allow-locked", action="append", default=[])
        elif name == "from-handoff":
            command.add_argument("--spec-id", required=True)
            command.add_argument("--asset-id", required=True)
            command.add_argument("--kind", choices=("portrait_circle", "top_down", "creature_cutout"), default="portrait_circle")
    args = parser.parse_args()
    try:
        inputs, text_output = [args.input], False
        if args.command == "inspect-image":
            result = inspect_image(args.input)
        else:
            source = load_json(args.input)
            if args.command == "validate":
                errors, warnings = validate(source)
                write_output({"valid": not errors, "errors": errors, "warnings": warnings}, args.output, inputs)
                return int(bool(errors))
            if args.command == "compile":
                result = compile_source(source, args.audience, args.asset)
                if args.text:
                    if len(result["briefs"]) != 1 or not result["briefs"][0]["render_ready"]:
                        raise ValueError("Text output requires exactly one ready visible token")
                    result, text_output = result["briefs"][0]["image_instructions"], True
            elif args.command == "revise":
                inputs.append(args.change)
                result = revise(source, load_json(args.change), args.allow_locked)
            elif args.command == "from-handoff":
                result = from_handoff(source, args.spec_id, args.asset_id, args.kind)
                inputs.append(source["approved_image"])
            else:
                raise ValueError("Unknown command")
        write_output(result, args.output, inputs, text_output)
        return 0
    except (ValueError, OSError, ImportError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
