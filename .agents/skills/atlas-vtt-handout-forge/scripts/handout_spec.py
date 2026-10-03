"""Small handout authoring helper. No image service, network, or vault writes."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import html
import io
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast

Json = dict[str, Any]
KINDS = {"letter", "poster", "journal", "contract", "inscription", "other"}
ROLES = {"style", "material", "illustration", "seal", "glyphs", "edit_target"}
FAMILIES = {"serif", "sans-serif", "monospace"}
LAYOUT_KEYS = {"width_px", "height_px", "margin_px", "reserved_illustration_px"}
TYPE_KEYS = {"family", "font_px", "line_height", "ink"}
ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,79}\Z")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def keys(value: Any, required: set[str], optional: set[str] | None = None) -> None:
    require(isinstance(value, dict), "expected an object")
    require(required <= value.keys(), "missing required fields")
    require(value.keys() <= required | (optional or set()), "unknown fields")


def string(value: Any, field: str, *, empty: bool = False) -> None:
    require(isinstance(value, str), f"{field} must be a string")
    require(empty or bool(value.strip()), f"{field} must be nonempty")
    require(
        all(
            (ord(c) >= 32 or c in "\t\n\r") and not 0xD800 <= ord(c) <= 0xDFFF
            for c in value
        ),
        f"{field} contains unsupported control characters or Unicode surrogates",
    )


def pointer(path: str) -> list[str]:
    require(
        isinstance(path, str) and path.startswith("/"), "use an absolute JSON pointer"
    )
    require(re.search(r"~(?![01])", path) is None, "invalid JSON pointer escape")
    return [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/")]


def resolve(source: Any, parts: list[str]) -> Any:
    current = source
    for part in parts:
        if isinstance(current, list):
            require(
                re.fullmatch(r"0|[1-9][0-9]*", part) is not None, "invalid list index"
            )
            require(int(part) < len(current), "list index does not exist")
            current = current[int(part)]
        else:
            require(
                isinstance(current, dict) and part in current, "pointer does not exist"
            )
            current = current[part]
    return current


def overlaps(a: list[str], b: list[str]) -> bool:
    return a[: len(b)] == b or b[: len(a)] == a


def validate(source: Json) -> None:
    keys(
        source,
        {
            "schema_version",
            "set_id",
            "revision",
            "locks",
            "art_direction",
            "documents",
            "references",
        },
        {"gm_notes"},
    )
    require(
        type(source["schema_version"]) is int and source["schema_version"] == 1,
        "schema_version must be 1",
    )
    require(
        type(source["revision"]) is int and source["revision"] >= 1,
        "revision must be positive",
    )
    require(
        isinstance(source["set_id"], str)
        and ID_PATTERN.fullmatch(source["set_id"]) is not None,
        "invalid set_id",
    )
    string(source["art_direction"], "art_direction", empty=True)
    require(isinstance(source["references"], list), "references must be a list")
    refs: Json = {}
    for ref in source["references"]:
        keys(ref, {"ref_id", "locator", "roles", "status", "gm_only", "use", "ignore"})
        require(
            isinstance(ref["ref_id"], str)
            and ID_PATTERN.fullmatch(ref["ref_id"]) is not None,
            "invalid ref_id",
        )
        require(ref["ref_id"] not in refs, "duplicate ref_id")
        refs[ref["ref_id"]] = ref
        string(ref["locator"], "locator")
        require(type(ref["gm_only"]) is bool, "gm_only must be boolean")
        require(
            isinstance(ref["status"], str)
            and ref["status"] in {"uninspected", "inspected", "unavailable"},
            "invalid reference status",
        )
        roles = ref["roles"]
        require(
            isinstance(roles, list)
            and bool(roles)
            and all(isinstance(role, str) and role in ROLES for role in roles),
            "invalid reference roles",
        )
        require(len(roles) == len(set(roles)), "duplicate reference roles")
        string(ref["use"], "use", empty=True)
        string(ref["ignore"], "ignore", empty=True)
        if ref["status"] != "inspected":
            require(
                not ref["use"] and not ref["ignore"],
                "uninspected references cannot contain observations",
            )
    require(
        isinstance(source["documents"], list) and bool(source["documents"]),
        "documents must be nonempty",
    )
    ids = set()
    for doc in source["documents"]:
        keys(
            doc,
            {
                "asset_id",
                "kind",
                "gm_only",
                "wording",
                "material",
                "illustration",
                "typography",
                "layout",
                "reference_ids",
            },
            {"edit_target_id"},
        )
        require(
            isinstance(doc["asset_id"], str)
            and ID_PATTERN.fullmatch(doc["asset_id"]) is not None,
            "invalid asset_id",
        )
        require(doc["asset_id"] not in ids, "duplicate asset_id")
        ids.add(doc["asset_id"])
        require(
            isinstance(doc["kind"], str) and doc["kind"] in KINDS,
            "invalid document kind",
        )
        require(type(doc["gm_only"]) is bool, "gm_only must be boolean")
        for field in ("material", "illustration"):
            string(doc[field], field, empty=True)
        keys(doc["wording"], {"content", "approval", "basis"})
        string(doc["wording"]["content"], "content", empty=True)
        string(doc["wording"]["basis"], "wording basis", empty=True)
        require(
            doc["wording"]["approval"] in ("draft", "approved"),
            "invalid wording approval",
        )
        if doc["wording"]["approval"] == "approved":
            require(
                bool(doc["wording"]["content"].strip()),
                "approved wording must be nonempty",
            )
            require(
                bool(doc["wording"]["basis"].strip()),
                "final wording needs a recorded authority basis",
            )
        typo, layout = doc["typography"], doc["layout"]
        keys(typo, TYPE_KEYS)
        keys(layout, LAYOUT_KEYS)
        require(
            isinstance(typo["family"], str) and typo["family"] in FAMILIES,
            "unsupported font family",
        )
        require(
            type(typo["font_px"]) is int and 1 <= typo["font_px"] <= 300,
            "invalid font size",
        )
        require(
            type(typo["line_height"]) in (int, float) and 1 <= typo["line_height"] <= 3,
            "invalid line height",
        )
        require(
            isinstance(typo["ink"], str)
            and re.fullmatch(r"#[0-9a-fA-F]{6}", typo["ink"]) is not None,
            "invalid ink color",
        )
        require(
            all(
                type(layout[field]) is int and layout[field] >= 0
                for field in LAYOUT_KEYS
            ),
            "layout dimensions must be nonnegative integers",
        )
        require(
            1 <= layout["width_px"] <= 20000 and 1 <= layout["height_px"] <= 20000,
            "invalid page size",
        )
        require(
            2 * layout["margin_px"] < layout["width_px"], "margins leave no text width"
        )
        require(
            2 * layout["margin_px"]
            + layout["reserved_illustration_px"]
            + typo["font_px"] * typo["line_height"]
            <= layout["height_px"],
            "layout leaves no text line",
        )
        requested = doc["reference_ids"]
        require(
            isinstance(requested, list)
            and all(isinstance(rid, str) and rid in refs for rid in requested),
            "unknown reference ID",
        )
        require(
            len(requested) == len(set(requested)), "duplicate document reference IDs"
        )
        if "edit_target_id" in doc:
            target = doc["edit_target_id"]
            require(
                isinstance(target, str)
                and target in requested
                and "edit_target" in refs[target]["roles"],
                "invalid edit target binding",
            )
    locks = source["locks"]
    require(
        isinstance(locks, list) and all(isinstance(lock, str) for lock in locks),
        "locks must be pointers",
    )
    require(len(locks) == len(set(locks)), "duplicate locks")
    for lock in locks:
        require(lock != "/revision", "revision is managed and cannot be locked")
        resolve(source, pointer(lock))


def get_document(source: Json, asset: str, audience: str = "player") -> Json:
    validate(source)
    found = [doc for doc in source["documents"] if doc["asset_id"] == asset]
    require(len(found) == 1, "asset ID does not exist")
    require(
        audience == "gm" or not found[0]["gm_only"],
        "private document excluded from player output",
    )
    return cast(Json, found[0])


def approved_text(doc: Json) -> str:
    require(
        doc["wording"]["approval"] == "approved",
        "wording is draft; approval is required for composition",
    )
    text: str = doc["wording"]["content"]
    return text


def brief(source: Json, audience: str = "player", asset: str | None = None) -> Json:
    validate(source)
    docs = [get_document(source, asset, audience)] if asset else source["documents"]
    refs = {ref["ref_id"]: ref for ref in source["references"]}
    output = []
    for doc in docs:
        if audience == "player" and doc["gm_only"]:
            continue
        used, unresolved = [], []
        for rid in doc["reference_ids"]:
            ref = refs[rid]
            if ref["status"] != "inspected" or (
                audience == "player" and ref["gm_only"]
            ):
                unresolved.append(rid)
            else:
                used.append(copy.deepcopy(ref))
        layout = doc["layout"]
        prompt = (
            f"Create the background artwork for a {doc['kind']}. {source['art_direction']}\n"
            f"Material: {doc['material']}\nIllustration: {doc['illustration']}\n"
            f"Requested canvas: {layout['width_px']} by {layout['height_px']} pixels. "
            f"Keep a blank readable text region inside {layout['margin_px']} pixel margins, "
            f"reserving the bottom {layout['reserved_illustration_px']} pixels for illustration. "
            "Do not draw lettering, titles, signatures, glyphs, captions, or interface elements. "
            "Approved wording will be added through deterministic text composition."
        )
        output.append(
            {
                "asset_id": doc["asset_id"],
                "kind": doc["kind"],
                "background_prompt": prompt,
                "wording": {
                    "content": doc["wording"]["content"],
                    "approval": doc["wording"]["approval"],
                },
                "typography": copy.deepcopy(doc["typography"]),
                "layout": copy.deepcopy(layout),
                "references": used,
                "unresolved_reference_ids": unresolved,
                "edit_target_id": doc.get("edit_target_id"),
                "render_ready": not unresolved and bool(doc["material"].strip()),
                "composition_ready": doc["wording"]["approval"] == "approved",
            }
        )
    return {
        "set_id": source["set_id"],
        "source_revision": source["revision"],
        "audience": audience,
        "documents": output,
    }


def inspect_image(path: Path) -> Json:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError(
            "image checks need Pillow; use uv run --with 'pillow>=11,<13' python"
        ) from exc
    with Image.open(path) as image:
        require(
            image.format in {"PNG", "JPEG", "WEBP", "GIF"},
            "background must be PNG, JPEG, WebP, or GIF",
        )
        image.load()
        alpha = image.convert("RGBA").getchannel("A")
        low, high = alpha.getextrema()
        return {
            "format": image.format,
            "width_px": image.width,
            "height_px": image.height,
            "frames": getattr(image, "n_frames", 1),
            "alpha_min": low,
            "alpha_max": high,
        }


def compose(
    source: Json, asset: str, background: Path | None = None, audience: str = "player"
) -> str:
    doc = get_document(source, asset, audience)
    wording = approved_text(doc)
    layout, typo = doc["layout"], doc["typography"]
    background_css = ""
    if background:
        metadata = inspect_image(background)
        require(metadata["frames"] == 1, "composition expects a static background")
        require(
            (metadata["width_px"], metadata["height_px"])
            == (layout["width_px"], layout["height_px"]),
            "background dimensions differ from layout; review and resolve before composition",
        )
        from PIL import Image

        with Image.open(background) as image:
            clean = image.convert("RGBA")
            clean.info.clear()
            buffer = io.BytesIO()
            clean.save(buffer, format="PNG")
        data = base64.b64encode(buffer.getvalue()).decode("ascii")
        background_css = f"background-image:url('data:image/png;base64,{data}');background-size:100% 100%;"
    # Character references preserve CRs through HTML line-ending normalization.
    escaped = html.escape(wording, quote=True).replace("\r", "&#13;")
    digest = hashlib.sha256(wording.encode("utf-8")).hexdigest()
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src data:; style-src 'unsafe-inline'\">"
        f"<title>{html.escape(asset)}</title><style>"
        "*{box-sizing:border-box}body{margin:0;background:#fff}.sheet{"
        f"width:{layout['width_px']}px;min-height:{layout['height_px']}px;"
        f"padding:{layout['margin_px']}px {layout['margin_px']}px "
        f"{layout['margin_px'] + layout['reserved_illustration_px']}px;"
        f"background-color:#f3ead3;{background_css}"
        "}.exact-text{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;"
        f"font-family:{typo['family']};font-size:{typo['font_px']}px;"
        f"line-height:{typo['line_height']};color:{typo['ink']};"
        "}</style></head><body>"
        f'<main class="sheet"><div class="exact-text" id="approved-wording" data-text-sha256="{digest}">'
        f"{escaped}</div></main></body></html>"
    )


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.found = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        require(not self.active, "unexpected markup inside approved wording")
        if dict(attrs).get("id") == "approved-wording":
            require(
                tag == "div", "approved wording must use its expected text container"
            )
            self.active = True
            self.found += 1

    def handle_endtag(self, tag: str) -> None:
        if self.active:
            require(tag == "div", "unexpected markup inside approved wording")
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)


def check_text(
    source: Json, asset: str, document_html: str, audience: str = "player"
) -> None:
    expected = approved_text(get_document(source, asset, audience))
    parser = TextExtractor()
    parser.feed(document_html)
    parser.close()
    require(
        parser.found == 1 and not parser.active,
        "expected one complete approved wording container",
    )
    require(
        "".join(parser.parts) == expected, "HTML text differs from approved wording"
    )


def revise(
    source: Json,
    change: Json,
    allow_locked: list[str] | None = None,
    wording_basis: str | None = None,
) -> Json:
    validate(source)
    keys(change, {"expected_revision", "changes"})
    require(
        type(change["expected_revision"]) is int
        and change["expected_revision"] == source["revision"],
        "stale expected revision",
    )
    require(
        isinstance(change["changes"], list) and bool(change["changes"]),
        "changes must be nonempty",
    )
    allowed = set(allow_locked or [])
    require(
        allowed <= set(source["locks"]),
        "lock authorization must name an existing exact lock",
    )
    if wording_basis is not None:
        string(wording_basis, "wording basis")
    result = copy.deepcopy(source)
    seen: list[list[str]] = []
    changed = False
    for item in change["changes"]:
        keys(item, {"path", "value"})
        parts = pointer(item["path"])
        require(
            not any(overlaps(parts, old) for old in seen),
            "overlapping changes are ambiguous",
        )
        seen.append(parts)
        editable = (
            parts == ["art_direction"]
            or (
                len(parts) == 3
                and parts[0] == "documents"
                and parts[2] in {"material", "illustration"}
            )
            or (
                len(parts) == 4
                and parts[0] == "documents"
                and (
                    (parts[2] == "wording" and parts[3] == "content")
                    or (parts[2] == "layout" and parts[3] in LAYOUT_KEYS)
                    or (parts[2] == "typography" and parts[3] in TYPE_KEYS)
                )
            )
            or (
                len(parts) == 3
                and parts[0] == "references"
                and parts[2] in {"locator", "use", "ignore"}
            )
        )
        require(editable, "field requires a deliberate master edit")
        old_value = resolve(result, parts)
        require(
            not isinstance(old_value, (dict, list)),
            "only existing leaf values can be revised",
        )
        for lock in source["locks"]:
            require(
                not overlaps(parts, pointer(lock)) or lock in allowed,
                "change touches a locked field",
            )
        parent = resolve(result, parts[:-1])
        if old_value != item["value"]:
            changed = True
            parent[parts[-1]] = copy.deepcopy(item["value"])
            if parts[0] == "documents" and parts[2:] == ["wording", "content"]:
                wording = result["documents"][int(parts[1])]["wording"]
                wording["approval"] = "approved" if wording_basis else "draft"
                wording["basis"] = wording_basis or ""
            if parts[0] == "references" and parts[2:] == ["locator"]:
                ref = result["references"][int(parts[1])]
                ref.update(status="uninspected", use="", ignore="")
    require(changed, "change has no effect")
    for lock in source["locks"]:
        require(
            resolve(source, pointer(lock)) == resolve(result, pointer(lock))
            or lock in allowed,
            "change indirectly touches a locked field",
        )
    result["revision"] += 1
    validate(result)
    return result


def load(path: Path) -> Json:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "source must be an object")
    return cast(Json, value)


def write_new(path: Path, content: str) -> None:
    with path.open("xb") as output:
        output.write(content.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "brief", "compose", "text", "check-text", "revise"):
        item = sub.add_parser(command)
        item.add_argument("source", type=Path)
        if command in {"brief", "compose", "text", "check-text"}:
            item.add_argument("--audience", choices=("player", "gm"), default="player")
            item.add_argument("--asset", required=command != "brief")
        if command in {"brief", "compose", "text", "revise"}:
            item.add_argument("-o", "--output", type=Path, required=True)
        if command == "compose":
            item.add_argument("--background", type=Path)
        if command == "check-text":
            item.add_argument("--html", type=Path, required=True)
        if command == "revise":
            item.add_argument("change", type=Path)
            item.add_argument("--allow-locked", action="append", default=[])
            item.add_argument(
                "--wording-basis",
                help="record existing user authority for final changed wording",
            )
    inspector = sub.add_parser("inspect-image")
    inspector.add_argument("image", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "inspect-image":
            print(json.dumps(inspect_image(args.image), indent=2))
            return 0
        source = load(args.source)
        validate(source)
        if args.command == "validate":
            print(
                f"valid: {len(source['documents'])} document(s), revision {source['revision']}"
            )
            return 0
        if args.command == "check-text":
            check_text(
                source,
                args.asset,
                args.html.read_bytes().decode("utf-8"),
                args.audience,
            )
            print("exact text matches approved source")
            return 0
        if args.command == "brief":
            content = (
                json.dumps(
                    brief(source, args.audience, args.asset),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
        elif args.command == "compose":
            content = compose(source, args.asset, args.background, args.audience)
            check_text(source, args.asset, content, args.audience)
        elif args.command == "text":
            content = approved_text(get_document(source, args.asset, args.audience))
        else:
            content = (
                json.dumps(
                    revise(
                        source, load(args.change), args.allow_locked, args.wording_basis
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
        write_new(args.output, content)
        print(f"created: {args.output}")
        return 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
