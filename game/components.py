import inspect
import sys
from dataclasses import dataclass, field
from enum import Enum


class AIState(str, Enum):
    IDLE = "idle"
    WANDER = "wander"
    CHASE = "chase"
    TALK = "talk"
    WORK = "work"
    PATROL = "patrol"
    SOCIALIZE = "socialize"
    SLEEP = "sleep"


# Schedule activity strings -> AI states (shared by ScheduleSystem and
# WorldSimulationService).
ACTIVITY_TO_STATE = {
    "WORK": AIState.WORK,
    "PATROL": AIState.PATROL,
    "SOCIALIZE": AIState.SOCIALIZE,
    "SLEEP": AIState.SLEEP,
    "IDLE": AIState.IDLE,
    "WANDER": AIState.WANDER,
}


class Alignment(str, Enum):
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"


class SlotType(str, Enum):
    HEAD = "head"
    BODY = "body"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    FEET = "feet"
    ACCESSORY = "accessory"


@dataclass
class PlayerTag:
    pass


@dataclass
class TemplateId:
    """Stores the registry template ID the entity was created from."""

    id: str = ""


@dataclass
class Position:
    x: int
    y: int
    layer: int = 0


@dataclass
class Portal:
    target_map_id: str
    target_x: int
    target_y: int
    target_layer: int = 0
    name: str = "Portal"
    travel_ticks: int = 1


@dataclass
class Renderable:
    sprite: str
    layer: int
    color: tuple[int, int, int] = (255, 255, 255)


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
    # Base fields for Effective Stats pattern
    base_hp: int = 0
    base_max_hp: int = 0
    base_power: int = 0
    base_defense: int = 0
    base_mana: int = 0
    base_max_mana: int = 0
    base_perception: int = 0
    base_intelligence: int = 0
    max_carry_weight: float = 20.0


@dataclass
class EffectiveStats:
    hp: int
    max_hp: int
    power: int
    defense: int
    mana: int
    max_mana: int
    perception: int
    intelligence: int


@dataclass
class StatModifiers:
    hp: int = 0
    power: int = 0
    defense: int = 0
    mana: int = 0
    perception: int = 0
    intelligence: int = 0


@dataclass
class Portable:
    weight: float  # kg


@dataclass
class Equippable:
    slot: SlotType


@dataclass
class ItemMaterial:
    material: str  # e.g., 'iron', 'wood', 'glass'


@dataclass
class Inventory:
    items: list = field(default_factory=list)


@dataclass
class Equipment:
    slots: dict[SlotType, int | None] = field(default_factory=lambda: {s: None for s in SlotType})


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
class AttackIntent:
    target_entity: int


@dataclass
class Action:
    name: str
    cost_mana: int = 0
    cost_arrows: int = 0
    range: int = 0
    requires_targeting: bool = False
    targeting_mode: str = "auto"  # "auto" or "manual"


@dataclass
class ActionList:
    actions: list[Action] = field(default_factory=list)
    selected_idx: int = 0


@dataclass
class Targeting:
    origin_x: int
    origin_y: int
    target_x: int
    target_y: int
    range: int
    mode: str  # 'auto' or 'manual'
    action: Action
    potential_targets: list[int] = field(default_factory=list)  # Entity IDs
    target_idx: int = 0


@dataclass
class Corpse:
    pass


@dataclass
class Description:
    base: str
    wounded_text: str = ""
    wounded_threshold: float = 0.5

    def get(self, stats=None) -> str:
        if (
            stats is not None
            and self.wounded_text
            and stats.max_hp > 0
            and stats.hp / stats.max_hp <= self.wounded_threshold
        ):
            return self.wounded_text
        return self.base


@dataclass
class AIBehaviorState:
    state: AIState
    alignment: Alignment


@dataclass
class Activity:
    current_activity: str = "IDLE"
    target_pos: tuple[int, int] | None = None
    home_pos: tuple[int, int] | None = None
    # Set by NeedsSystem while a need (e.g. "EAT") preempts the schedule;
    # ScheduleSystem skips entities with an active override.
    need_override: str | None = None


@dataclass
class ChaseData:
    last_known_x: int
    last_known_y: int
    turns_without_sight: int = 0


@dataclass
class PathData:
    path: list[tuple[int, int]]
    destination: tuple[int, int]


@dataclass
class LootTable:
    entries: list[tuple[str, float]] = field(default_factory=list)


@dataclass
class WanderData:
    """Stub component for wander state. Fields added when wander behavior is implemented."""

    pass


@dataclass
class Consumable:
    effect_type: str
    amount: int
    consumed_on_use: bool = True


@dataclass
class Schedule:
    schedule_id: str


@dataclass
class FCT:
    text: str
    color: tuple[int, int, int]
    vx: float
    vy: float
    ttl: float
    max_ttl: float
    offset_x: float = 0.0
    offset_y: float = 0.0


@dataclass
class MapBound:
    """Marker component. Indicates entity belongs to the current map and should be frozen along with it."""

    pass


@dataclass
class Purse:
    """Gold carried by an entity (player or NPC)."""

    gold: int = 0


@dataclass
class Value:
    """Base trade value of an item in gold."""

    amount: int = 0


@dataclass
class Merchant:
    """Marks an NPC as a trader. Stock is a list of item template ids —
    fungible goods, not item entities, so freeze/thaw never dangles."""

    stock: list[str] = field(default_factory=list)


@dataclass
class Needs:
    """Physical needs that can preempt an NPC's schedule (ROADMAP Phase D).

    hunger rises by hunger_rate per in-game hour; above eat_threshold the
    NeedsSystem overrides the schedule with an EAT activity.
    """

    hunger: float = 0.0
    hunger_rate: float = 2.0  # points per in-game hour
    eat_threshold: float = 70.0
    eat_duration_ticks: int = 30  # half an hour per meal
    eating_ticks_left: int = 0


KNOWN_COMPONENT_TYPES = []
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj) and obj.__module__ == __name__:
        KNOWN_COMPONENT_TYPES.append(obj)
