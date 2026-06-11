"""Save/Load of a full game session to a single JSON snapshot (Phase A4).

What gets saved: world clock, world graph state (current location +
discovered flags), all map containers (tiles, visibility, frozen
entities), the active map id and the live player party. ECS systems,
registries and the world graph topology are NOT saved — they are rebuilt
from code/JSON on every boot; the save only carries mutable state.

Entity ids are not stable across sessions: the party is stored with its
old ids and id-bearing components (Inventory.items, Equipment.slots) are
remapped after recreation.
"""

import json
import logging
import os

import esper

from config import SAVE_FILE, LogCategory
from game.components import Equipment, Inventory, Position
from game.services.party_service import get_entity_closure
from game.services.save_serialization import (
    decode_dataclass,
    decode_map,
    encode_components_of,
    encode_map,
)

logger = logging.getLogger(__name__)

SAVE_VERSION = 1


class SaveService:
    """Stateless snapshot save/load against the shared GameContext."""

    @staticmethod
    def save(ctx, filepath: str = SAVE_FILE) -> bool:
        """Write the current session to filepath. Returns True on success."""
        if ctx.player_entity is None:
            logger.warning("Save requested without a player entity — ignored.")
            return False

        active_map = ctx.map_service.get_active_map()
        closure = get_entity_closure(esper, ctx.player_entity)

        # Freeze the active map so ALL maps carry their entities in
        # frozen_entities; thaw again afterwards to restore the session.
        active_map.freeze(esper, exclude_entities=closure)
        try:
            party = [{"old_id": ent, "components": encode_components_of(esper, ent)} for ent in closure]
            data = {
                "version": SAVE_VERSION,
                "clock_ticks": ctx.world_clock.total_ticks,
                "round_counter": ctx.systems.turn_system.round_counter,
                "active_map_id": ctx.map_service.active_map_id,
                "world_graph": {
                    "current_location_id": ctx.world_graph.current_location_id if ctx.world_graph else None,
                    "discovered": [loc.id for loc in ctx.world_graph.locations.values() if loc.discovered]
                    if ctx.world_graph
                    else [],
                },
                "maps": {map_id: encode_map(c) for map_id, c in ctx.map_service.maps.items()},
                "chronicle": ctx.world_chronicle.to_dict() if ctx.world_chronicle else None,
                "economy": ctx.economy.to_dict() if ctx.economy else None,
                "reputation": ctx.reputation.to_dict() if ctx.reputation else None,
                "party": party,
                "player_old_id": ctx.player_entity,
            }
        finally:
            active_map.thaw(esper)

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f)
        logger.info("Game saved to %s", filepath)
        esper.dispatch_event("log_message", "Game saved.", None, LogCategory.SYSTEM)
        return True

    @staticmethod
    def load(ctx, filepath: str = SAVE_FILE) -> bool:
        """Replace the current session with the snapshot. Returns True on success."""
        if not os.path.exists(filepath):
            logger.warning("No save file at %s", filepath)
            return False

        with open(filepath) as f:
            data = json.load(f)
        if data.get("version") != SAVE_VERSION:
            logger.error("Incompatible save version %s", data.get("version"))
            return False

        # Wipe live entities. Event handlers and processors stay registered —
        # they belong to the session's systems, not to the saved state.
        esper.clear_database()

        # Maps
        ctx.map_service.maps = {map_id: decode_map(encoded) for map_id, encoded in data["maps"].items()}
        ctx.map_service.active_map_id = None  # set after thaw below

        # World graph state
        if ctx.world_graph is not None:
            wg = data.get("world_graph", {})
            for location in ctx.world_graph.locations.values():
                location.discovered = location.id in wg.get("discovered", [])
            if wg.get("current_location_id"):
                ctx.world_graph.set_current_location(wg["current_location_id"])

        # Clock & turn flow
        ctx.world_clock.total_ticks = data["clock_ticks"]
        ctx.systems.turn_system.round_counter = data.get("round_counter", data["clock_ticks"] + 1)

        # World chronicle
        if ctx.world_chronicle is not None and data.get("chronicle"):
            ctx.world_chronicle.from_dict(data["chronicle"])

        # Settlement economy
        if ctx.economy is not None and data.get("economy"):
            ctx.economy.from_dict(data["economy"])

        # Reputation
        if ctx.reputation is not None and data.get("reputation"):
            ctx.reputation.from_dict(data["reputation"])

        # Party (with entity-id remapping)
        id_map: dict[int, int] = {}
        created: list[int] = []
        for entry in data["party"]:
            ent = esper.create_entity()
            id_map[entry["old_id"]] = ent
            created.append(ent)
            for comp_encoded in entry["components"]:
                esper.add_component(ent, decode_dataclass(comp_encoded))
        for ent in created:
            if esper.has_component(ent, Inventory):
                inv = esper.component_for_entity(ent, Inventory)
                inv.items = [id_map.get(i, i) for i in inv.items]
            if esper.has_component(ent, Equipment):
                eq = esper.component_for_entity(ent, Equipment)
                eq.slots = {slot: id_map.get(i) if i is not None else None for slot, i in eq.slots.items()}

        ctx.player_entity = id_map[data["player_old_id"]]

        # Activate and thaw the saved active map
        ctx.map_service.set_active_map(data["active_map_id"])
        active_map = ctx.map_service.get_active_map()
        active_map.thaw(esper)

        # Re-point map-aware systems and camera
        for system in ctx.systems.map_aware():
            system.set_map(active_map)
        try:
            pos = esper.component_for_entity(ctx.player_entity, Position)
            ctx.camera.update(pos.x, pos.y)
        except KeyError:
            pass

        logger.info("Game loaded from %s", filepath)
        esper.dispatch_event("log_message", "Game loaded.", None, LogCategory.SYSTEM)
        return True
