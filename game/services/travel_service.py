"""Overworld travel: leaving one settlement for another.

The rules of a journey — whether a road event interrupts it, how far the
player actually gets, and what the chronicle is told — live here rather than
in WorldMapState, which only picks the destination. Travel itself is executed
through the regular ``map_change_requested`` event, so freeze/thaw, the clock
advance and map-aware system re-pointing all reuse MapTransitionService.
"""

import esper

from config import TICKS_PER_HOUR


def _go(target_map_id: str, x: int, y: int, travel_ticks: int) -> None:
    esper.dispatch_event(
        "map_change_requested",
        {
            "target_map_id": target_map_id,
            "target_x": x,
            "target_y": y,
            "target_layer": 0,
            "travel_ticks": travel_ticks,
        },
    )


def travel_to(ctx, destination, travel_ticks: int) -> bool:
    """Set out for ``destination``; returns False if there is nowhere to go.

    A road event may cut the journey short: the player then lands on a
    one-shot road map whose far portal carries the remaining travel time.
    """
    target_map = ctx.map_service.get_map(destination.id)
    if target_map is None:
        return False

    hours = travel_ticks / TICKS_PER_HOUR
    encounters = ctx.travel_encounters
    origin_id = ctx.world_graph.current_location_id
    encounter = encounters.roll_encounter(origin_id, destination.id, travel_ticks) if encounters else None

    if encounter is not None:
        road_map = ctx.map_service.get_map(encounter["map_id"])
        ax, ay = road_map.arrival_pos
        _go(encounter["map_id"], ax, ay, encounter["elapsed_ticks"])
        esper.dispatch_event(
            "log_message",
            f"You set out for [color=yellow]{destination.name}[/color] ({hours:.0f}h on the road).",
        )
        esper.dispatch_event("log_message", f"[color=orange]{encounter['message']}[/color]")
    else:
        ax, ay = target_map.arrival_pos or (1, 1)
        _go(destination.id, ax, ay, travel_ticks)
        esper.dispatch_event(
            "log_message",
            f"You travel to [color=yellow]{destination.name}[/color] ({hours:.0f}h on the road).",
        )
    return True
