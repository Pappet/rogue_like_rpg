"""JSON (de)serialization for ECS components, entities and map tiles.

Components are plain dataclasses (see game/components.py), so encoding is
generic: enums store their value, tuples become lists, nested dataclasses
recurse. Decoding is driven by the dataclass field type hints, which
restores enums, tuples and nested types without per-component code.

Entity ids are NOT stable across save/load. Components that reference
other entities by id (Inventory.items, Equipment.slots) are remapped by
SaveService after the entities have been recreated. Transient combat/UI
components are skipped entirely.
"""

import dataclasses
import types
import typing
from enum import Enum

import game.components as components_module
from game.components import (
    FCT,
    Action,
    AttackIntent,
    MovementRequest,
    PathData,
    Targeting,
)
from game.map.map_container import MapContainer
from game.map.map_layer import MapLayer
from game.map.tile import Tile, VisibilityState

# Components that never survive a save (in-flight per-frame state).
TRANSIENT_COMPONENT_TYPES = (MovementRequest, AttackIntent, Targeting, FCT, PathData)

# All serializable dataclasses by name (components + nested types like Action).
SERIALIZABLE_TYPES: dict[str, type] = {
    cls.__name__: cls for cls in components_module.KNOWN_COMPONENT_TYPES if dataclasses.is_dataclass(cls)
}
SERIALIZABLE_TYPES[Action.__name__] = Action

_type_hint_cache: dict[type, dict] = {}


def _hints(cls: type) -> dict:
    if cls not in _type_hint_cache:
        _type_hint_cache[cls] = typing.get_type_hints(cls)
    return _type_hint_cache[cls]


# --- Encoding ---------------------------------------------------------------


def _encode_value(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return [_encode_value(v) for v in value]
    if isinstance(value, dict):
        return [[_encode_value(k), _encode_value(v)] for k, v in value.items()]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return encode_dataclass(value)
    return value


def encode_dataclass(obj) -> dict:
    """Encode a component/dataclass instance into a JSON-compatible dict."""
    data = {f.name: _encode_value(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    return {"__type__": type(obj).__name__, "data": data}


# --- Decoding ---------------------------------------------------------------


def _decode_value(annotation, raw):
    if raw is None:
        return None
    origin = typing.get_origin(annotation)

    if origin in (types.UnionType, typing.Union):
        for arg in typing.get_args(annotation):
            if arg is not type(None):
                return _decode_value(arg, raw)
        return raw
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(raw)
    if origin is tuple or annotation is tuple:
        args = typing.get_args(annotation)
        if args and Ellipsis not in args:
            return tuple(_decode_value(a, r) for a, r in zip(args, raw, strict=False))
        inner = args[0] if args else None
        return tuple(_decode_value(inner, r) if inner else r for r in raw)
    if origin is list or annotation is list:
        args = typing.get_args(annotation)
        inner = args[0] if args else None
        return [_decode_value(inner, r) if inner is not None else r for r in raw]
    if origin is dict or annotation is dict:
        args = typing.get_args(annotation)
        k_ann, v_ann = args if args else (None, None)
        return {_decode_value(k_ann, k) if k_ann else k: _decode_value(v_ann, v) if v_ann else v for k, v in raw}
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return decode_dataclass(raw)
    return raw


def decode_dataclass(encoded: dict):
    """Reverse of encode_dataclass()."""
    cls = SERIALIZABLE_TYPES.get(encoded["__type__"])
    if cls is None:
        raise ValueError(f"Unknown serialized type '{encoded['__type__']}'")
    hints = _hints(cls)
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name in encoded["data"]:
            kwargs[f.name] = _decode_value(hints.get(f.name), encoded["data"][f.name])
    return cls(**kwargs)


# --- Entity helpers ----------------------------------------------------------


def encode_components_of(world, entity: int) -> list[dict]:
    """Encode all persistent components of a live entity."""
    encoded = []
    for comp in world.components_for_entity(entity):
        if isinstance(comp, TRANSIENT_COMPONENT_TYPES):
            continue
        encoded.append(encode_dataclass(comp))
    return encoded


def encode_frozen_entities(frozen: list[list]) -> list[list[dict]]:
    """Encode a MapContainer.frozen_entities structure."""
    return [[encode_dataclass(c) for c in comps if not isinstance(c, TRANSIENT_COMPONENT_TYPES)] for comps in frozen]


def decode_frozen_entities(encoded: list[list[dict]]) -> list[list]:
    return [[decode_dataclass(c) for c in comps] for comps in encoded]


# --- Map helpers --------------------------------------------------------------


def encode_map(container: MapContainer) -> dict:
    """Encode a MapContainer (tile grids + frozen entities + metadata)."""
    layers = []
    for layer in container.layers:
        layers.append(
            {
                "type_ids": [[t._type_id or "floor_stone" for t in row] for row in layer.tiles],
                "visibility": [[t.visibility_state.name for t in row] for row in layer.tiles],
                "rounds": [[t.rounds_since_seen for t in row] for row in layer.tiles],
            }
        )
    return {
        "layers": layers,
        "frozen_entities": encode_frozen_entities(container.frozen_entities),
        "last_visited_turn": container.last_visited_turn,
        "arrival_pos": list(container.arrival_pos) if container.arrival_pos else None,
    }


def decode_map(encoded: dict) -> MapContainer:
    layers = []
    for layer_data in encoded["layers"]:
        tiles = []
        for y, row in enumerate(layer_data["type_ids"]):
            tile_row = []
            for x, type_id in enumerate(row):
                tile = Tile(type_id=type_id)
                tile.visibility_state = VisibilityState[layer_data["visibility"][y][x]]
                tile.rounds_since_seen = layer_data["rounds"][y][x]
                tile_row.append(tile)
            tiles.append(tile_row)
        layers.append(MapLayer(tiles))

    arrival = encoded.get("arrival_pos")
    container = MapContainer(layers, arrival_pos=tuple(arrival) if arrival else None)
    container.frozen_entities = decode_frozen_entities(encoded["frozen_entities"])
    container.last_visited_turn = encoded.get("last_visited_turn", 0)
    return container
