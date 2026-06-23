"""Capacity-based housing for settlement NPCs (Living Village).

At village build time every scheduled townsperson is given a Residence that
decides where it belongs after dark:

- The settlement's beds are counted (one dwelling = one or more beds). Common
  folk are seated into those beds; whoever is left over has no home and spends
  the night at the hearth (campfire) or the tavern instead — exactly the
  "not enough houses, so they gather round the fire" behaviour asked for.
- Everyone is also told where the village's social centre is (`hearth_pos`),
  so SOCIALIZE schedule entries converge on the real campfire of *this*
  village rather than a hard-coded coordinate that only fits one map.
- Guards keep no bed: they take the night watch by the fire/gate.
- Notables (merchants, the innkeeper, the quest-giving mayor) keep the home
  their template authored.

Runs against the live exterior entities of a single scenario, before the map
is frozen. The assignment is stored on a Residence component, so it survives
freeze/thaw and saves like any other component.
"""

import logging

from game.components import (
    Activity,
    Innkeeper,
    Merchant,
    Needs,
    Position,
    QuestGiver,
    Residence,
    Schedule,
    TemplateId,
)
from game.map.map_generator_utils import get_nearest_walkable_tile

logger = logging.getLogger(__name__)


class HousingService:
    """Assigns Residence components to a settlement's scheduled NPCs."""

    @staticmethod
    def assign(world, config: dict, exterior_layer) -> None:
        """Give every live scheduled NPC a Residence based on bed capacity.

        Args:
            world: The ECS world (the scenario's exterior NPCs are live).
            config: The parsed scenario JSON (structures + lights).
            exterior_layer: The settlement's ground MapLayer, for snapping
                home/gather spots onto walkable tiles.
        """
        hearth_pos = HousingService._hearth(config, exterior_layer)
        gather_spots = HousingService._gather_spots(config, exterior_layer) or ([hearth_pos] if hearth_pos else [])
        bed_spots = HousingService._bed_spots(config, exterior_layer)

        # Deterministic order so a given world seed always houses the same folk.
        residents = sorted(
            (ent for ent, _ in world.get_components(Schedule, Activity, Position)),
            key=lambda e: e,
        )

        gather_cycle = 0
        next_bed = 0
        for ent in residents:
            is_notable = (
                world.has_component(ent, Merchant)
                or world.has_component(ent, QuestGiver)
                or world.has_component(ent, Innkeeper)
            )
            has_needs = world.has_component(ent, Needs)
            bed_eligible = has_needs and not is_notable

            if bed_eligible and next_bed < len(bed_spots):
                # A common townsperson with a bed waiting for them.
                spot = bed_spots[next_bed]
                next_bed += 1
                activity = world.component_for_entity(ent, Activity)
                activity.home_pos = spot
                world.add_component(ent, Residence(hearth_pos=hearth_pos, housed=True))
            elif is_notable:
                # Merchants/innkeeper/mayor keep the home their template set.
                world.add_component(ent, Residence(hearth_pos=hearth_pos, housed=True))
            else:
                # No bed: surplus folk and guards on watch gather at the fire.
                gather_pos = gather_spots[gather_cycle % len(gather_spots)] if gather_spots else hearth_pos
                gather_cycle += 1
                world.add_component(ent, Residence(hearth_pos=hearth_pos, housed=False, gather_pos=gather_pos))

        HousingService._assign_work_and_patrol(world, config, exterior_layer, residents)

        logger.info(
            "Housing: %d residents, %d beds, %d gather spots (hearth=%s).",
            len(residents),
            len(bed_spots),
            len(gather_spots),
            hearth_pos,
        )

    @staticmethod
    def _assign_work_and_patrol(world, config: dict, layer, residents) -> None:
        """Bind ambient daytime targets to the settlement's own geography.

        Common folk (villager/vendor/blacksmith routines, which target
        ``"work"``) are fanned across the scenario's ``work_anchors`` so the
        daytime crowd gathers at this town's real market/fields/shops instead
        of a fixed corner. Guards get this town's ``patrol_route`` so the watch
        covers the actual map. Both are optional — without them the legacy
        per-schedule targets still apply."""
        anchors = [get_nearest_walkable_tile(layer, x, y) for x, y in config.get("work_anchors", [])]
        patrol = [list(get_nearest_walkable_tile(layer, x, y)) for x, y in config.get("patrol_route", [])]

        work_i = 0
        for ent in residents:
            tid = world.try_component(ent, TemplateId)
            residence = world.try_component(ent, Residence)
            if residence is None:
                continue
            if tid is not None and tid.id == "guard":
                if patrol:
                    residence.patrol_route = patrol
                continue
            # Notables work at their authored shop/home, not a generic anchor.
            is_notable = (
                world.has_component(ent, Merchant)
                or world.has_component(ent, QuestGiver)
                or world.has_component(ent, Innkeeper)
            )
            if anchors and not is_notable:
                residence.work_pos = anchors[work_i % len(anchors)]
                work_i += 1

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _hearth(config: dict, layer) -> tuple[int, int] | None:
        """The social centre: the first campfire, else the tavern door."""
        for light in config.get("lights", []):
            if light["type"] == "campfire":
                return get_nearest_walkable_tile(layer, light["pos"][0], light["pos"][1])
        for door in HousingService._tavern_doors(config, layer):
            return door
        return None

    @staticmethod
    def _gather_spots(config: dict, layer) -> list[tuple[int, int]]:
        """Where bedless folk spend the night: campfires and tavern doors."""
        spots: list[tuple[int, int]] = []
        for light in config.get("lights", []):
            if light["type"] == "campfire":
                spots.append(get_nearest_walkable_tile(layer, light["pos"][0], light["pos"][1]))
        spots.extend(HousingService._tavern_doors(config, layer))
        return spots

    @staticmethod
    def _tavern_doors(config: dict, layer) -> list[tuple[int, int]]:
        doors = []
        for s in config.get("structures", []):
            if s.get("style") == "tavern":
                vx, vy = s["v_pos"]
                vw, vh = s["v_size"]
                doors.append(get_nearest_walkable_tile(layer, vx + vw // 2, vy + vh + 1))
        return doors

    @staticmethod
    def _bed_spots(config: dict, layer) -> list[tuple[int, int]]:
        """Distinct walkable tiles around each home, one per bed it provides.

        Beds default to the dwelling's floor count (the furnish routine puts
        roughly one bed per floor in a home); a scenario may override with a
        `"beds"` field. The spots ring the house so housed NPCs settle next to
        their own home instead of stacking on a single tile."""
        used: set[tuple[int, int]] = set()
        spots: list[tuple[int, int]] = []
        for s in config.get("structures", []):
            if s.get("style") != "home":
                continue
            beds = int(s.get("beds", s.get("floors", 1)))
            spots.extend(HousingService._perimeter_spots(s, layer, beds, used))
        return spots

    @staticmethod
    def _perimeter_spots(structure: dict, layer, count: int, used: set) -> list[tuple[int, int]]:
        vx, vy = structure["v_pos"]
        vw, vh = structure["v_size"]
        # Front (south) tiles first — that is where the door is — then the
        # remaining sides, so beds fill out from the entrance.
        candidates = [(x, vy + vh) for x in range(vx, vx + vw)]
        candidates += [(x, vy - 1) for x in range(vx, vx + vw)]
        candidates += [(vx - 1, y) for y in range(vy, vy + vh)]
        candidates += [(vx + vw, y) for y in range(vy, vy + vh)]

        result: list[tuple[int, int]] = []
        for cx, cy in candidates:
            if len(result) >= count:
                break
            sx, sy = get_nearest_walkable_tile(layer, cx, cy, excluded_positions=used)
            if (sx, sy) in used:
                continue
            used.add((sx, sy))
            result.append((sx, sy))
        return result
