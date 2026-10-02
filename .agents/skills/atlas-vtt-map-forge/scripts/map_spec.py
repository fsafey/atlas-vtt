#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.23,<5"]
# ///
"""Validate, patch and compile map briefs. Never calls an image service.

Run with uv run python; the uv script metadata declares the validator dependency.
The compiler is deterministic; the eventual image renderer is not.
"""
from __future__ import annotations

import argparse
from collections import deque
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:
    raise SystemExit('Run with: uv run --with "jsonschema>=4.23,<5" python scripts/map_spec.py ...')

ROOT = Path(__file__).resolve().parents[1]
COMPILER_VERSION = '1.1.0-atlas'
SCHEMA = json.loads((ROOT / 'schemas/map-spec.schema.json').read_text())
PATCH_SCHEMA = json.loads((ROOT / 'schemas/patch.schema.json').read_text())


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def load_json(path: str | Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f'Not valid JSON: {value}')
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=_no_duplicates, parse_constant=reject_constant)


def dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n'


def canonical_hash(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def pointer_parts(path: str) -> list[str]:
    if not path.startswith('/'):
        raise ValueError('Only non-root JSON Pointers beginning with / are supported.')
    if re.search(r'~(?![01])', path):
        raise ValueError(f'Invalid JSON Pointer escape: {path}')
    return [part.replace('~1', '/').replace('~0', '~') for part in path[1:].split('/')]


def _index(token: str, length: int, append: bool = False) -> int:
    if append and token == '-':
        return length
    if not re.fullmatch(r'0|[1-9][0-9]*', token):
        raise ValueError(f'Invalid array index: {token}')
    index = int(token)
    if not (0 <= index <= length if append else 0 <= index < length):
        raise ValueError(f'Array index out of range: {token}')
    return index


def get_pointer(document: Any, path: str) -> Any:
    value = document
    for token in pointer_parts(path):
        if isinstance(value, dict):
            if token not in value:
                raise ValueError(f'JSON Pointer does not exist: {path}')
            value = value[token]
        elif isinstance(value, list):
            value = value[_index(token, len(value))]
        else:
            raise ValueError(f'Cannot traverse scalar at: {path}')
    return value


def _equal(a: Any, b: Any) -> bool:
    # JSON treats booleans separately from numbers (unlike Python's True == 1).
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_equal(x, y) for x, y in zip(a, b))
    return a == b


def apply_patch(document: Any, operations: Any) -> Any:
    """Atomic JSON Patch subset: add / remove / replace / test. No root patch."""
    failures = list(Draft202012Validator(PATCH_SCHEMA).iter_errors(operations))
    if failures:
        raise ValueError('Invalid patch: ' + failures[0].message)
    result = copy.deepcopy(document)
    for operation in operations:
        path, op = operation['path'], operation['op']
        parts = pointer_parts(path)
        if op == 'test':
            if not _equal(get_pointer(result, path), operation['value']):
                raise ValueError(f'Patch test failed: {path}')
            continue
        parent = result
        for token in parts[:-1]:
            if isinstance(parent, dict) and token in parent:
                parent = parent[token]
            elif isinstance(parent, list):
                parent = parent[_index(token, len(parent))]
            else:
                raise ValueError(f'Patch parent does not exist: {path}')
        token = parts[-1]
        if isinstance(parent, dict):
            if op != 'add' and token not in parent:
                raise ValueError(f'Patch target does not exist: {path}')
            if op == 'remove':
                del parent[token]
            else:
                parent[token] = copy.deepcopy(operation['value'])
        elif isinstance(parent, list):
            index = _index(token, len(parent), append=op == 'add')
            if op == 'add':
                parent.insert(index, copy.deepcopy(operation['value']))
            elif op == 'remove':
                parent.pop(index)
            else:
                parent[index] = copy.deepcopy(operation['value'])
        else:
            raise ValueError(f'Cannot patch scalar parent: {path}')
    return result


def is_visible(item: dict[str, Any], audience: str) -> bool:
    return audience == 'gm' or item['visibility'] == 'public'


def _center(entity: dict[str, Any]) -> tuple[float, float]:
    x, y, w, h = entity['placement']['bounds']
    return x + w / 2, y + h / 2


