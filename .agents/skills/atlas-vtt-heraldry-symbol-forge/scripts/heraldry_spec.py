"""Validate heraldry authoring data, filter briefs, and apply narrow revisions."""

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
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


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


def parts(pointer: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ValueError(f"Invalid nonroot JSON Pointer: {pointer}")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


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


def overlaps(left: str, right: str) -> bool:
    a, b = parts(left), parts(right)
    return a[:len(b)] == b or b[:len(a)] == a


def validate(source: Any) -> tuple[list[str], list[str]]:
    from jsonschema import Draft202012Validator

    schema = load_json(ROOT / "schemas/heraldry-spec.schema.json")
    failures = sorted(Draft202012Validator(schema).iter_errors(source), key=lambda error: str(error.path))
    errors = [f"/{'/'.join(map(str, error.path))}: {error.message}" for error in failures]
    warnings: list[str] = []
    if errors:
        return errors, warnings
    for name in ("schema_version", "revision"):
        if type(source[name]) is not int:
            errors.append(f"{name} must be an integer")
    for collection, id_field in (("factions", "faction_id"), ("assets", "asset_id"), ("references", "reference_id")):
        ids = [record[id_field] for record in source[collection]]
        if len(ids) != len(set(ids)):
            errors.append(f"Duplicate {id_field}")
    factions = {item["faction_id"]: item for item in source["factions"]}
    assets = {item["asset_id"]: item for item in source["assets"]}
    refs = {item["reference_id"]: item for item in source["references"]}

    def check_refs(ids: list[str], private: bool, owner: str) -> None:
        for ref_id in ids:
            ref = refs.get(ref_id)
            if ref is None:
                errors.append(f"{owner}: unknown reference {ref_id}")
            elif not private and ref["gm_only"]:
                errors.append(f"{owner}: public consumer requires private reference {ref_id}")

    for ref in source["references"]:
        if ref["inspection"] != "inspected":
            if ref["use"] or ref["ignore"] or ref["approval"] == "user_approved":
                errors.append(f"{ref['reference_id']}: uninspected reference asserts traits or approval")
            warnings.append(f"{ref['reference_id']}: reference {ref['inspection']}")
    for faction in source["factions"]:
        check_refs(faction["reference_ids"], faction["gm_only"], faction["faction_id"])
        emblem_id = faction["emblem_reference_id"]
        if emblem_id is not None:
            check_refs([emblem_id], faction["gm_only"], faction["faction_id"])
            if emblem_id in refs and (refs[emblem_id]["role"] != "emblem" or refs[emblem_id]["inspection"] != "inspected"):
                errors.append(f"{faction['faction_id']}: canonical emblem requires an inspected emblem reference")
            if emblem_id in refs and refs[emblem_id]["approval"] == "rejected":
                errors.append(f"{faction['faction_id']}: rejected reference cannot be the canonical emblem")
        anchor_id = faction["consistency_anchor_asset_id"]
        if anchor_id is not None:
            anchor = assets.get(anchor_id)
            if anchor is None or anchor["faction_id"] != faction["faction_id"]:
                errors.append(f"{faction['faction_id']}: anchor must belong to the faction")
            elif not faction["gm_only"] and anchor["gm_only"]:
                errors.append(f"{faction['faction_id']}: public faction requires a private anchor")
    for asset in source["assets"]:
        faction = factions.get(asset["faction_id"])
        if faction is None:
            errors.append(f"{asset['asset_id']}: unknown faction")
            continue
        private = asset["gm_only"] or faction["gm_only"]
        check_refs(asset["reference_ids"], private, asset["asset_id"])
        target = asset["edit_target_ref"]
        if (asset["intent"] == "edit") != (target is not None):
            errors.append(f"{asset['asset_id']}: edit intent requires a target; generation cannot have one")
        if target is not None:
            check_refs([target], private, asset["asset_id"])
            if target in refs and refs[target]["role"] != "edit_target":
                errors.append(f"{asset['asset_id']}: target requires edit_target role")
        output = asset["output"]
        width, height, ratio = output["width_px"], output["height_px"], output["aspect_ratio"]
        if (width is None) != (height is None):
            errors.append(f"{asset['asset_id']}: specify both output dimensions or neither")
        if width is not None and height is not None and ratio and width * ratio[1] != height * ratio[0]:
            errors.append(f"{asset['asset_id']}: dimensions conflict with aspect_ratio")
        lettering = asset["lettering"]
        if lettering["mode"] == "none" and lettering["wording"]:
            errors.append(f"{asset['asset_id']}: no-text mode cannot discard wording")
        if lettering["mode"] != "none" and (not lettering["wording"].strip() or not lettering["placement"].strip()):
            errors.append(f"{asset['asset_id']}: requested lettering requires wording and placement")
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
    lines = [f"Asset: {brief['title']} - {brief['kind']}.", f"Faction: {brief['faction_name']}",
             f"Intended use: {brief['intended_use']}"]
    for field, value in brief["identity"].items():
        if value not in ("", []):
            lines.append(f"Shared identity / {field}: {json.dumps(value, ensure_ascii=False)}")
    for field in ("carrier", "background", "output", "art_direction", "constraints"):
        lines.append(f"{field}: {json.dumps(brief[field], ensure_ascii=False)}")
    if brief["emblem_reference_id"]:
        lines.append("Reuse the supplied canonical emblem. Adapt the carrier and material while preserving motif, silhouette, and arrangement.")
    if brief["intent"] == "edit":
        lines.append("Edit the supplied target only within the requested scope; preserve all other identity and carrier details.")
    lettering = brief["lettering"]
    if lettering["mode"] == "none":
        lines.append("No lettering, captions, labels, or interface elements.")
    elif lettering["mode"] == "raster_verify":
        lines.append(f"Exact lettering to render and verify: {json.dumps(lettering['wording'], ensure_ascii=False)}. Placement: {lettering['placement']}")
    else:
        lines.append(f"Reserve an empty lettering area for later deterministic composition: {lettering['placement']}. Leave it blank; no generated lettering.")
    for ref in brief["references"]:
        lines.append(f"Reference {ref['reference_id']} ({ref['role']}): use {json.dumps(ref['use'], ensure_ascii=False)}; ignore {json.dumps(ref['ignore'], ensure_ascii=False)}.")
    return "\n".join(lines)


def compile_source(source: Any, audience: str = "player", asset_id: str | None = None) -> dict[str, Any]:
    require_valid(source)
    if audience not in ("player", "gm"):
        raise ValueError("Audience must be player or gm")
    factions = {item["faction_id"]: item for item in source["factions"]}
    refs = {item["reference_id"]: item for item in source["references"]}
    briefs = []
    for asset in source["assets"]:
        faction = factions[asset["faction_id"]]
        if asset_id is not None and asset["asset_id"] != asset_id:
            continue
        if audience == "player" and (asset["gm_only"] or faction["gm_only"]):
            continue
        emblem_id, anchor_id = faction["emblem_reference_id"], faction["consistency_anchor_asset_id"]
        used = list(dict.fromkeys(faction["reference_ids"] + asset["reference_ids"]
                                 + ([emblem_id] if emblem_id else [])
                                 + ([asset["edit_target_ref"]] if asset["edit_target_ref"] else [])))
        visible_refs, unresolved = [], []
        for ref_id in used:
            ref = refs[ref_id]
            if ref["inspection"] == "inspected":
                visible_refs.append({field: copy.deepcopy(ref[field]) for field in
                                     ("reference_id", "locator", "role", "approval", "use", "ignore")})
            else:
                unresolved.append(ref_id)
        dependency = anchor_id if anchor_id != asset["asset_id"] and not emblem_id else None
        issues = [f"Reference {ref_id} has not been inspected and supplied" for ref_id in unresolved]
        if dependency:
            issues.append(f"Requires inspected canonical emblem from asset {dependency}")
        member_count = sum(a["faction_id"] == faction["faction_id"] and (audience == "gm" or not a["gm_only"])
                           for a in source["assets"])
        if member_count > 1 and not anchor_id and not emblem_id:
            issues.append("Coherent set requires a canonical emblem reference or a consistency anchor")
        for field in ("motif", "silhouette", "arrangement"):
            if not faction["identity"][field].strip():
                issues.append(f"Identity {field} is unspecified")
        if not faction["identity"]["palette"]:
            issues.append("Identity palette roles are unspecified")
        for field in ("intended_use",):
            if not asset[field].strip():
                issues.append(f"{field} is unspecified")
        if not asset["carrier"]["material"].strip() or not asset["carrier"]["shape"].strip():
            issues.append("Carrier material or shape is unspecified")
        if asset["background"]["mode"] == "unspecified":
            issues.append("Background treatment is unspecified")
        brief = {"asset_id": asset["asset_id"], "faction_id": faction["faction_id"],
                 "faction_name": faction["name"], "identity": copy.deepcopy(faction["identity"]),
                 **{field: copy.deepcopy(asset[field]) for field in
                    ("title", "intended_use", "kind", "intent", "carrier", "background", "output", "lettering", "art_direction", "constraints", "edit_target_ref")},
                 "emblem_reference_id": emblem_id, "dependency_asset_id": dependency,
                 "references": visible_refs, "unresolved_reference_ids": unresolved,
                 "readiness_issues": issues, "render_ready": not issues}
        brief["image_instructions"] = prompt_for(brief)
        briefs.append(brief)
    if not briefs:
        raise ValueError("No selected heraldry assets are visible to this audience")
    return {"schema_version": 1, "source_id": source["spec_id"], "source_revision": source["revision"],
            "source_sha256": hashlib.sha256(canonical(source).encode()).hexdigest(),
            "audience": audience, "briefs": briefs, "image": "not_generated", "atlas": "not_imported"}


def identity_signature(source: Any) -> dict[str, Any]:
    return {"schema_version": source["schema_version"], "spec_id": source["spec_id"], "revision": source["revision"],
            "locks": source["locks"], "factions": [f["faction_id"] for f in source["factions"]],
            "assets": [(a["asset_id"], a["faction_id"]) for a in source["assets"]],
            "references": [r["reference_id"] for r in source["references"]]}


def revise(source: Any, change: Any, allow_locked: list[str] | None = None) -> dict[str, Any]:
    require_valid(source)
    if not isinstance(change, dict) or set(change) != {"expected_revision", "changes"}:
        raise ValueError("Change file requires only expected_revision and changes")
    if type(change["expected_revision"]) is not int or change["expected_revision"] != source["revision"]:
        raise ValueError("Stale or invalid expected_revision")
    if not isinstance(change["changes"], list) or not change["changes"]:
        raise ValueError("changes must be a nonempty replacement list")
    allowed = set(allow_locked or [])
    if not allowed.issubset(source["locks"]):
        raise ValueError("--allow-locked must name exact existing locks")
    result: dict[str, Any] = copy.deepcopy(source)
    paths: list[str] = []
    for entry in change["changes"]:
        if not isinstance(entry, dict) or set(entry) != {"path", "value"}:
            raise ValueError("Each change requires only path and value")
        path = entry["path"]
        tokens = parts(path)
        if any(overlaps(path, previous) for previous in paths):
            raise ValueError("Duplicate or overlapping change paths")
        paths.append(path)
        blocked = [lock for lock in source["locks"] if overlaps(path, lock) and lock not in allowed]
        if blocked:
            raise ValueError("Locked field: " + ", ".join(blocked))
        parent: Any = result
        for token in tokens[:-1]:
            parent = parent[key(parent, token)]
        parent[key(parent, tokens[-1])] = copy.deepcopy(entry["value"])
    try:
        if identity_signature(result) != identity_signature(source):
            raise ValueError("Managed fields, IDs, collection order, and faction bindings must remain unchanged")
    except (KeyError, TypeError) as error:
        raise ValueError("Managed fields and collection identities must remain unchanged") from error
    result["revision"] += 1
    require_valid(result)
    return result


def inspect_image(path: str | Path) -> dict[str, Any]:
    from PIL import Image

    with Image.open(path) as img:
        img.load()
        alpha = img.convert("RGBA").getchannel("A")
        histogram = alpha.histogram()
        return {"file": str(Path(path).resolve()), "width_px": img.width, "height_px": img.height,
                "alpha_channel": "A" in img.getbands() or "transparency" in img.info,
                "alpha_min": alpha.getextrema()[0], "alpha_max": alpha.getextrema()[1],
                "transparent_pixels": histogram[0], "partial_alpha_pixels": sum(histogram[1:255]),
                "total_pixels": img.width * img.height, "visual_review": "not_run"}


def write_output(value: Any, output: str | None, plain: bool = False) -> None:
    rendered = value if plain else json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    if output:
        with Path(output).open("x") as stream:
            stream.write(rendered + "\n")
    else:
        print(rendered)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    valid = commands.add_parser("validate")
    valid.add_argument("source")
    compile_cmd = commands.add_parser("compile")
    compile_cmd.add_argument("source")
    compile_cmd.add_argument("--audience", choices=("player", "gm"), default="player")
    compile_cmd.add_argument("--asset")
    compile_cmd.add_argument("--text", action="store_true")
    compile_cmd.add_argument("-o", "--output")
    revision = commands.add_parser("revise")
    revision.add_argument("source")
    revision.add_argument("change")
    revision.add_argument("--allow-locked", action="append", default=[])
    revision.add_argument("-o", "--output", required=True)
    inspect = commands.add_parser("inspect-image")
    inspect.add_argument("image")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            errors, warnings = validate(load_json(args.source))
            write_output({"valid": not errors, "errors": errors, "warnings": warnings}, None)
            return 1 if errors else 0
        if args.command == "compile":
            result = compile_source(load_json(args.source), args.audience, args.asset)
            if args.text:
                if len(result["briefs"]) != 1:
                    raise ValueError("--text requires exactly one visible asset; select --asset")
                if not result["briefs"][0]["render_ready"]:
                    raise ValueError("--text requires a render-ready brief; resolve its missing fields, references, or anchor first")
                write_output(result["briefs"][0]["image_instructions"], args.output, True)
            else:
                write_output(result, args.output)
        elif args.command == "revise":
            result = revise(load_json(args.source), load_json(args.change), args.allow_locked)
            write_output(result, args.output)
        else:
            write_output(inspect_image(args.image), None)
        return 0
    except (OSError, ValueError, ImportError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
