from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class Position:
    x: int
    y: int

@dataclass
class Renderable:
    sprite: str
    layer: int
    color: Tuple[int, int, int] = (255, 255, 255)

@dataclass
class Stats:
    hp: int
    max_hp: int
    power: int
    defense: int
    mana: int
    max_mana: int
    perception: int
    intelligence: int

@dataclass
class Inventory:
    items: List = field(default_factory=list)

@dataclass
class Name:
    name: str

@dataclass
class Blocker:
    pass

@dataclass
class AI:
    pass

@dataclass
class TurnOrder:
    priority: int

@dataclass
class LightSource:
    radius: int

@dataclass
class MovementRequest:
    dx: int
    dy: int

@dataclass
class Action:
    name: str
    cost_mana: int = 0
    cost_arrows: int = 0
    range: int = 0
    requires_targeting: bool = False
    targeting_mode: str = "auto" # "auto" or "manual"

@dataclass
class ActionList:
    actions: List[Action] = field(default_factory=list)
    selected_idx: int = 0

@dataclass
class Targeting:
    origin_x: int
    origin_y: int
    target_x: int
    target_y: int
    range: int
    mode: str # 'auto' or 'manual'
    action: Action
    potential_targets: List[int] = field(default_factory=list) # Entity IDs
    target_idx: int = 0
