import esper
import math
from config import GameStates, TILE_SIZE
from ecs.components import Position, Renderable, Stats, Inventory, Targeting, Action, ActionList
from map.tile import VisibilityState

class ActionSystem(esper.Processor):
    def __init__(self, map_container, turn_system):
        self.map_container = map_container
        self.turn_system = turn_system

    def process(self, *args, **kwargs):
        # This could handle animations or time-based action logic
        pass

    def start_targeting(self, entity, action):
        # 1. Check resources
        stats = esper.component_for_entity(entity, Stats)
        if action.cost_mana > stats.mana:
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

            # 2. Check visibility (LoS)
            is_visible = False
            for layer in self.map_container.layers:
                if 0 <= new_y < len(layer.tiles) and 0 <= new_x < len(layer.tiles[new_y]):
                    if layer.tiles[new_y][new_x].visibility_state == VisibilityState.VISIBLE:
                        is_visible = True
                        break
            
            if is_visible:
                targeting.target_x = new_x
                targeting.target_y = new_y
        except KeyError:
            pass

    def confirm_action(self, entity):
        try:
            targeting = esper.component_for_entity(entity, Targeting)
            
            # Check visibility of target tile one last time
            is_visible = False
            for layer in self.map_container.layers:
                if 0 <= targeting.target_y < len(layer.tiles) and 0 <= targeting.target_x < len(layer.tiles[targeting.target_y]):
                    if layer.tiles[targeting.target_y][targeting.target_x].visibility_state == VisibilityState.VISIBLE:
                        is_visible = True
                        break
            
            if not is_visible:
                return False

            stats = esper.component_for_entity(entity, Stats)
            
            # Final resource check
            if targeting.action.cost_mana > stats.mana:
                self.cancel_targeting(entity)
                return False

            # Consume resources
            stats.mana -= targeting.action.cost_mana
            
            # Execute action logic (for now just print and end turn)
            print(f"Executed {targeting.action.name} at ({targeting.target_x}, {targeting.target_y})")
            
            self.cancel_targeting(entity)
            self.turn_system.end_player_turn()
            return True
        except KeyError:
            return False

    def cancel_targeting(self, entity):
        if esper.has_component(entity, Targeting):
            esper.remove_component(entity, Targeting)
        self.turn_system.current_state = GameStates.PLAYER_TURN