def _inside_point(point: list[float], bounds: list[float], tolerance: float = 0) -> bool:
    x, y, w, h = bounds
    return x - tolerance <= point[0] <= x + w + tolerance and y - tolerance <= point[1] <= y + h + tolerance


def validate_spec(spec: Any, audience: str | None = None) -> tuple[list[str], list[str]]:
    errors = []
    for err in sorted(Draft202012Validator(SCHEMA).iter_errors(spec),
                      key=lambda e: '/'.join(map(str, e.absolute_path))):
        where = '/' + '/'.join(map(str, err.absolute_path))
        errors.append(f'{where}: {err.message}')
    if errors:
        return errors, []
    warnings: list[str] = []
    audience = audience or spec['production']['audience']
    entities = spec['entities']
    public = {key for key, value in entities.items() if is_visible(value, audience)}
    width, height = spec['canvas']['target_pixels']
    aw, ah = spec['canvas']['aspect_ratio']
    if width * ah != height * aw:
        errors.append('/canvas: target_pixels must have exactly the specified aspect_ratio.')
    if spec['map_type'] in {'battlemap', 'dungeon'} and spec['style']['perspective'] != 'orthographic_top_down':
        errors.append('/style/perspective: battlemap and dungeon profiles require orthographic_top_down; use an overview profile for oblique illustration.')
    for key, entity in entities.items():
        x, y, w, h = entity['placement']['bounds']
        if x + w > 1.000001 or y + h > 1.000001:
            errors.append(f'/entities/{key}/placement: bounds extend outside the canvas.')
        for point in entity['placement'].get('path', []):
            if not _inside_point(point, [x, y, w, h], 0.000001):
                errors.append(f'/entities/{key}/placement/path: path point lies outside its bounds.')
    def check_id(value: str, path: str, require_visible: bool = False) -> None:
        if value not in entities:
            errors.append(f'{path}: unknown entity ID {value}.')
        elif require_visible and value not in public:
            errors.append(f'{path}: entity is not visible to the selected audience.')
    check_id(spec['style']['focal_entity_id'], '/style/focal_entity_id', True)
    for key in spec['style']['hierarchy']:
        check_id(key, '/style/hierarchy')
    for key in spec['gameplay']['entry_ids']:
        check_id(key, '/gameplay/entry_ids', True)
    for key in spec['gameplay']['objective_ids']:
        check_id(key, '/gameplay/objective_ids', True)
    adjacency: dict[str, set[str]] = {key: set() for key in public}
    minimum = spec['gameplay']['minimum_path_width_cells']
    for key, edge in spec['connections'].items():
        chain = [edge['from'], *edge['via'], edge['to']]
        for entity_id in chain:
            check_id(entity_id, f'/connections/{key}')
        visible = is_visible(edge, audience)
        if visible and any(node not in public for node in chain):
            errors.append(f'/connections/{key}: a visible route references an entity hidden from this audience.')
        if edge['width_cells'] is not None and minimum is not None and edge['traversable'] and edge['width_cells'] < minimum:
            errors.append(f'/connections/{key}/width_cells: smaller than gameplay minimum.')
        if spec['map_type'] in {'battlemap', 'dungeon'} and edge['traversable'] and edge['width_cells'] is None:
            warnings.append(f'/connections/{key}: tactical route has no explicit width_cells.')
        for end, node in [(edge['path'][0], edge['from']), (edge['path'][-1], edge['to'])]:
            if node in entities and not _inside_point(end, entities[node]['placement']['bounds'], 0.035):
                warnings.append(f'/connections/{key}: path endpoint is not near its declared endpoint entity; inspect layout.')
        if visible and edge['traversable'] and all(node in public for node in chain):
            for a, b in zip(chain, chain[1:]):
                adjacency[a].add(b)
                adjacency[b].add(a)
    for rel in spec['relationships']:
        a, b = rel['from'], rel['to']
        check_id(a, '/relationships/from')
        check_id(b, '/relationships/to')
        if a not in entities or b not in entities:
            continue
        ax, ay = _center(entities[a]); bx, by = _center(entities[b])
        status = {'north_of': ay < by, 'south_of': ay > by,
                  'east_of': ax > bx, 'west_of': ax < bx}.get(rel['relation'])
        if rel['relation'] == 'inside':
            x, y, w, h = entities[a]['placement']['bounds']
            status = all(_inside_point(pt, entities[b]['placement']['bounds'], 0.000001)
                         for pt in ([x, y], [x + w, y + h]))
        if status is False:
            message = f'/relationships: {a} {rel["relation"]} {b} conflicts with declared bounds.'
            (errors if rel['strength'] == 'must' else warnings).append(message)
    if spec['gameplay']['require_reachability']:
        starts = spec['gameplay']['entry_ids']; goals = spec['gameplay']['objective_ids']
        if not starts or not goals:
            errors.append('/gameplay: reachability requires at least one entry and one objective.')
        visited = set(node for node in starts if node in adjacency)
        queue = deque(visited)
        while queue:
            for node in adjacency[queue.popleft()]:
                if node not in visited:
                    visited.add(node); queue.append(node)
        for goal in goals:
            if goal not in visited:
                errors.append(f'/gameplay: objective {goal} is unreachable in the declared traversable route graph.')
    grid = spec['gameplay']['grid']
    if grid['type'] == 'none':
        if grid['render'] != 'none':
            errors.append('/gameplay/grid: type none requires render none.')
        if any(grid[k] is not None for k in ['columns','rows','pixels_per_cell','hex_cell_width_px','units_per_cell']) or grid['hex_orientation'] != 'none':
            errors.append('/gameplay/grid: inactive grid sizing fields must be null; hex_orientation must be none.')
    else:
        if grid['render'] == 'none':
            errors.append('/gameplay/grid: active grid requires a rendering destination.')
        if grid['units_per_cell'] is None:
            warnings.append('/gameplay/grid: distance per cell is unspecified.')
    if grid['type'] == 'square':
        if grid['hex_orientation'] != 'none' or grid['hex_cell_width_px'] is not None:
            errors.append('/gameplay/grid: square grid must not contain hex settings.')
        if any(grid[k] is None for k in ['columns','rows','pixels_per_cell']):
            errors.append('/gameplay/grid: square grid requires columns, rows and pixels_per_cell.')
        elif grid['offset_px'] == [0, 0]:
            if (grid['columns'] * grid['pixels_per_cell'], grid['rows'] * grid['pixels_per_cell']) != (width, height):
                errors.append('/gameplay/grid: square grid dimensions do not match canvas target_pixels.')
        else:
            warnings.append('/gameplay/grid: nonzero offsets require manual edge/cell calibration; square pixel equation was not checked.')
    if grid['type'] == 'hex':
        if grid['hex_orientation'] == 'none' or grid['pixels_per_cell'] is not None:
            errors.append('/gameplay/grid: hex grid requires orientation and null square pixels_per_cell.')
        warnings.append('Hex dimensions are a setup plan, not a square-grid pixel calculation. Calibrate the actual image in the VTT.')
    if grid['render'] == 'baked':
        warnings.append('A model-drawn grid is not guaranteed regular or correctly aligned; prefer a VTT/postprocess overlay.')
    label_ids = set()
    for label in spec['annotations']['labels']:
        if label['id'] in label_ids:
            errors.append('/annotations/labels: duplicate label id.')
        label_ids.add(label['id'])
        if label['entity_id'] is not None:
            check_id(label['entity_id'], '/annotations/labels/entity_id')
        if is_visible(label, audience) and label['entity_id'] in entities and label['entity_id'] not in public:
            errors.append('/annotations/labels: a visible label exposes a hidden entity.')
    for zone in spec['annotations']['clear_zones']:
        x, y, w, h = zone['bounds']
        if x + w > 1.000001 or y + h > 1.000001:
            errors.append('/annotations/clear_zones: bounds extend outside the canvas.')
    if spec['annotations']['label_mode'] == 'baked':
        warnings.append('Model-rendered labels require spelling, placement and legibility inspection.')
    if spec['production']['action'] == 'edit_existing':
        if not spec['production']['base_image_reference'] or not spec['production']['edit_scope']:
            errors.append('/production: edit_existing requires a base_image_reference and a nonempty edit_scope.')
    elif spec['production']['base_image_reference'] is not None or spec['production']['edit_scope']:
        errors.append('/production: new_image requires null base_image_reference and empty edit_scope; use inspiration.references for non-edit references.')
    if spec['production']['variant'] != 'base' and spec['production']['action'] == 'new_image':
        warnings.append('This variant is a fresh generation brief, not a geometry-preserving edit. Attach an approved base image for faithful variants.')
    for pointer in spec['locks']:
        try:
            get_pointer(spec, pointer)
        except ValueError as exc:
            errors.append(f'/locks: {exc}')
    warnings.extend([
        'Coordinates, counts and route geometry are design constraints, not proven properties of any generated image.',
        'Schema and structured-rule checks do not validate hydrology, crossings, visual occlusion, room topology or prose contradictions.',
        'Target pixel dimensions and file format are export goals. Verify actual image metadata and calibrate the VTT after generation.'
    ])
    return errors, list(dict.fromkeys(warnings))


