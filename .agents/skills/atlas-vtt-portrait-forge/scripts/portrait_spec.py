"""Portrait source validation, filtered briefs, controlled revisions, and image metadata.

Never generates/edits images, downloads references, or writes native Atlas data.
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


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def load_json(path: str | Path) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def constant(value: str) -> None:
        raise ValueError(f"Nonfinite JSON value: {value}")

    return json.loads(Path(path).read_text(), object_pairs_hook=pairs, parse_constant=constant)


def parts(pointer: str) -> list[str]:
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ValueError(f"Invalid nonroot JSON Pointer: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/")]


def key(container: Any, token: str) -> str | int:
    if isinstance(container, list):
        if not re.fullmatch(r"0|[1-9][0-9]*", token) or int(token) >= len(container):
            raise ValueError(f"Invalid existing array index: {token}")
        return int(token)
    if not isinstance(container, dict) or token not in container:
        raise ValueError(f"Missing field: {token}")
    return token


def pointer_value(source: Any, pointer: str) -> Any:
    value = source
    for token in parts(pointer):
        value = value[key(value, token)]
    return value


def validate(source: Any) -> tuple[list[str], list[str]]:
    from jsonschema import Draft202012Validator

    schema = load_json(ROOT / "schemas/portrait-spec.schema.json")
    failures = sorted(Draft202012Validator(schema).iter_errors(source), key=lambda e: str(e.path))
    errors = [f"/{'/'.join(map(str, error.path))}: {error.message}" for error in failures]
    warnings: list[str] = []
    if errors:
        return errors, warnings
    # JSON Schema const compares numbers numerically. The version is an integer contract.
    if type(source["schema_version"]) is not int:
        errors.append("schema_version must be an integer")
    for collection, id_field in (("subjects", "subject_id"), ("assets", "asset_id"), ("references", "reference_id")):
        ids = [entry[id_field] for entry in source[collection]]
        if len(ids) != len(set(ids)):
            errors.append(f"Duplicate {id_field}")
    subjects = {item["subject_id"]: item for item in source["subjects"]}
    references = {item["reference_id"]: item for item in source["references"]}

    def check_refs(ids: list[str], private: bool, owner: str, identity: bool = False) -> None:
        for reference_id in ids:
            ref = references.get(reference_id)
            if ref is None:
                errors.append(f"{owner}: unknown reference {reference_id}")
            elif not private and ref["gm_only"]:
                errors.append(f"{owner}: public consumer requires private reference {reference_id}")
            elif identity and ref["role"] not in ("identity", "edit_target"):
                errors.append(f"{owner}: identity reference has role {ref['role']}")

    for subject in source["subjects"]:
        check_refs(subject["identity_reference_ids"], subject["gm_only"], subject["subject_id"], True)
        anatomy = [entry["feature"].strip().casefold() for entry in subject["visible_identity"]["anatomy"]]
        if len(anatomy) != len(set(anatomy)):
            errors.append(f"{subject['subject_id']}: duplicate anatomy feature")
    for ref in references.values():
        if ref["inspection"] != "inspected":
            if ref["use"] or ref["ignore"] or ref["approved_identity"]:
                errors.append(f"{ref['reference_id']}: uninspected reference has traits or identity approval")
            warnings.append(f"{ref['reference_id']}: reference {ref['inspection']}")
        if ref["approved_identity"] and ref["role"] not in ("identity", "edit_target"):
            errors.append(f"{ref['reference_id']}: identity approval requires identity or edit_target role")
    for asset in source["assets"]:
        subject = subjects.get(asset["subject_id"])
        if subject is None:
            errors.append(f"{asset['asset_id']}: unknown subject {asset['subject_id']}")
            continue
        private = asset["gm_only"] or subject["gm_only"]
        check_refs(asset["reference_ids"], private, asset["asset_id"])
        target = asset["edit_target_ref"]
        if asset["intent"] == "edit" and target is None:
            errors.append(f"{asset['asset_id']}: edit intent requires edit_target_ref")
        if asset["intent"] == "generate" and target is not None:
            errors.append(f"{asset['asset_id']}: generate intent cannot have an edit target")
        if target is not None:
            check_refs([target], private, asset["asset_id"])
            if target in references and references[target]["role"] != "edit_target":
                errors.append(f"{asset['asset_id']}: edit target must have edit_target role")
        output = asset["output"]
        width, height, ratio = output["width_px"], output["height_px"], output["aspect_ratio"]
        if (width is None) != (height is None):
            errors.append(f"{asset['asset_id']}: specify both output dimensions or neither")
        if width is not None and height is not None and ratio and width * ratio[1] != height * ratio[0]:
            errors.append(f"{asset['asset_id']}: dimensions conflict with aspect_ratio")
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
    identity, presentation = brief["identity"], brief["presentation"]
    lines = [f"Asset: {brief['title']} - {presentation['framing']} character or creature portrait.",
             f"Intended use: {brief['intended_use']}", f"Subject: {brief['subject_name']}"]
    for field, value in identity.items():
        if value not in (None, "", []):
            lines.append(f"Visible identity / {field}: {json.dumps(value, ensure_ascii=False)}")
    for field in ("viewpoint", "pose", "expression", "background", "output", "constraints"):
        value = presentation[field]
        if value not in (None, "", []):
            lines.append(f"{field}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("Art direction: " + json.dumps(brief["art_direction"], ensure_ascii=False))
    if brief["intent"] == "edit":
        lines.append("Edit the supplied target. Apply only the requested change; preserve all other approved visible features.")
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
        visible_refs, unresolved = [], []
        for reference_id in used:
            ref = references[reference_id]
            if ref["inspection"] != "inspected":
                unresolved.append(reference_id)
            else:
                visible_refs.append({field: copy.deepcopy(ref[field]) for field in ("reference_id", "locator", "role", "use", "ignore", "approved_identity")})
        identity = copy.deepcopy(subject["visible_identity"])
        identity.update(copy.deepcopy(asset.get("wardrobe", {})))
        issues = [f"Reference {item} has not been inspected and supplied" for item in unresolved]
        if not identity["form"].strip():
            issues.append("Subject form is unspecified")
        if not identity["face_head"].strip() and not identity["anatomy"]:
            issues.append("Subject head/body appearance or anatomy is unspecified")
        if not asset["intended_use"].strip():
            issues.append("Intended display is unspecified")
        brief = {
            "asset_id": asset["asset_id"], "subject_id": subject["subject_id"],
            "title": asset["title"], "subject_name": subject["name"],
            "intended_use": asset["intended_use"], "intent": asset["intent"],
            "identity": copy.deepcopy(identity),
            "presentation": {field: copy.deepcopy(asset[field]) for field in ("framing", "viewpoint", "pose", "expression", "background", "output", "constraints")},
            "art_direction": copy.deepcopy(asset["art_direction"]),
            "references": visible_refs, "edit_target_ref": asset["edit_target_ref"],
            "unresolved_reference_ids": unresolved, "readiness_issues": issues, "render_ready": not issues,
        }
        brief["image_instructions"] = prompt_for(brief)
        briefs.append(brief)
    if not briefs:
        raise ValueError("No selected portraits are visible to this audience")
    return {"schema_version": 1, "source_id": source["spec_id"], "source_revision": source["revision"],
            "source_sha256": hashlib.sha256(canonical(source).encode()).hexdigest(), "audience": audience, "briefs": briefs}


def revise(source: Any, change: Any, allow_locked: list[str] | None = None) -> dict[str, Any]:
    require_valid(source)
    if not isinstance(change, dict) or set(change) != {"expected_revision", "changes"}:
        raise ValueError("Change file requires only expected_revision and changes")
    if type(change["expected_revision"]) is not int or change["expected_revision"] != source["revision"]:
        raise ValueError("Stale or invalid expected_revision")
    changes = change["changes"]
    if not isinstance(changes, list) or not changes:
        raise ValueError("changes must be a nonempty replacement list")
    allowed = set(allow_locked or [])
    if not allowed.issubset(source["locks"]):
        raise ValueError("--allow-locked must name exact existing locks")
    result = copy.deepcopy(source)
    paths: list[list[str]] = []
    for entry in changes:
        if not isinstance(entry, dict) or set(entry) != {"path", "value"} or not isinstance(entry["path"], str):
            raise ValueError("Each change requires only a string path and value")
        tokens = parts(entry["path"])
        if tokens[0] in ("schema_version", "spec_id", "revision", "locks"):
            raise ValueError("Source identity, revision, and lock definitions require a master edit")
        if any(tokens[:len(other)] == other or other[:len(tokens)] == tokens for other in paths):
            raise ValueError("Overlapping change paths")
        paths.append(tokens)
        parent = result
        for token in tokens[:-1]:
            parent = parent[key(parent, token)]
        parent[key(parent, tokens[-1])] = copy.deepcopy(entry["value"])
    for lock in source["locks"]:
        if lock not in allowed:
            try:
                same = canonical(pointer_value(source, lock)) == canonical(pointer_value(result, lock))
            except ValueError:
                same = False
            if not same:
                raise ValueError(f"Locked field changed: {lock}")
    for collection, id_field in (("subjects", "subject_id"), ("assets", "asset_id"), ("references", "reference_id")):
        before = [entry[id_field] for entry in source[collection]]
        after = [entry.get(id_field) for entry in result[collection]] if isinstance(result[collection], list) and all(isinstance(item, dict) for item in result[collection]) else []
        if after[:len(before)] != before:
            raise ValueError(f"Existing {id_field} positions cannot change")
    for before, after in zip(source["assets"], result["assets"]):
        if before["subject_id"] != after.get("subject_id"):
            raise ValueError("Existing assets cannot be rebound to another subject")
    if canonical(result) == canonical(source):
        raise ValueError("No source change; revision was not incremented")
    result["revision"] += 1
    require_valid(result)
    return result


def handoff(source: Any, asset_id: str, approved_image: str) -> dict[str, Any]:
    compiled = compile_source(source, "player", asset_id)
    brief = compiled["briefs"][0]
    if not brief["render_ready"]:
        raise ValueError("Cannot hand off an incomplete portrait brief")
    path = Path(approved_image).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Approved image must be an existing nonempty local file")
    return {"subject_id": brief["subject_id"], "asset_id": asset_id, "source_revision": compiled["source_revision"],
            "source_sha256": compiled["source_sha256"], "approved_image": str(path),
            "identity": brief["identity"], "art_direction": brief["art_direction"],
            "references": [ref for ref in brief["references"] if ref["role"] == "style" or (ref["approved_identity"] and ref["role"] in ("identity", "edit_target"))],
            "approval_basis": "Caller asserts prior user approval; receiving workflow must inspect the image",
            "token_status": "not_created", "atlas_status": "not_imported"}


def inspect_image(path: str) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as image:
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        alpha = image.convert("RGBA").getchannel("A")
        histogram = alpha.histogram()
        pixels = image.width * image.height
        return {"file": str(Path(path).resolve()), "format": image.format, "width_px": image.width,
                "height_px": image.height, "has_alpha": has_alpha, "alpha_extrema": list(alpha.getextrema()),
                "has_transparent_pixels": sum(histogram[:255]) > 0,
                "nonopaque_pixel_fraction": sum(histogram[:255]) / pixels,
                "visual_review": "not_run", "identity_approval": "not_verified"}


def write_output(value: Any, path: str | None, inputs: list[str], text: bool = False) -> None:
    content = value if text else json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
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
    for name in ("validate", "compile", "revise", "handoff"):
        command = commands.add_parser(name)
        command.add_argument("source")
        command.add_argument("-o", "--output")
        if name == "compile":
            command.add_argument("--audience", choices=("player", "gm"), default="player")
            command.add_argument("--asset")
            command.add_argument("--text", action="store_true")
        elif name == "revise":
            command.add_argument("change")
            command.add_argument("--allow-locked", action="append", default=[])
        elif name == "handoff":
            command.add_argument("--asset", required=True)
            command.add_argument("--approved-image", required=True)
    metadata = commands.add_parser("inspect-image")
    metadata.add_argument("image")
    metadata.add_argument("-o", "--output")
    args = parser.parse_args()
    try:
        inputs = [args.image] if args.command == "inspect-image" else [args.source]
        text = False
        if args.command == "inspect-image":
            result = inspect_image(args.image)
        else:
            source = load_json(args.source)
            if args.command == "validate":
                errors, warnings = validate(source)
                result = {"valid": not errors, "errors": errors, "warnings": warnings}
                write_output(result, args.output, inputs)
                return int(bool(errors))
            if args.command == "compile":
                result = compile_source(source, args.audience, args.asset)
                if args.text:
                    if len(result["briefs"]) != 1 or not result["briefs"][0]["render_ready"]:
                        raise ValueError("Text output requires exactly one ready visible portrait")
                    result = result["briefs"][0]["image_instructions"]
                    text = True
            elif args.command == "revise":
                inputs.append(args.change)
                result = revise(source, load_json(args.change), args.allow_locked)
            elif args.command == "handoff":
                inputs.append(args.approved_image)
                result = handoff(source, args.asset, args.approved_image)
        write_output(result, args.output, inputs, text)
        return 0
    except (ValueError, OSError, ImportError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
