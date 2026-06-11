import logging
import math

import esper

from config import GameStates, LogCategory
from game.components import (
    AIBehaviorState,
    AIState,
    Description,
    EffectiveStats,
    ItemMaterial,
    Name,
    Portable,
    Portal,
    Position,
    Renderable,
    Stats,
    Targeting,
)
from game.map.tile import VisibilityState
from game.map.tile_registry import tile_registry
from game.systems.map_aware_system import MapAwareSystem

logger = logging.getLogger(__name__)


class ActionSystem(esper.Processor, MapAwareSystem):
    def __init__(self, turn_system):
        esper.Processor.__init__(self)
        MapAwareSystem.__init__(self)
        self.turn_system = turn_system

    @staticmethod
    def get_detailed_description(world, entity_id) -> str:
        """Generates a detailed physical description for an item or entity."""
        desc_comp = world.try_component(entity_id, Description)
        material_comp = world.try_component(entity_id, ItemMaterial)
        portable_comp = world.try_component(entity_id, Portable)

        # We might also want stats for wounded descriptions
        stats_comp = world.try_component(entity_id, Stats)

        parts = []
        if desc_comp:
            parts.append(desc_comp.get(stats_comp))

        if material_comp:
            parts.append(f"Material: {material_comp.material}")

        if portable_comp:
            parts.append(f"Weight: {portable_comp.weight}kg")

        return "\n".join(parts)

    def process(self, *args, **kwargs):
        # This could handle animations or time-based action logic
        pass

    def perform_action(self, entity, action):
        """Executes a non-targeting action."""
        if action.name == "Wait":
            esper.dispatch_event("log_message", "You wait...")
            if self.turn_system:
                self.turn_system.end_player_turn()
            return True

        if action.name == "Enter Portal":
            pos = esper.component_for_entity(entity, Position)

            # Find portal at current position
            portal_found = False
            for p_ent, (p_pos, portal) in esper.get_components(Position, Portal):
                if p_pos.x == pos.x and p_pos.y == pos.y and p_pos.layer == pos.layer:
                    portal_found = True
                    esper.dispatch_event("log_message", f"You enter the {portal.name}...")
                    esper.dispatch_event(
                        "map_change_requested",
                        {
                            "target_map_id": portal.target_map_id,
                            "target_x": portal.target_x,
                            "target_y": portal.target_y,
                            "target_layer": portal.target_layer,
                            "travel_ticks": portal.travel_ticks,
                        },
                    )
                    # Note: map_change_requested is handled by MapTransitionService (wired in GameplayState)
                    # We end turn here, but the map transition might reset things.
                    self.turn_system.end_player_turn()
                    break

            if not portal_found:
                esper.dispatch_event("log_message", "There is no portal here.", None, LogCategory.ALERT)
                return False
            return True

        return False

    def start_targeting(self, entity, action):
        # 1. Check resources using effective stats
        eff = esper.try_component(entity, EffectiveStats) or esper.component_for_entity(entity, Stats)
        if action.cost_mana > eff.mana:
            return False  # Not enough mana

        # 2. Transition to targeting mode
        pos = esper.component_for_entity(entity, Position)

        targeting = Targeting(
            origin_x=pos.x,
            origin_y=pos.y,
            target_x=pos.x,
            target_y=pos.y,
            range=action.range,
            mode=action.targeting_mode,
            action=action,
        )

        if action.targeting_mode == "inspect":
            targeting.range = eff.perception

        if action.targeting_mode == "auto":
            # Find potential targets in LoS and range
            targets = self.find_potential_targets(entity, pos.x, pos.y, action.range)
            if targets:
                targeting.potential_targets = targets
                target_pos = esper.component_for_entity(targets[0], Position)
                targeting.target_x = target_pos.x
                targeting.target_y = target_pos.y
            else:
                # No targets found, maybe still allow manual targeting or just fail?
                # If auto-targeting finds nothing, we might want to still enter targeting
                # but with the player's position as initial target.
                pass

        esper.add_component(entity, targeting)
        self.turn_system.current_state = GameStates.TARGETING
        return True

    def find_potential_targets(self, source_entity, x, y, range_limit):
        targets = []
        for ent, (pos, rend) in esper.get_components(Position, Renderable):
            if ent == source_entity:
                continue

            # Check if in range
            dist = math.sqrt((pos.x - x) ** 2 + (pos.y - y) ** 2)
            if dist > range_limit:
                continue

            # Check if in visibility
            is_visible = False
            for layer in self._map_container.layers:
                if (
                    0 <= pos.y < len(layer.tiles)
                    and 0 <= pos.x < len(layer.tiles[pos.y])
                    and layer.tiles[pos.y][pos.x].visibility_state == VisibilityState.VISIBLE
                ):
                    is_visible = True
                    break

            if is_visible:
                targets.append(ent)

        return targets

    def cycle_targets(self, entity, direction=1):
        targeting = esper.try_component(entity, Targeting)
        if not targeting or not targeting.potential_targets:
            return

        targeting.target_idx = (targeting.target_idx + direction) % len(targeting.potential_targets)
        target_ent = targeting.potential_targets[targeting.target_idx]
        target_pos = esper.try_component(target_ent, Position)
        if target_pos:
            targeting.target_x = target_pos.x
            targeting.target_y = target_pos.y

    def move_cursor(self, entity, dx, dy):
        targeting = esper.try_component(entity, Targeting)
        if not targeting:
            return

        new_x = targeting.target_x + dx
        new_y = targeting.target_y + dy

        # 1. Check range from origin
        dist = math.sqrt((new_x - targeting.origin_x) ** 2 + (new_y - targeting.origin_y) ** 2)
        if dist > targeting.range:
            return

        # 2. Check tile accessibility (any previously-seen tile is reachable)
        is_accessible = False
        for layer in self._map_container.layers:
            if (
                0 <= new_y < len(layer.tiles)
                and 0 <= new_x < len(layer.tiles[new_y])
                and layer.tiles[new_y][new_x].visibility_state != VisibilityState.UNEXPLORED
            ):
                is_accessible = True
                break

        if is_accessible:
            targeting.target_x = new_x
            targeting.target_y = new_y

    def confirm_action(self, entity):
        targeting = esper.try_component(entity, Targeting)
        if not targeting:
            return False

        # Check visibility of target tile — mode-aware gate
        tile_visibility = VisibilityState.UNEXPLORED
        target_tile = None
        for layer in self._map_container.layers:
            if 0 <= targeting.target_y < len(layer.tiles) and 0 <= targeting.target_x < len(
                layer.tiles[targeting.target_y]
            ):
                t = layer.tiles[targeting.target_y][targeting.target_x]
                if t.visibility_state != VisibilityState.UNEXPLORED:
                    target_tile = t
                    tile_visibility = t.visibility_state
                    break

        if targeting.action.targeting_mode == "inspect":
            if tile_visibility == VisibilityState.UNEXPLORED:
                return False
        else:
            if tile_visibility != VisibilityState.VISIBLE:
                return False

        # Final resource check using effective stats
        eff = esper.try_component(entity, EffectiveStats) or esper.component_for_entity(entity, Stats)
        if targeting.action.cost_mana > eff.mana:
            self.cancel_targeting(entity)
            return False

        # Consume resources from base stats
        stats = esper.component_for_entity(entity, Stats)
        stats.mana -= targeting.action.cost_mana

        # Dispatch inspection output for inspect mode
        if targeting.action.targeting_mode == "inspect":
            # Look up tile type from registry
            if target_tile is not None and target_tile._type_id is not None:
                tile_type = tile_registry.get(target_tile._type_id)
                if tile_type is not None:
                    tile_name = tile_type.name
                    tile_desc = tile_type.base_description
                else:
                    tile_name = "Unknown tile"
                    tile_desc = ""
            else:
                tile_name = "Unknown tile"
                tile_desc = ""

            # Always dispatch tile name in yellow
            esper.dispatch_event("log_message", f"[color=yellow]{tile_name}[/color]")

            # For VISIBLE tiles: dispatch description and entity info
            if tile_visibility == VisibilityState.VISIBLE:
                if tile_desc:
                    esper.dispatch_event("log_message", tile_desc)

                # List all entities at the target position
                for ent, (pos,) in esper.get_components(Position):
                    if ent == entity:
                        continue
                    if pos.x != targeting.target_x or pos.y != targeting.target_y:
                        continue

                    name_comp = esper.try_component(ent, Name)
                    if name_comp is None:
                        continue

                    detailed_desc = ActionSystem.get_detailed_description(esper, ent)

                    # Show name in yellow
                    esper.dispatch_event("log_message", f"[color=yellow]{name_comp.name}[/color]")
                    if detailed_desc:
                        esper.dispatch_event("log_message", detailed_desc)
        else:
            # Execute action logic (for now just print and end turn)
            logger.debug(f"Executed {targeting.action.name} at ({targeting.target_x}, {targeting.target_y})")

        mode = targeting.action.targeting_mode
        self.cancel_targeting(entity)
        if mode != "inspect":
            self.turn_system.end_player_turn()
        return True

    def cancel_targeting(self, entity):
        if esper.has_component(entity, Targeting):
            esper.remove_component(entity, Targeting)
        self.turn_system.current_state = GameStates.PLAYER_TURN

    def wake_up(self, target_entity):
        """Centralized logic to wake up a sleeping entity."""
        behavior = esper.try_component(target_entity, AIBehaviorState)
        if behavior and behavior.state == AIState.SLEEP:
            behavior.state = AIState.IDLE
            name_comp = esper.try_component(target_entity, Name)
            if name_comp:
                esper.dispatch_event("log_message", f"The {name_comp.name} wakes up!", None, LogCategory.ALERT)
            else:
                esper.dispatch_event("log_message", "Something wakes up!", None, LogCategory.ALERT)
