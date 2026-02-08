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
    mana: int
    max_mana: int
    perception: int
    intelligence: int

@dataclass
class Inventory:
    items: List = field(default_factory=list)

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
class ActionList:
    actions: List[str]
    selected_idx: int = 0