def patch_spec(spec: dict[str, Any], operations: Any, allow_locked: list[str] | None = None) -> dict[str, Any]:
    patch_errors = list(Draft202012Validator(PATCH_SCHEMA).iter_errors(operations))
    if patch_errors:
        raise ValueError('Invalid patch: ' + patch_errors[0].message)
    errors, _ = validate_spec(spec)
    if errors:
        raise ValueError('Invalid original spec: ' + '; '.join(errors))
    if not any(op.get('op') == 'test' and op.get('path') == '/revision'
               and _equal(op.get('value'), spec['revision']) for op in operations):
        raise ValueError('Patch must test the current /revision to prevent stale updates.')
    allowed = set(allow_locked or [])
    if not allowed.issubset(set(spec['locks'])):
        raise ValueError('--allow-locked must name exact currently locked paths.')
    result = apply_patch(spec, operations)
    for pointer in ['/version','/id','/revision','/locks']:
        try:
            unchanged = _equal(get_pointer(spec, pointer), get_pointer(result, pointer))
        except ValueError:
            unchanged = False
        if not unchanged:
            raise ValueError(f'Patch cannot change {pointer}; revision increments automatically. Edit identity/lock definitions deliberately in the master file.')
    for pointer in spec['locks']:
        try:
            unchanged = _equal(get_pointer(spec, pointer), get_pointer(result, pointer))
        except ValueError:
            unchanged = False
        if not unchanged and pointer not in allowed:
            raise ValueError(f'Locked field changed: {pointer}')
    result['revision'] += 1
    errors, _ = validate_spec(result)
    if errors:
        raise ValueError('Patched spec failed validation: ' + '; '.join(errors))
    return result


