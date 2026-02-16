import esper
import math
from config import GameStates, TILE_SIZE
from ecs.components import Position, Renderable, Stats, EffectiveStats, Inventory, Targeting, Action, ActionList, Portal, Name, Description
from map.tile import VisibilityState
from map.tile_registry import TileRegistry

class ActionSystem(esper.Processor):
    def __init__(self, map_container, turn_system):
        self.map_container = map_container
        self.turn_system = turn_system

    def set_map(self, map_container):
        self.map_container = map_container

    def process(self, *args, **kwargs):
        # This could handle animations or time-based action logic
        pass

    def perform_action(self, entity, action):
        """Executes a non-targeting action."""
        if action.name == "Enter Portal":
            pos = esper.component_for_entity(entity, Position)
            
            # Find portal at current position
            portal_found = False
            for p_ent, (p_pos, portal) in esper.get_components(Position, Portal):
                if p_pos.x == pos.x and p_pos.y == pos.y and p_pos.layer == pos.layer:
                    portal_found = True
                    esper.dispatch_event("log_message", f"You enter the {portal.name}...")
                    esper.dispatch_event("change_map", {
                        "target_map_id": portal.target_map_id,
                        "target_x": portal.target_x,
                        "target_y": portal.target_y,
                        "target_layer": portal.target_layer
                    })
                    # Note: change_map event will trigger map transition in game_states.py
                    # We end turn here, but the map transition might reset things.
                    self.turn_system.end_player_turn()
                    break
            
            if not portal_found:
                esper.dispatch_event("log_message", "There is no portal here.")
                return False
            return True
        
        return False

    def start_targeting(self, entity, action):
        # 1. Check resources using effective stats
        eff = esper.try_component(entity, EffectiveStats) or esper.component_for_entity(entity, Stats)
        if action.cost_mana > eff.mana:
            return False # Not enough mana
        
        # 2. Transition to targeting mode
        pos = esper.component_for_entity(entity, Position)
        
        targeting = Targeting(
            origin_x=pos.x,
            origin_y=pos.y,
            target_x=pos.x,
            target_y=pos.y,
            range=action.range,
            mode=action.targeting_mode,
            action=action
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
            dist = math.sqrt((pos.x - x)**2 + (pos.y - y)**2)
            if dist > range_limit:
                continue

            # Check if in visibility
            is_visible = False
            for layer in self.map_container.layers:
                if 0 <= pos.y < len(layer.tiles) and 0 <= pos.x < len(layer.tiles[pos.y]):
                    if layer.tiles[pos.y][pos.x].visibility_state == VisibilityState.VISIBLE:
                        is_visible = True
                        break
            
            if is_visible:
                targets.append(ent)
        
        return targets

    def cycle_targets(self, entity, direction=1):
        try:
            targeting = esper.component_for_entity(entity, Targeting)
            if not targeting.potential_targets:
                return
            
            targeting.target_idx = (targeting.target_idx + direction) % len(targeting.potential_targets)
            target_ent = targeting.potential_targets[targeting.target_idx]
            target_pos = esper.component_for_entity(target_ent, Position)
            targeting.target_x = target_pos.x
            targeting.target_y = target_pos.y
        except KeyError:
            pass

    def move_cursor(self, entity, dx, dy):
        try:
            targeting = esper.component_for_entity(entity, Targeting)
            new_x = targeting.target_x + dx
            new_y = targeting.target_y + dy
            
            # 1. Check range from origin
            dist = math.sqrt((new_x - targeting.origin_x)**2 + (new_y - targeting.origin_y)**2)
            if dist > targeting.range:
                return

            # 2. Check tile accessibility (any previously-seen tile is reachable)
            is_accessible = False
            for layer in self.map_container.layers:
                if 0 <= new_y < len(layer.tiles) and 0 <= new_x < len(layer.tiles[new_y]):
                    if layer.tiles[new_y][new_x].visibility_state != VisibilityState.UNEXPLORED:
                        is_accessible = True
                        break

            if is_accessible:
                targeting.target_x = new_x
                targeting.target_y = new_y
        except KeyError:
            pass

    def confirm_action(self, entity):
        try:
            targeting = esper.component_for_entity(entity, Targeting)

            # Check visibility of target tile — mode-aware gate
            tile_visibility = VisibilityState.UNEXPLORED
            target_tile = None
            for layer in self.map_container.layers:
                if 0 <= targeting.target_y < len(layer.tiles) and 0 <= targeting.target_x < len(layer.tiles[targeting.target_y]):
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
                    tile_type = TileRegistry.get(target_tile._type_id)
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

                        desc_comp = esper.try_component(ent, Description)
                        ent_stats = esper.try_component(ent, Stats)

                        if desc_comp is not None:
                            esper.dispatch_event(
                                "log_message",
                                f"[color=white]{name_comp.name}[/color]: {desc_comp.get(ent_stats)}"
                            )
                        else:
                            esper.dispatch_event(
                                "log_message",
                                f"[color=white]{name_comp.name}[/color]"
                            )
            else:
                # Execute action logic (for now just print and end turn)
                print(f"Executed {targeting.action.name} at ({targeting.target_x}, {targeting.target_y})")

            mode = targeting.action.targeting_mode
            self.cancel_targeting(entity)
            if mode != "inspect":
                self.turn_system.end_player_turn()
            return True
        except KeyError:
            return False

    def cancel_targeting(self, entity):
        if esper.has_component(entity, Targeting):
            esper.remove_component(entity, Targeting)
        self.turn_system.current_state = GameStates.PLAYER_TURN
