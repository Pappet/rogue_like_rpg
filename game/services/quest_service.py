"""Quests: authored and simulation-generated requests (ROADMAP Phase E).

Quest model: plain dataclasses owned by this service (not ECS components —
quests belong to the session, not to an entity on a map). Lifecycle:

    offered -> active -> completed -> turned_in
                       \\-> (visit quests auto-complete on arrival)

Authored quests come from assets/data/quests.json. Generated quests are
derived from the simulation when the player arrives at a settlement:

- a good the settlement consumes is nearly out of stock (EconomyService)
  -> a *deliver* request appears at the local quest giver
- a recent wolf chronicle event (WorldChronicleService)
  -> a *kill* request; arriving with it active spawns the wolves if the
     map doesn't have enough — the cause genuinely exists

Turn-in happens at the quest giver of the giver_location. Rewards pay
gold; deliveries melt the items back into the local economy's stock, so
fulfilling the request actually fixes the shortage that created it.
"""

import json
import logging
import random
from dataclasses import asdict, dataclass, field

import esper

from config import LogCategory
from game.components import Equipment, Inventory, PlayerTag, Position, Purse, TemplateId
from game.content.item_registry import item_registry

logger = logging.getLogger(__name__)

# Generation thresholds
GEN_STOCK_THRESHOLD = 2.0  # consumed goods below this stock trigger a request
GEN_DELIVER_COUNT = 2
GEN_DELIVER_REWARD_FACTOR = 2.0  # reward = item value * count * factor
GEN_KILL_COUNT = 2
GEN_KILL_REWARD = 40
GEN_WOLF_EVENT_ID = "wolves_spotted"
GEN_EVENT_MAX_AGE_TICKS = 3 * 24 * 60  # wolf sightings older than 3 days expire


@dataclass
class Quest:
    id: str
    title: str
    description: str
    quest_type: str  # "deliver" | "kill" | "visit"
    giver_location: str
    target: dict
    reward_gold: int
    state: str = "offered"  # offered | active | completed | turned_in
    progress: int = 0
    source: str = "authored"  # authored | generated
    cause_event_id: str = ""  # chronicle event that caused this quest (G2)