def describe_bounds(bounds: list[float]) -> str:
    x, y, w, h = bounds
    return f'box left {x:.1%}, top {y:.1%}, width {w:.1%}, height {h:.1%}'


def describe_path(path: list[list[float]]) -> str:
    return ' -> '.join(f'({x:.1%} across, {y:.1%} down)' for x, y in path)


def atlas_setup_plan(spec: dict[str, Any], audience: str,
                     labels: list[dict[str, Any]], markers: list[dict[str, Any]]) -> dict[str, Any]:
    """Atlas UI setup hints, never a MapFile or persisted Zustand envelope.

    Pixel hints assume an unscaled background at the requested dimensions.
    Neither the actual raster nor a running Atlas instance is inspected here.
    """
    grid = spec['gameplay']['grid']
    active = grid['type'] != 'none'
    hints: dict[str, Any] = {
        'enabled': active, 'visible': active and grid['render'] == 'vtt',
        'snapToGrid': active,
    }
    notes = ['All settings are candidates for manual calibration against the actual imported image.']
    if active:
        if grid['type'] == 'square':
            hints.update(type='square', size=grid['pixels_per_cell'])
        else:
            pointy = grid['hex_orientation'] == 'pointy_top'
            hints['type'] = 'hex-vertical' if pointy else 'hex-horizontal'
            width = grid['hex_cell_width_px']
            if width is not None:
                hints['size'] = width if pointy else width * math.sqrt(3) / 2
            else:
                notes.append('Hex width is unspecified; measure it before setting Atlas grid.size.')
        hints.update(offsetX=grid['offset_px'][0], offsetY=grid['offset_px'][1])
        unit, factor = {'ft': ('feet', 1), 'm': ('meters', 1),
                        'mi': ('feet', 5280), 'km': ('meters', 1000),
                        'abstract': ('units', 1)}[grid['units']]
        hints.update(unitType=unit,
                     measurementType='abstract' if grid['units'] == 'abstract' else 'units')
        if grid['units_per_cell'] is not None:
            hints['unitDistance'] = grid['units_per_cell'] * factor
        if factor != 1:
            notes.append(f"Atlas has no {grid['units']} unitType; converted distance to {unit}. Confirm the displayed scale.")
        if grid['render'] != 'vtt':
            notes.append('Hide Atlas grid lines to avoid doubling a baked or externally composited grid; calibrate snapping separately.')
    note_candidates = copy.deepcopy(markers) if spec['annotations']['markers'] == 'vtt' else []
    label_candidates = copy.deepcopy(labels) if spec['annotations']['label_mode'] == 'postprocess' else []
    steps = [
        'Produce and inspect a player-safe base image; keep the editable master specification private.',
        'Open Atlas VTT: Open dashboard in desktop Obsidian; choose the intended collection.',
        'Import the local image with the asset manager + button, then create a scene from the map asset.',
        'Align the grid manually; auto detection is an option for an image with an existing grid, not proof of correct alignment.',
        'Add labels with Atlas text tools or a separately prepared overlay. Link Markdown or Atlas maps with note pins; pins are GM preparation aids.',
        'Place tokens and configure fog, walls and lighting separately in Atlas as needed.',
        'Present the scene in the separate player window, inspect disclosure, then reopen the scene to verify persistence.',
    ]
    if not active:
        steps[3] = 'Disable grid display and snapping for this gridless scene.'
    return {
        'platform': 'atlas-vtt', 'status': 'plan_only_not_imported',
        'scene_export': 'not_created', 'scene_extension': '.atlasmap',
        'background_audience': audience,
        'background_use': 'player_safe_candidate' if audience == 'player' else 'gm_reference_only',
        'coordinate_basis': 'normalized_image_space_not_atlas_world_coordinates',
        'target_pixels': copy.deepcopy(spec['canvas']['target_pixels']),
        'grid_field_hints': hints, 'source_grid': copy.deepcopy(grid),
        'text_label_candidates': label_candidates,
        'gm_note_pin_candidates': note_candidates if audience == 'gm' else [],
        'setup_steps': steps, 'calibration_notes': notes,
        'acceptance_checks': [
            'Inspect actual image dimensions and compare several cell spacings across the image after alignment.',
            'Test token snapping and a known movement distance, including hex orientation if applicable.',
            'Inspect the player window for unintended labels, tokens, secrets and revealed areas. Baked image content cannot be removed by GM visibility flags.',
            'Reopen the .atlasmap scene and confirm background, grid and authored objects persist.',
        ],
    }


