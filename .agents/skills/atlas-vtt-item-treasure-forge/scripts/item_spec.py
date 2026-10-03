"""Validate, filter, and revise item illustration sources; performs no rendering."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
Json = dict[str, Any]


class SpecError(ValueError):
    """An invalid source or unsafe derived operation."""


def tokens(pointer: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/") or pointer == "/":
        raise SpecError("Use a nonroot JSON Pointer path.")
    parts = pointer[1:].split("/")
    if any(re.search(r"~(?![01])", part) for part in parts):
        raise SpecError(f"Invalid JSON Pointer escape: {pointer}")
    return [part.replace("~1", "/").replace("~0", "~") for part in parts]


def child(value: Any, key: str) -> Any:
    if isinstance(value, list):
        if not re.fullmatch(r"0|[1-9][0-9]*", key) or int(key) >= len(value):
            raise SpecError(f"Unknown array index: {key}")
        return value[int(key)]
    if isinstance(value, dict) and key in value:
        return value[key]
    raise SpecError(f"Unknown path component: {key}")


def get(source: Json, pointer: str) -> Any:
    value: Any = source
    for key in tokens(pointer):
        value = child(value, key)
    return value


def replace(source: Json, pointer: str, value: Any) -> None:
    parts = tokens(pointer)
    parent: Any = source
    for key in parts[:-1]:
        parent = child(parent, key)
    child(parent, parts[-1])
    if isinstance(parent, list):
        parent[int(parts[-1])] = deepcopy(value)
    else:
        parent[parts[-1]] = deepcopy(value)


def unique(records: list[Json], key: str) -> dict[str, Json]:
    result: dict[str, Json] = {}
    for record in records:
        identifier = record[key]
        if identifier in result:
            raise SpecError(f"Duplicate {key}: {identifier}")
        result[identifier] = record
    return result


def validate(source: Json) -> None:
    schema = json.loads((ROOT / "schemas/item-spec.schema.json").read_text())
    errors = list(Draft202012Validator(schema).iter_errors(source))
    if errors:
        error = errors[0]
        path = "/" + "/".join(map(str, error.absolute_path))
        raise SpecError(f"{path}: {error.message}")
    items = unique(source["items"], "item_id")
    unique(source["assets"], "asset_id")
    references = unique(source["references"], "reference_id")
    for item in items.values():
        unique(item["inscriptions"], "inscription_id")
        for inscription in item["inscriptions"]:
            if not inscription["text"].strip() or not inscription["placement"].strip():
                raise SpecError("An inscription needs content and a placement.")
    for reference in references.values():
        if reference["inspection"] != "inspected" and (
            reference["use"] or reference["ignore"]
        ):
            raise SpecError(
                "Uninspected references cannot assert visual use/ignore traits."
            )
    for asset in source["assets"]:
        for identifier in asset["item_ids"]:
            if identifier not in items:
                raise SpecError(f"Unknown item: {identifier}")
            if items[identifier]["gm_only"] and not asset["gm_only"]:
                raise SpecError("A public asset cannot contain a private item.")
        required_refs = list(asset["reference_ids"])
        target = asset["edit_target_ref"]
        if asset["intent"] == "edit" and target is None:
            raise SpecError("An edit requires an actual edit-target reference.")
        if asset["intent"] == "generate" and target is not None:
            raise SpecError("A generation asset cannot claim an edit target.")
        if target is not None:
            if target not in references or references[target]["role"] != "edit_target":
                raise SpecError("Edit target must identify an edit_target reference.")
            required_refs.append(target)
        for identifier in required_refs:
            if identifier not in references:
                raise SpecError(f"Unknown reference: {identifier}")
            if references[identifier]["gm_only"] and not asset["gm_only"]:
                raise SpecError("A public asset cannot require a private reference.")
        output = asset["presentation"]["output"]
        width, height = output["width_px"], output["height_px"]
        if (width is None) != (height is None):
            raise SpecError("Requested dimensions must be supplied together.")
        ratio = output["aspect_ratio"]
        if ratio and width is not None and width * ratio[1] != height * ratio[0]:
            raise SpecError("Requested dimensions and aspect ratio conflict.")
    for lock in source["locks"]:
        if tokens(lock)[0] in {"schema_version", "spec_id", "revision", "locks"}:
            raise SpecError("Locks must target authoring values, not managed metadata.")
        get(source, lock)


def compile_spec(
    source: Json, audience: str = "player", asset_id: str | None = None
) -> Json:
    validate(source)
    if audience not in {"player", "gm"}:
        raise SpecError("Audience must be player or gm.")
    items = unique(source["items"], "item_id")
    references = unique(source["references"], "reference_id")
    assets = [a for a in source["assets"] if audience == "gm" or not a["gm_only"]]
    if asset_id is not None:
        assets = [a for a in assets if a["asset_id"] == asset_id]
        if not assets:
            raise SpecError("Selected asset is absent or unavailable to this audience.")
    briefs: list[Json] = []
    for asset in assets:
        public_items = []
        issues = []
        prompt_lines = [
            f"Illustrate {asset['title']}. Show exactly {len(asset['item_ids'])} item(s)."
        ]
        lettering = []
        for identifier in asset["item_ids"]:
            item = items[identifier]
            public_items.append(
                {
                    key: deepcopy(item[key])
                    for key in ["item_id", "name", "kind", "appearance"]
                }
            )
            if (
                not item["appearance"]["shape"].strip()
                or not item["appearance"]["materials"]
            ):
                issues.append(f"{identifier}: define shape and materials.")
            prompt_lines.append(
                f"Object {identifier}: {item['name']} ({item['kind']})."
            )
            for key, value in item["appearance"].items():
                if value:
                    prompt_lines.append(
                        f"{key}: {value if isinstance(value, str) else '; '.join(value)}"
                    )
            for inscription in item["inscriptions"]:
                plan = {
                    "item_id": identifier,
                    **deepcopy(inscription),
                    "status": "pending",
                }
                lettering.append(plan)
                placement = inscription["placement"]
                if inscription["handling"] == "exact_composition":
                    prompt_lines.append(
                        f"Leave an unlettered area at {placement} for later exact text composition."
                    )
                elif inscription["handling"] == "render_and_verify":
                    prompt_lines.append(
                        f"Requested inscription at {placement}: {json.dumps(inscription['text'], ensure_ascii=False)}. Lettering must be inspected afterward."
                    )
                else:
                    prompt_lines.append(
                        f"Decorative marks at {placement}: {inscription['text']}."
                    )
        presentation = deepcopy(asset["presentation"])
        if (
            not presentation["viewpoint"].strip()
            or not presentation["arrangement"].strip()
        ):
            issues.append("Define viewpoint and arrangement.")
        prompt_lines.append(
            "Presentation: " + json.dumps(presentation, ensure_ascii=False)
        )
        prompt_lines.append(
            "Art direction: " + json.dumps(source["art_direction"], ensure_ascii=False)
        )
        if asset["constraints"]:
            prompt_lines.append("Constraints: " + "; ".join(asset["constraints"]))
        used_ids = list(
            dict.fromkeys(
                asset["reference_ids"]
                + ([asset["edit_target_ref"]] if asset["edit_target_ref"] else [])
            )
        )
        used_refs = []
        unresolved = []
        for identifier in used_ids:
            reference = references[identifier]
            if reference["inspection"] != "inspected":
                unresolved.append(identifier)
                continue
            used_refs.append(
                {
                    key: deepcopy(reference[key])
                    for key in [
                        "reference_id",
                        "locator",
                        "role",
                        "inspection",
                        "use",
                        "ignore",
                    ]
                }
            )
            prompt_lines.append(
                f"Reference {identifier} ({reference['role']}): use {json.dumps(reference['use'], ensure_ascii=False)}; ignore {json.dumps(reference['ignore'], ensure_ascii=False)}."
            )
        if unresolved:
            issues.append(
                "Required references need inspection and actual image availability."
            )
        briefs.append(
            {
                "asset_id": asset["asset_id"],
                "intent": asset["intent"],
                "items": public_items,
                "presentation": presentation,
                "art_direction": deepcopy(source["art_direction"]),
                "constraints": deepcopy(asset["constraints"]),
                "references": used_refs,
                "edit_target_ref": asset["edit_target_ref"],
                "unresolved_reference_ids": unresolved,
                "lettering_plan": lettering,
                "render_ready": not issues,
                "readiness_issues": issues,
                "image_prompt": "\n".join(prompt_lines),
            }
        )
    canonical = json.dumps(
        source, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return {
        "spec_id": source["spec_id"],
        "source_revision": source["revision"],
        "source_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "audience": audience,
        "briefs": briefs,
        "image": "not_generated",
        "atlas": "not_imported",
    }


def revise(source: Json, change: Json, allowed_locks: list[str] | None = None) -> Json:
    validate(source)
    if (
        set(change) != {"expected_revision", "changes"}
        or type(change["expected_revision"]) is not int
    ):
        raise SpecError("A change needs expected_revision and changes only.")
    if change["expected_revision"] != source["revision"]:
        raise SpecError("Stale source revision.")
    if not isinstance(change["changes"], list) or not change["changes"]:
        raise SpecError("Supply a nonempty list of replacements.")
    allowed = set(allowed_locks or [])
    if not allowed <= set(source["locks"]):
        raise SpecError("Only exact existing lock paths can be authorized.")
    paths: list[list[str]] = []
    result = deepcopy(source)
    for replacement in change["changes"]:
        if not isinstance(replacement, dict) or set(replacement) != {"path", "value"}:
            raise SpecError("Each replacement needs path and value only.")
        parts = tokens(replacement["path"])
        if parts[0] in {"schema_version", "spec_id", "revision", "locks"}:
            raise SpecError("Managed metadata cannot be revised.")
        if any(parts[: len(old)] == old or old[: len(parts)] == parts for old in paths):
            raise SpecError("Overlapping replacement paths.")
        paths.append(parts)
        replace(result, replacement["path"], replacement["value"])
    for group, key in [
        ("items", "item_id"),
        ("assets", "asset_id"),
        ("references", "reference_id"),
    ]:
        old = source[group]
        new = result[group]
        if not isinstance(new, list) or len(new) < len(old):
            raise SpecError(
                "Existing records cannot be removed through a narrow revision."
            )
        for index, record in enumerate(old):
            if not isinstance(new[index], dict) or new[index].get(key) != record[key]:
                raise SpecError("Existing IDs and record order must remain stable.")
            if group == "assets" and new[index].get("item_ids") != record["item_ids"]:
                raise SpecError("Existing assets cannot be rebound to different items.")
            if group == "items":
                inscriptions = new[index].get("inscriptions")
                original = record["inscriptions"]
                if not isinstance(inscriptions, list) or len(inscriptions) < len(
                    original
                ):
                    raise SpecError(
                        "Existing inscriptions cannot be removed through a narrow revision."
                    )
                for position, inscription in enumerate(original):
                    if (
                        not isinstance(inscriptions[position], dict)
                        or inscriptions[position].get("inscription_id")
                        != inscription["inscription_id"]
                    ):
                        raise SpecError(
                            "Existing inscription IDs and order must remain stable."
                        )
    for lock in source["locks"]:
        if lock not in allowed and get(source, lock) != get(result, lock):
            raise SpecError(f"Locked value changed: {lock}")
    result["revision"] += 1
    validate(result)
    return result


def read_json(path: str) -> Json:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SpecError("Expected a JSON object.")
    return value


def write_result(value: Any, output: str | None) -> None:
    rendered = (
        value
        if isinstance(value, str)
        else json.dumps(value, indent=2, ensure_ascii=False)
    )
    if output is None:
        print(rendered)
    else:
        with Path(output).open("x", encoding="utf-8") as stream:
            stream.write(rendered + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate")
    check.add_argument("source")
    compile_command = commands.add_parser("compile")
    compile_command.add_argument("source")
    compile_command.add_argument(
        "--audience", choices=["player", "gm"], default="player"
    )
    compile_command.add_argument("--asset")
    compile_command.add_argument("--text", action="store_true")
    compile_command.add_argument("-o", "--output")
    revision = commands.add_parser("revise")
    revision.add_argument("source")
    revision.add_argument("change")
    revision.add_argument("--allow-locked", action="append", default=[])
    revision.add_argument("-o", "--output", required=True)
    args = parser.parse_args(argv)
    try:
        source = read_json(args.source)
        if args.command == "validate":
            validate(source)
            print("Valid item illustration source.")
        elif args.command == "compile":
            value = compile_spec(source, args.audience, args.asset)
            if args.text:
                if len(value["briefs"]) != 1 or not value["briefs"][0]["render_ready"]:
                    raise SpecError(
                        "Text output requires exactly one ready visible asset."
                    )
                value = value["briefs"][0]["image_prompt"]
            write_result(value, args.output)
        else:
            if Path(args.output).resolve() in {
                Path(args.source).resolve(),
                Path(args.change).resolve(),
            }:
                raise SpecError("Revision output cannot overwrite an input.")
            write_result(
                revise(source, read_json(args.change), args.allow_locked), args.output
            )
    except (SpecError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