# eq=False keeps identity hashing — esper event handlers live in weakref sets.
@dataclass(eq=False)
class QuestService:
    """Owns all quests of a session and tracks their progress."""

    ctx: object = None
    quests: list[Quest] = field(default_factory=list)
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self):
        esper.set_handler("entity_died", self.on_entity_died)

    # --- Loading ------------------------------------------------------------

    def load_authored(self, filepath: str) -> None:
        with open(filepath) as f:
            data = json.load(f)
        known = {q.id for q in self.quests}
        for entry in data:
            if entry["id"] in known:
                continue
            self.quests.append(
                Quest(
                    id=entry["id"],
                    title=entry["title"],
                    description=entry["description"],
                    quest_type=entry["quest_type"],
                    giver_location=entry["giver_location"],
                    target=dict(entry["target"]),
                    reward_gold=int(entry["reward_gold"]),
                    source="authored",
                )
            )
        logger.info("Loaded %d quests (%d total).", len(data), len(self.quests))

    # --- Queries ---------------------------------------------------------------

    def offers_at(self, location_id: str | None) -> list[Quest]:
        return [q for q in self.quests if q.state == "offered" and q.giver_location == location_id]

    def active_quests(self) -> list[Quest]:
        return [q for q in self.quests if q.state in ("active", "completed")]

    def turn_in_candidates(self, location_id: str | None) -> list[Quest]:
        """Active/completed quests that can be turned in here right now."""
        result = []
        for quest in self.active_quests():
            if quest.giver_location != location_id:
                continue
            if quest.quest_type == "deliver":
                if self._count_player_items(quest.target["item"]) >= quest.target["count"]:
                    result.append(quest)
            elif quest.state == "completed":
                result.append(quest)
        return result

    def open_offers_elsewhere(self, location_id: str | None) -> list[Quest]:
        """Offers at OTHER settlements — rumor material (Phase E3)."""
        return [q for q in self.quests if q.state == "offered" and q.giver_location != location_id]

    # --- Lifecycle ----------------------------------------------------------------

    def accept(self, quest: Quest) -> None:
        if quest.state != "offered":
            return
        quest.state = "active"
        esper.dispatch_event("log_message", f"Quest accepted: [color=yellow]{quest.title}[/color]")

    def turn_in(self, quest: Quest) -> bool:
        """Complete a quest at its giver. Returns True on success."""
        if self.ctx is None or self.ctx.player_entity is None:
            return False
        location_id = self.ctx.world_graph.current_location_id if self.ctx.world_graph else None
        if quest.giver_location != location_id:
            return False

        if quest.quest_type == "deliver":
            if not self._remove_player_items(quest.target["item"], quest.target["count"]):
                return False
            # The delivered goods enter the local market: shortage resolved.
            if self.ctx.economy is not None:
                for _ in range(quest.target["count"]):
                    self.ctx.economy.record_sale(location_id, quest.target["item"])
        elif quest.state != "completed":
            return False

        purse = esper.try_component(self.ctx.player_entity, Purse)
        if purse is not None:
            purse.gold += quest.reward_gold
        if self.ctx.reputation is not None:
            self.ctx.reputation.adjust(location_id, 5, f"quest '{quest.id}'")
        # Resolving the cause stops what it would have escalated into (G2):
        # hunted wolves never reach the herds.
        if quest.cause_event_id and self.ctx.world_chronicle is not None:
            self.ctx.world_chronicle.cancel_escalations(quest.giver_location, quest.cause_event_id)
        quest.state = "turned_in"
        esper.dispatch_event(
            "log_message",
            f"Quest completed: [color=green]{quest.title}[/color] (+{quest.reward_gold} gold)",
            None,
            LogCategory.LOOT,
        )
        return True

    # --- Progress hooks ---------------------------------------------------------

    def on_entity_died(self, entity, attacker=None) -> None:
        """Kill-quest progress: player kills of the target template count."""
        if attacker is None or self.ctx is None:
            return
        if not esper.has_component(attacker, PlayerTag):
            return
        tid = esper.try_component(entity, TemplateId)
        if tid is None:
            return
        location_id = self.ctx.world_graph.current_location_id if self.ctx.world_graph else None
        for quest in self.quests:
            if quest.state != "active" or quest.quest_type != "kill":
                continue
            if quest.target.get("template") != tid.id or quest.giver_location != location_id:
                continue
            quest.progress += 1
            if quest.progress >= quest.target["count"]:
                quest.state = "completed"
                esper.dispatch_event("log_message", f"[color=green]{quest.title}[/color]: done! Report back.")
            else:
                esper.dispatch_event(
                    "log_message",
                    f"{quest.title}: {quest.progress}/{quest.target['count']}",
                )

    def on_arrival(self, location_id: str) -> None:
        """Map-arrival hook: visit completion, cause-spawning, new offers."""
        # Visit quests auto-complete (reward immediately, giver irrelevant)
        for quest in self.quests:
            if quest.state == "active" and quest.quest_type == "visit" and quest.target.get("location") == location_id:
                quest.state = "turned_in"
                purse = esper.try_component(self.ctx.player_entity, Purse) if self.ctx else None
                if purse is not None:
                    purse.gold += quest.reward_gold
                esper.dispatch_event(
                    "log_message",
                    f"Quest completed: [color=green]{quest.title}[/color] (+{quest.reward_gold} gold)",
                    None,
                    LogCategory.LOOT,
                )

        # Generate offers for EVERY settlement (economy and chronicle are
        # global state) so rumors can point at requests before the player
        # has ever been there.
        if self.ctx is not None and self.ctx.world_graph is not None:
            for loc in self.ctx.world_graph.locations.values():
                if loc.type == "settlement":
                    self._generate_offers(loc.id)
        else:
            self._generate_offers(location_id)

    # --- Generated quests (E2) -----------------------------------------------------

    def _generate_offers(self, location_id: str) -> None:
        """Derive new requests from the simulation state of this settlement."""
        if self.ctx is None:
            return

        # Shortage -> deliver request (one open request per good per place)
        economy = self.ctx.economy
        if economy is not None:
            for item_id, level in economy.stocks.get(location_id, {}).items():
                rates = economy.rates_per_day.get(location_id, {})
                if rates.get(item_id, 0) >= 0 or level >= GEN_STOCK_THRESHOLD:
                    continue
                quest_id = f"gen_deliver_{location_id}_{item_id}"
                if any(q.id == quest_id and q.state != "turned_in" for q in self.quests):
                    continue
                template = item_registry.get(item_id)
                item_name = template.name if template else item_id
                value = template.value if template else 10
                self.quests = [q for q in self.quests if q.id != quest_id]  # drop old turned_in copy
                self.quests.append(
                    Quest(
                        id=quest_id,
                        title=f"Shortage of {item_name}s",
                        description=f"{location_id} has run out of {item_name}s. "
                        f"Bring {GEN_DELIVER_COUNT} and you will be paid well.",
                        quest_type="deliver",
                        giver_location=location_id,
                        target={"item": item_id, "count": GEN_DELIVER_COUNT},
                        reward_gold=int(value * GEN_DELIVER_COUNT * GEN_DELIVER_REWARD_FACTOR),
                        source="generated",
                    )
                )
                logger.info("Generated deliver quest at %s for %s.", location_id, item_id)

        # Recent wolf sighting -> kill request
        chronicle = self.ctx.world_chronicle
        clock = self.ctx.world_clock
        if chronicle is not None and clock is not None:
            recent = [
                e
                for e in chronicle.events_for(location_id, since_tick=clock.total_ticks - GEN_EVENT_MAX_AGE_TICKS)
                if e.event_id == GEN_WOLF_EVENT_ID
            ]
            quest_id = f"gen_wolves_{location_id}"
            if recent and not any(q.id == quest_id and q.state != "turned_in" for q in self.quests):
                self.quests = [q for q in self.quests if q.id != quest_id]
                self.quests.append(
                    Quest(
                        id=quest_id,
                        title=f"Wolves near {location_id}",
                        description=f"Wolves have been spotted around {location_id}. "
                        f"Hunt down {GEN_KILL_COUNT} of them in the wilds.",
                        quest_type="kill",
                        giver_location=location_id,
                        target={"template": "wolf", "count": GEN_KILL_COUNT},
                        reward_gold=GEN_KILL_REWARD,
                        source="generated",
                        cause_event_id=GEN_WOLF_EVENT_ID,
                    )
                )
                logger.info("Generated wolf-hunt quest at %s.", location_id)

    def on_map_entered(self, map_id: str) -> None:
        """Any-map-transition hook: kill-quest targets live in the giver
        settlement's wilderness — entering it spawns whatever is missing."""
        from game.services.map_generator import wilderness_map_id

        for quest in self.quests:
            if (
                quest.state == "active"
                and quest.quest_type == "kill"
                and wilderness_map_id(quest.giver_location) == map_id
            ):
                self._ensure_kill_targets(quest)

    def _ensure_kill_targets(self, quest) -> None:
        """The cause must exist: spawn missing kill targets on this map."""
        if self.ctx is None:
            return
        from game.content.entity_factory import EntityFactory
        from game.map.map_generator_utils import get_nearest_walkable_tile

        template = quest.target.get("template")
        needed = quest.target["count"] - quest.progress
        alive = sum(
            1
            for _ent, (tid,) in esper.get_components(TemplateId)
            if tid.id == template and esper.has_component(_ent, Position)
        )
        missing = needed - alive
        if missing <= 0:
            return
        container = self.ctx.map_service.get_active_map()
        layer = container.layers[0]
        for _ in range(missing):
            x = self.rng.randint(2, container.width - 3)
            y = self.rng.randint(2, container.height - 3)
            nx, ny = get_nearest_walkable_tile(layer, x, y)
            EntityFactory.create(esper, template, nx, ny)
        logger.info("Spawned %d %s(s) for quest '%s'.", missing, template, quest.id)

    # --- Player inventory helpers ---------------------------------------------------

    def _player_items_of(self, template_id: str) -> list[int]:
        inventory = esper.try_component(self.ctx.player_entity, Inventory) if self.ctx else None
        if inventory is None:
            return []
        equipment = esper.try_component(self.ctx.player_entity, Equipment) if self.ctx else None
        equipped_ids: set[int] = set(equipment.slots.values()) if equipment else set()
        result = []
        for item_ent in inventory.items:
            if item_ent in equipped_ids:
                continue
            tid = esper.try_component(item_ent, TemplateId)
            if tid is not None and tid.id == template_id:
                result.append(item_ent)
        return result

    def _count_player_items(self, template_id: str) -> int:
        return len(self._player_items_of(template_id))

    def _remove_player_items(self, template_id: str, count: int) -> bool:
        items = self._player_items_of(template_id)
        if len(items) < count:
            return False
        inventory = esper.component_for_entity(self.ctx.player_entity, Inventory)
        for item_ent in items[:count]:
            inventory.items.remove(item_ent)
            esper.delete_entity(item_ent)
        return True

    # --- Persistence ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"quests": [asdict(q) for q in self.quests]}

    def from_dict(self, data: dict) -> None:
        self.quests = [Quest(**entry) for entry in data.get("quests", [])]