def compile_spec(spec: dict[str, Any], audience: str | None = None) -> dict[str, Any]:
    # Normalize object order as well as hashing it; array order remains meaningful.
    spec = json.loads(json.dumps(spec, ensure_ascii=False, sort_keys=True, allow_nan=False))
    audience = audience or spec['production']['audience']
    errors, warnings = validate_spec(spec, audience)
    if errors:
        raise ValueError('Spec failed validation: ' + '; '.join(errors))
    entities = {k:v for k,v in spec['entities'].items() if is_visible(v, audience)}
    connections = {k:v for k,v in spec['connections'].items() if is_visible(v, audience)
                   and all(node in entities for node in [v['from'], *v['via'], v['to']])}
    style, environment = spec['style'], spec['environment']
    annotations, production, grid = spec['annotations'], spec['production'], spec['gameplay']['grid']
    labels = [copy.deepcopy(label) for label in annotations['labels']
              if is_visible(label, audience) and (label['entity_id'] is None or label['entity_id'] in entities)]
    if annotations['label_mode'] == 'none':
        labels = []
    sections: list[tuple[str, str]] = []
    ratio = ':'.join(map(str, spec['canvas']['aspect_ratio']))
    perspective = ('True orthographic top-down plan; no horizon, vanishing point, perspective tilt or facade views.'
                   if style['perspective'] == 'orthographic_top_down'
                   else 'Overhead geographic composition with pictorial oblique mountains and buildings; no horizon or cinematic landscape camera.')
    sections.append(('DELIVERABLE', f"One {spec['map_type']} map for tabletop play, {ratio} composition. {perspective}\nPurpose: {spec['purpose']}\nWorking title (not automatically printed): {spec['title']}."))
    if production['action'] == 'edit_existing':
        sections.append(('EDIT ONLY THE APPROVED BASE', 'Use the attached approved base image as the editing target. Change only: '
                         + '; '.join(production['edit_scope'])
                         + '. Preserve all unrequested geography, placement, scale, route topology and object identities. Do not redraw the map from scratch.'))
    sections.append(('INTENT AND COMPOSITION',
        f"Premise: {spec['inspiration']['premise']}\nMood: {', '.join(spec['inspiration']['mood'])}. Novelty: {spec['inspiration']['novelty']}.\n"
        + 'Motifs: ' + '; '.join(spec['inspiration']['motifs']) + '\n'
        + environment['terrain_summary'] + '\n'
        + f"Primary visual anchor: {entities[style['focal_entity_id']]['name']}. "
        + 'Read in this order: ' + ' > '.join(entities[k]['name'] for k in style['hierarchy'] if k in entities) + '.\n'
        + f"Keep critical content inside an edge safety inset of {spec['canvas']['margin_fraction']:.1%}. North is up. "
        + 'Coordinates below use image space: x left-to-right, y top-to-bottom; every percentage is relative to the complete canvas. These are layout instructions, not drawn coordinate labels.'))
    sections.append(('VISUAL LANGUAGE', f"{style['medium']}\nLinework: {style['linework']}\nPalette by role: "
                     + '; '.join(f'{k}: {v}' for k,v in style['palette'].items())
                     + f"\nSurface: {style['surface_texture']}\nLighting: {style['lighting']}\nDetail density: {style['density']}. Border: {style['border_treatment']}. "
                     + 'Concentrate small detail around important places; protect terrain silhouettes and readable routes.'))
    sections.append(('ENVIRONMENT', f"Season: {environment['season']}. Time: {environment['time_of_day']}. Weather: {environment['weather']}. "
                     + f"Physical logic: {environment['physical_logic']}. "
                     + ('Explicit exceptions: ' + '; '.join(environment['exceptions']) if environment['exceptions'] else 'No unrequested supernatural geography.')))
    rank = {'primary':0,'supporting':1,'ambient':2}
    content = []
    for key, entity in sorted(entities.items(), key=lambda kv:(rank[kv[1]['importance']], kv[0])):
        value = (f"{key} | {entity['name']} | {entity['kind']} | {entity['importance']} | quantity {entity['quantity']}. "
                 + describe_bounds(entity['placement']['bounds']) + '. '
                 + entity['appearance'])
        if 'path' in entity['placement']:
            value += '\nShape path: ' + describe_path(entity['placement']['path']) + '.'
        if entity['must_show']:
            value += '\nMust show: ' + '; '.join(entity['must_show']) + '.'
        if entity['must_avoid']:
            value += '\nDo not show here: ' + '; '.join(entity['must_avoid']) + '.'
        if entity['gameplay_role']:
            value += '\nSpatial function: ' + entity['gameplay_role'] + '.'
        content.append(value)
    sections.append(('REQUIRED MAP CONTENT', '\n\n'.join(content)))
    route_text = []
    for key, route in sorted(connections.items()):
        chain = ' -> '.join(entities[k]['name'] for k in [route['from'], *route['via'], route['to']])
        text = (f"{key}: {route['kind']}; {chain}. "
                + ('Traversable.' if route['traversable'] else 'Intentionally blocked or impassable.')
                + ' Route shape: ' + describe_path(route['path']) + '. ' + route['appearance'])
        if route['width_cells'] is not None:
            text += f" Keep a clear width of at least {route['width_cells']} grid cells; the grid need not be drawn."
        route_text.append(text)
    if route_text:
        sections.append(('ROUTES AND ACCESS', '\n'.join(route_text)))
    relationship_text = [f"{r['strength'].upper()}: {entities[r['from']]['name']} {r['relation'].replace('_',' ')} {entities[r['to']]['name']}. {r['detail']}"
                         for r in spec['relationships'] if r['from'] in entities and r['to'] in entities]
    if relationship_text:
        sections.append(('SPATIAL RELATIONSHIPS', '\n'.join(relationship_text)))
    play = spec['gameplay']
    gameplay_text = 'Affordances: ' + '; '.join(play['affordances']) + '\nPreserve: ' + '; '.join(play['must_preserve'])
    if play['minimum_path_width_cells'] is not None:
        gameplay_text += f"\nAll designated traversable routes need at least {play['minimum_path_width_cells']} cells of clear width."
    if grid['type'] == 'square':
        gameplay_text += f"\nCompose against an underlying {grid['columns']} column by {grid['rows']} row square layout. Each cell represents {grid['units_per_cell']} {grid['units']}. This is a spacing guide even when no grid is painted."
    if play['require_reachability']:
        gameplay_text += '\nKeep the declared traversable routes visibly continuous between entry points and objectives; do not seal openings with props or decoration.'
    sections.append(('PLAYABILITY', gameplay_text))
    if grid['render'] == 'baked':
        grid_text = f"Paint a regular {grid['type']} grid. "
        if grid['type'] == 'square':
            grid_text += f"Requested layout: {grid['columns']} columns and {grid['rows']} rows. "
        else:
            grid_text += f"Orientation: {grid['hex_orientation']}. "
        grid_text += 'No cell numbers unless explicitly included in the label list.'
    else:
        grid_text = 'Do not paint a square grid, hex grid, coordinate numbers or grid intersections. Grid setup is handled separately.'
    if annotations['label_mode'] == 'baked':
        label_text = 'Paint only these exact text strings, preserving spelling: ' + '; '.join(
            f"{json.dumps(label['text'],ensure_ascii=False)} at {label['anchor'][0]:.1%} across / {label['anchor'][1]:.1%} down, rotation {label['rotation_deg']} degrees"
            for label in labels) + '. Typography: ' + annotations['typography']
    else:
        label_text = 'Do not paint any titles, names, text, numbers or legends. Location names in these instructions identify objects only; lettering is a separate layer.'
    zone_text = '; '.join(describe_bounds(zone['bounds']) + ': ' + zone['purpose'] for zone in annotations['clear_zones'])
    sections.append(('GRID, TEXT AND UI', grid_text + '\n' + label_text + '\nDo not draw VTT pins, tokens, mouse pointers, toolbars or interface chrome. '
                     + ('Keep these regions visually quiet for overlays, without drawing blank boxes: ' + zone_text if zone_text else '')))
    references = []
    attachments = []
    for reference in spec['inspiration']['references']:
        references.append(f"Reference {reference['id']}, role {reference['role']}: use " + '; '.join(reference['use_traits'])
                          + '. Ignore ' + '; '.join(reference['ignore_traits']) + '.')
        if reference['kind'] == 'image':
            attachments.append({'source':reference['source'],'role':reference['role']})
    if production['action'] == 'edit_existing':
        attachments.insert(0, {'source':production['base_image_reference'],'role':'approved_edit_base'})
    if references:
        sections.append(('REFERENCE DIRECTION', '\n'.join(references) + '\nUse references only for their assigned roles; create the specified new geography unless a layout reference explicitly requires otherwise.'))
    sections.append(('FINAL PRIORITIES',
        'Required objects, their quantities, spatial relationships and readable routes take precedence over decorative density. '
        + 'Do not replace a difficult required feature with a generic substitute.\nMust include: '
        + '; '.join(production['must_include']) + '\nAvoid: ' + '; '.join(production['must_avoid'])))
    instructions = '\n\n'.join(f'{heading}\n{text}' for heading,text in sections)
    checks = [
        'Confirm actual image dimensions, aspect ratio and export format; do not infer them from the requested settings.',
        'Compare each required landmark, requested quantity and distinctive detail with the spec at full size.',
        'Verify the main focal hierarchy at thumbnail size; check small detail does not overwhelm routes.',
        'Inspect physical route continuity, bridges, river outlets, openings, stairs and occlusion; graph validity alone is insufficient.',
        'Confirm no GM-only information, text or markers leaked into a player image.',
        'Calibrate the actual raster to the VTT grid and test representative token movement before play.',
        'After an edit, compare unchanged regions to the approved base; do not assume identical geometry.'
    ]
    checks += [f"Check {entity['name']}: quantity {entity['quantity']}; " + '; '.join(entity['must_show'])
               for entity in entities.values() if entity['importance'] != 'ambient']
    compiled: dict[str, Any] = {
        'compiler_version':COMPILER_VERSION,'source_sha256':canonical_hash(spec),'map_id':spec['id'],
        'revision':spec['revision'],'audience':audience,'image_instructions':instructions,
        'attachments_required':attachments,
        'postproduction':{
            'target_pixels':spec['canvas']['target_pixels'],'output_format':production['output_format'],
            'grid':copy.deepcopy(grid),'label_mode':annotations['label_mode'],'labels':labels,
            'typography':annotations['typography'],'marker_destination':annotations['markers'],
            'marker_candidates':[{'entity_id':key,'name':entity['name'],'anchor':list(_center(entity))}
                                      for key,entity in entities.items() if entity['importance']!='ambient'] if annotations['markers']!='none' else [],
            'status':'plan_only_not_exported',
            'calibration_note':'Overlay positions are design targets; align to the actual generated art. No SVG layers, VTT walls, lighting, tokens or scene file have been created.'
        },
        'acceptance_checks':checks,'warnings':warnings,
        'validation':{'schema':'pass','structured_rules':'pass','image_review':'not_run','errors':[],'warnings':warnings},
        'image_status':'not_generated'
    }
    compiled['atlas_setup'] = atlas_setup_plan(
        spec, audience, labels, compiled['postproduction']['marker_candidates'])
    if audience == 'gm':
        compiled['private_gm_notes']={key:entity['gm_notes'] for key,entity in spec['entities'].items() if entity['gm_notes']}
    return compiled


