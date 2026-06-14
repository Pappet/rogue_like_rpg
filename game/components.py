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
class Skills:
    """Learn-by-doing character progression (ROADMAP Phase I).

    Accumulated XP per skill id (e.g. "smithing", "combat"). Level is derived
    from XP via SkillService — no stored level — so the component stays a flat,
    trivially-serializable dict. SkillService is the only writer.
    """

    xp: dict[str, int] = field(default_factory=dict)


@dataclass
class Quality:
    """Crafted-item grade (ROADMAP Phase J).

    Tier indexes ``crafting_quality.QUALITY_TIERS`` (1 == standard). Equippable
    crafts carry one; the grade is reflected immersively in the item's Name
    ("Masterwork Iron Sword") and baked into its StatModifiers/Value, so no
    numeric "+N" suffix is shown.
    """

    tier: int = 1


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
    # Lit only between dusk and dawn (street torches, campfires).
    night_only: bool = False


@dataclass
class MovementRequest:
    dx: int
    dy: int


@dataclass
class AttackIntent:
    target_entity: int
    power_multiplier: float = 1.0  # abilities hit harder than a plain bump


@dataclass
class Bleeding:
    """Status effect: loses HP at the end of each round (ROADMAP Phase G5).

    Applied by critical hits; ticked once per round by StatusEffectSystem.
    """

    damage_per_turn: int = 1
    turns_left: int = 3


@dataclass
class Action:
    name: str
    cost_mana: int = 0
    cost_arrows: int = 0
    range: int = 0
    requires_targeting: bool = False
    targeting_mode: str = "auto"  # "auto" or "manual"
    power_multiplier: float = 1.0  # damage scale for attack abilities


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
class PatrolRoute:
    """A guard's looping beat. Assigned by ScheduleSystem the first time a
    PATROL entry with a `route` is encountered. `index` is staggered per
    entity so guards sharing a route walk it out of phase instead of marching
    as one pack. Recomputed on thaw, so it is treated as transient state."""

    waypoints: list[tuple[int, int]] = field(default_factory=list)
    index: int = 0


@dataclass
class Residence:
    """Where an NPC belongs in town, assigned once at village build by
    HousingService (capacity-based housing).

    - `hearth_pos`: the settlement's social centre (campfire, else tavern).
      SOCIALIZE entries with `target_meta: "hearth"` head here, so evening
      gatherings happen at the *real* fire of whichever village the NPC is in.
    - `housed`: True if the NPC owns a bed; it sleeps at home_pos. When False
      the NPC has no bed and instead drifts to `gather_pos` at night.
    - `gather_pos`: the campfire/tavern spot a bedless NPC (or a guard on the
      night watch) mills about after dark instead of sleeping."""

    hearth_pos: tuple[int, int] | None = None
    housed: bool = True
    gather_pos: tuple[int, int] | None = None


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
class Animal:
    """Marker: wildlife. Bumping attacks (no dialogue), and hunting
    neutral animals never costs reputation."""

    pass


@dataclass
class Hidden:
    """Marker: entity is concealed until revealed (ROADMAP Phase F).

    Hidden entities are not rendered, not listed by the tooltip and not
    picked up. VisibilitySystem reveals them when the player gets close
    enough (perception-gated).
    """

    reveal_radius: int = 2


@dataclass
class Skirmisher:
    """Locked in battle with a rival faction (travel encounters).

    AISystem routes entities with this component to skirmish behavior:
    attack the nearest living Skirmisher of another side instead of
    reacting to the player. Removed when no opponents remain.
    """

    side: str = ""


@dataclass
class QuestGiver:
    """Marker: bumping this NPC opens the quest window (ROADMAP Phase E)."""

    pass


@dataclass
class Innkeeper:
    """Marker: bumping this NPC opens the rest/sleep duration picker."""

    pass


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
