import json
import os
import esper
from ecs.components import (
    Position, Renderable, Stats, Name, Inventory, TurnOrder,
    ActionList, Action, Blocker, Equipment, EffectiveStats, HotbarSlots, PlayerTag
)
from config import SpriteLayer

_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'assets', 'data', 'player.json')

def _load_player_data():
    with open(_DATA_PATH, 'r') as f:
        return json.load(f)

def _build_action(data: dict) -> Action:
    """Build an Action from a JSON dict."""
    return Action(
        name=data["name"],
        cost_mana=data.get("cost_mana", 0),
        cost_arrows=data.get("cost_arrows", 0),
        range=data.get("range", 0),
        requires_targeting=data.get("requires_targeting", False),
        targeting_mode=data.get("targeting_mode", "auto"),
    )

class PartyService:
    def __init__(self):
        pass

    def create_initial_party(self, x: int, y: int):
        data = _load_player_data()

        # Build actions from JSON
        actions = [_build_action(a) for a in data["actions"]]
        actions_by_name = {a.name: a for a in actions}
        # Wait action is hotbar-only, not in the main action list
        wait_action = Action(name="Wait")
        actions_by_name["Wait"] = wait_action

        # Build hotbar mapping
        hotbar = {i: None for i in range(1, 10)}
        for slot_str, action_name in data["hotbar"].items():
            hotbar[int(slot_str)] = actions_by_name[action_name]

        layer = SpriteLayer[data["sprite_layer"]].value
        color = tuple(data["color"])

        stat_fields = {
            k: data[k] for k in
            ("hp", "max_hp", "power", "defense", "mana", "max_mana", "perception", "intelligence")
        }

        player_entity = esper.create_entity(
            PlayerTag(),
            Position(x, y),
            Renderable(data["sprite"], layer, color),
            Stats(
                **stat_fields,
                **{f"base_{k}": v for k, v in stat_fields.items()},
                max_carry_weight=data.get("max_carry_weight", 20.0),
            ),
            Equipment(),
            EffectiveStats(**stat_fields),
            Name(data["name"]),
            Blocker(),
            Inventory(),
            TurnOrder(priority=0),
            ActionList(actions=actions),
            HotbarSlots(slots=hotbar),
        )

        return player_entity

def get_entity_closure(world, root_entity):
    """Find all entities that should travel with the root_entity (e.g., inventory items)."""
    closure = {root_entity}
    stack = [root_entity]

    while stack:
        current = stack.pop()
        try:
            inventory = world.component_for_entity(current, Inventory)
            for item_id in inventory.items:
                if item_id not in closure:
                    closure.add(item_id)
                    stack.append(item_id)
        except KeyError:
            pass

    return list(closure)