def envelope(spec: dict[str, Any], compiled: dict[str, Any]) -> dict[str, Any]:
    return {'stage':'ready','questions':[],'concept_options':[],'assumptions':[],
            'map_spec':spec,'changes':[],'compiled':compiled,'validation':compiled['validation']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['validate','compile']:
        p = sub.add_parser(name)
        p.add_argument('spec', help='Canonical full map spec, not a sparse starter brief')
        p.add_argument('--audience', choices=['player','gm'])
        p.add_argument('-o','--output')
        if name == 'compile':
            p.add_argument('--render-brief', action='store_true', help='Only the audience-filtered compiled object, without the private master spec')
            p.add_argument('--text', action='store_true', help='Only image_instructions as plain text')
    p = sub.add_parser('patch')
    p.add_argument('spec'); p.add_argument('patch')
    p.add_argument('-o','--output',required=True)
    p.add_argument('--allow-locked', action='append', default=[], metavar='POINTER', help='Explicitly approve changing this exact locked path for this patch')
    args = parser.parse_args()
    try:
        spec = load_json(args.spec)
        if args.command == 'validate':
            errors, warnings = validate_spec(spec, args.audience)
            result = {'valid':not errors,'errors':errors,'warnings':warnings,'image_review':'not_run'}
        elif args.command == 'patch':
            result = patch_spec(spec, load_json(args.patch), args.allow_locked)
            errors = []
        else:
            compiled = compile_spec(spec, args.audience)
            result = compiled if args.render_brief else envelope(spec, compiled)
            if args.text:
                result = compiled['image_instructions']
            errors = []
        text = result + '\n' if isinstance(result,str) else dump(result)
        if args.output:
            # Never clobber the input master or patch accidentally.
            output = Path(args.output).resolve()
            inputs = {Path(args.spec).resolve()}
            if args.command == 'patch':
                inputs.add(Path(args.patch).resolve())
            if output in inputs:
                raise ValueError('Choose a separate output path; in-place overwrites are disabled.')
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(text,encoding='utf-8')
        else:
            sys.stdout.write(text)
        return 2 if errors else 0
    except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
        sys.stderr.write(dump({'error':str(exc)}))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
