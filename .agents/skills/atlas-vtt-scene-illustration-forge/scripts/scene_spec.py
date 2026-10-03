"""Validate scene authoring sources, filter briefs, and apply guarded revisions.

No rendering, reference downloads, pixel edits, or native Atlas writes.
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
COLLECTIONS = (("locations", "location_id"), ("assets", "asset_id"), ("references", "reference_id"))


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def read_json(path: str | Path) -> Any:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise ValueError(f"Duplicate JSON key: {name}")
            result[name] = value
        return result

    def finite(value: str) -> None:
        raise ValueError(f"Nonfinite JSON value: {value}")

    return json.loads(Path(path).read_text(), object_pairs_hook=unique_pairs, parse_constant=finite)


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


def at(source: Any, pointer: str) -> Any:
    value = source
    for token in tokens(pointer):
        value = value[index(value, token)]
    return value


def validate(source: Any) -> list[str]:
    from jsonschema import Draft202012Validator

    schema = read_json(ROOT / "schemas/scene-spec.schema.json")
    failures = sorted(Draft202012Validator(schema).iter_errors(source), key=lambda error: str(error.path))
    errors = [f"/{'/'.join(map(str, error.path))}: {error.message}" for error in failures]
    if errors:
        return errors
    for name in ("schema_version", "revision"):
        if type(source[name]) is not int:
            errors.append(f"{name} must be a JSON integer")
    for collection, id_name in COLLECTIONS:
        values = [entry[id_name] for entry in source[collection]]
        if len(values) != len(set(values)):
            errors.append(f"Duplicate {id_name}")
    locations = {entry["location_id"]: entry for entry in source["locations"]}
    references = {entry["reference_id"]: entry for entry in source["references"]}

    def check_refs(ids: list[str], private: bool, owner: str, identity: bool = False) -> None:
        for ref_id in ids:
            ref = references.get(ref_id)
            if ref is None:
                errors.append(f"{owner}: unknown reference {ref_id}")
            elif not private and ref["gm_only"]:
                errors.append(f"{owner}: public consumer requires private reference {ref_id}")
            elif identity and ref["role"] not in ("location_identity", "edit_target"):
                errors.append(f"{owner}: location identity requires location_identity or edit_target role")

    for location in locations.values():
        check_refs(location["identity_reference_ids"], location["gm_only"], location["location_id"], True)
    for ref in references.values():
        if ref["inspection"] != "inspected" and (ref["use"] or ref["ignore"]):
            errors.append(f"{ref['reference_id']}: uninspected reference cannot assert observed traits")
    for asset in source["assets"]:
        location = locations.get(asset["location_id"])
        if location is None:
            errors.append(f"{asset['asset_id']}: unknown location {asset['location_id']}")
            continue
        private = asset["gm_only"] or location["gm_only"]
        check_refs(asset["reference_ids"], private, asset["asset_id"])
        target = asset["edit_target_ref"]
        if asset["intent"] == "edit":
            if target is None or asset["edit_scope"] is None or not asset["edit_scope"]["change"].strip():
                errors.append(f"{asset['asset_id']}: edit requires a target and a nonempty edit_scope.change")
        elif target is not None or asset["edit_scope"] is not None:
            errors.append(f"{asset['asset_id']}: generate intent cannot have edit inputs")
        if target is not None:
            check_refs([target], private, asset["asset_id"])
            if target in references and references[target]["role"] != "edit_target":
                errors.append(f"{asset['asset_id']}: target requires edit_target role")
        output = asset["output"]
        width, height, ratio = output["width_px"], output["height_px"], output["aspect_ratio"]
        if (width is None) != (height is None):
            errors.append(f"{asset['asset_id']}: specify both dimensions or neither")
        if width is not None and height is not None and ratio and width * ratio[1] != height * ratio[0]:
            errors.append(f"{asset['asset_id']}: dimensions conflict with aspect ratio")
    for lock in source["locks"]:
        if lock == "/revision":
            errors.append("Revision is managed and cannot be locked")
        try:
            at(source, lock)
        except ValueError as error:
            errors.append(f"Lock {lock}: {error}")
    return errors


def require_valid(source: Any) -> None:
    errors = validate(source)
    if errors:
        raise ValueError("Invalid source: " + "; ".join(errors))


def image_prompt(brief: dict[str, Any]) -> str:
    lines = [f"Illustration: {brief['title']} ({brief['kind']}).",
             f"Intended use: {brief['intended_use']}",
             "Location identity: " + json.dumps(brief["location"], ensure_ascii=False)]
    for field in ("moment", "visible_changes", "composition", "atmosphere", "art_direction",
                  "background", "output", "lettering", "constraints"):
        value = brief[field]
        if value not in (None, "", []):
            lines.append(f"{field}: {json.dumps(value, ensure_ascii=False)}")
    if brief["intent"] == "edit":
        lines.append("Edit the supplied target; preserve unspecified visible features.")
        lines.append("Edit scope: " + json.dumps(brief["edit_scope"], ensure_ascii=False))
    for ref in brief["references"]:
        lines.append(f"Reference {ref['reference_id']} ({ref['role']}): "
                     f"use {json.dumps(ref['use'], ensure_ascii=False)}; "
                     f"ignore {json.dumps(ref['ignore'], ensure_ascii=False)}.")
    return "\n".join(lines)


def compile_source(source: Any, audience: str = "player", asset_id: str | None = None) -> dict[str, Any]:
    require_valid(source)
    if audience not in ("player", "gm"):
        raise ValueError("Audience must be player or gm")
    locations = {entry["location_id"]: entry for entry in source["locations"]}
    references = {entry["reference_id"]: entry for entry in source["references"]}
    briefs = []
    for asset in source["assets"]:
        location = locations[asset["location_id"]]
        if audience == "player" and (asset["gm_only"] or location["gm_only"]):
            continue
        if asset_id is not None and asset["asset_id"] != asset_id:
            continue
        brief = {name: copy.deepcopy(value) for name, value in asset.items()
                 if name not in ("gm_only", "reference_ids")}
        brief["location"] = {name: copy.deepcopy(location[name])
                             for name in ("location_id", "name", "description", "architecture", "landmarks")}
        ids = list(dict.fromkeys(location["identity_reference_ids"] + asset["reference_ids"] +
                                 ([asset["edit_target_ref"]] if asset["edit_target_ref"] else [])))
        brief["references"] = [{name: copy.deepcopy(value) for name, value in references[ref_id].items()
                                if name != "gm_only"}
                               for ref_id in ids if references[ref_id]["inspection"] == "inspected"]
        unresolved = [ref_id for ref_id in ids if references[ref_id]["inspection"] != "inspected"]
        issues = [f"Required reference {ref_id} is not inspected and available" for ref_id in unresolved]
        for name, value in (("location description", location["description"]),
                            ("viewpoint", asset["composition"]["viewpoint"]),
                            ("focal point", asset["composition"]["focal_point"]),
                            ("intended use", asset["intended_use"])):
            if not value.strip():
                issues.append(f"Missing {name}")
        if asset["kind"] == "dramatic_scene" and not asset["moment"].strip():
            issues.append("Missing visible dramatic moment")
        brief["unresolved_reference_ids"] = unresolved
        brief["readiness_issues"] = issues
        brief["render_ready"] = not issues
        brief["image_prompt"] = image_prompt(brief)
        briefs.append(brief)
    if asset_id is not None and not briefs:
        raise ValueError(f"Asset unavailable to {audience} audience: {asset_id}")
    return {"spec_id": source["spec_id"], "source_revision": source["revision"],
            "source_sha256": hashlib.sha256(canonical(source).encode()).hexdigest(),
            "audience": audience, "briefs": briefs}


def revise(source: Any, change: Any, allowed_locks: tuple[str, ...] = ()) -> dict[str, Any]:
    require_valid(source)
    if not isinstance(change, dict) or set(change) != {"expected_revision", "changes"}:
        raise ValueError("Change requires only expected_revision and changes")
    if type(change["expected_revision"]) is not int or change["expected_revision"] != source["revision"]:
        raise ValueError("Stale or invalid expected revision")
    changes = change["changes"]
    if not isinstance(changes, list) or not changes:
        raise ValueError("Changes must be a nonempty array")
    if any(path not in source["locks"] for path in allowed_locks):
        raise ValueError("allow-locked must name an exact existing lock")
    result = copy.deepcopy(source)
    paths: list[list[str]] = []
    for entry in changes:
        if not isinstance(entry, dict) or set(entry) != {"path", "value"}:
            raise ValueError("Each change requires only path and value")
        path = entry["path"]
        if not isinstance(path, str):
            raise TypeError("Change path must be a JSON Pointer string")
        parts = tokens(path)
        if parts[0] in ("schema_version", "spec_id", "revision", "locks"):
            raise ValueError(f"Managed source field: {path}")
        if any(parts[:len(prior)] == prior or prior[:len(parts)] == parts for prior in paths):
            raise ValueError("Overlapping change paths")
        paths.append(parts)
        container = result
        for token in parts[:-1]:
            container = container[index(container, token)]
        container[index(container, parts[-1])] = copy.deepcopy(entry["value"])
    for collection, id_name in COLLECTIONS:
        old = source[collection]
        new = result.get(collection)
        if not isinstance(new, list) or len(new) < len(old):
            raise ValueError(f"Existing {collection} cannot be removed")
        for before, after in zip(old, new):
            if not isinstance(after, dict) or after.get(id_name) != before[id_name]:
                raise ValueError(f"Existing {id_name} and order must be preserved")
            if collection == "assets" and after.get("location_id") != before["location_id"]:
                raise ValueError("Existing asset location binding must be preserved")
    for lock in source["locks"]:
        if lock not in allowed_locks and canonical(at(source, lock)) != canonical(at(result, lock)):
            raise ValueError(f"Locked field changed: {lock}")
    result["revision"] += 1
    require_valid(result)
    return result


def write_result(value: Any, output: str | None, inputs: tuple[str, ...], text_only: bool = False) -> None:
    rendered = value if text_only else json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
    if output is None:
        print(rendered)
        return
    path = Path(output)
    if any(path.resolve() == Path(source).resolve() for source in inputs):
        raise ValueError("Refusing to overwrite an input")
    with path.open("x") as handle:
        handle.write(rendered + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate")
    check.add_argument("source")
    build = commands.add_parser("compile")
    build.add_argument("source")
    build.add_argument("--audience", choices=("player", "gm"), default="player")
    build.add_argument("--asset")
    build.add_argument("--text", action="store_true")
    build.add_argument("-o", "--output")
    edit = commands.add_parser("revise")
    edit.add_argument("source")
    edit.add_argument("change")
    edit.add_argument("--allow-locked", action="append", default=[])
    edit.add_argument("-o", "--output", required=True)
    args = parser.parse_args()
    try:
        source = read_json(args.source)
        if args.command == "validate":
            errors = validate(source)
            print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
            return 1 if errors else 0
        if args.command == "revise":
            result = revise(source, read_json(args.change), tuple(args.allow_locked))
            write_result(result, args.output, (args.source, args.change))
        else:
            result = compile_source(source, args.audience, args.asset)
            if args.text:
                if len(result["briefs"]) != 1 or not result["briefs"][0]["render_ready"]:
                    raise ValueError("Text output requires exactly one ready brief")
                result = result["briefs"][0]["image_prompt"]
            write_result(result, args.output, (args.source,), args.text)
        return 0
    except (ValueError, OSError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
