from enum import Enum, auto

from game.components import (
    Activity,
    AIBehaviorState,
    AIState,
    Alignment,
    AttackIntent,
    Merchant,
    Name,
    Stats,
    TemplateId,
)
from game.content.dialogue_service import dialogue_service


class InteractionType(Enum):
    NONE = auto()
    ATTACK = auto()
    WAKE_UP = auto()
    TALK = auto()
    TRADE = auto()


class InteractionResolver:
    @staticmethod
    def resolve(world, source_ent: int, target_ent: int) -> InteractionType:
        """Determines the interaction type when source_ent bumps into target_ent."""
        if world.has_component(target_ent, AIBehaviorState):
            behavior = world.component_for_entity(target_ent, AIBehaviorState)

            # Sleeping NPCs are woken up regardless of alignment
            if behavior.state == AIState.SLEEP:
                return InteractionType.WAKE_UP

            # Hostile entities are attacked
            if behavior.alignment == Alignment.HOSTILE:
                return InteractionType.ATTACK

            # Non-hostile merchants open their shop
            if world.has_component(target_ent, Merchant):
                return InteractionType.TRADE

            # Neutral/Friendly entities are talked to
            if behavior.alignment in [Alignment.NEUTRAL, Alignment.FRIENDLY]:
                return InteractionType.TALK

        # Generic entities with Stats (destructibles?) are attacked
        if world.has_component(target_ent, Stats):
            return InteractionType.ATTACK

        return InteractionType.NONE

    @staticmethod
    def execute(world, interaction: InteractionType, source_ent: int, target_ent: int, action_system=None):
        """Applies the logic for the given interaction type."""
        if interaction == InteractionType.ATTACK:
            world.add_component(source_ent, AttackIntent(target_entity=target_ent))

        elif interaction == InteractionType.WAKE_UP:
            if action_system:
                action_system.wake_up(target_ent)
            else:
                # Fallback implementation if action_system is not provided (useful for tests)
                behavior = world.component_for_entity(target_ent, AIBehaviorState)
                behavior.state = AIState.IDLE
                name = (
                    world.component_for_entity(target_ent, Name).name
                    if world.has_component(target_ent, Name)
                    else "Someone"
                )
                world.dispatch_event("log_message", f"You wake up {name}.")

        elif interaction == InteractionType.TALK:
            InteractionResolver._say_line(world, target_ent)

        elif interaction == InteractionType.TRADE:
            InteractionResolver._say_line(world, target_ent)
            # Sanctioned request: the movement layer must not know about UI —
            # the gameplay state opens the trade window.
            world.dispatch_event("trade_requested", target_ent)

    @staticmethod
    def _say_line(world, target_ent: int) -> None:
        name = world.component_for_entity(target_ent, Name).name if world.has_component(target_ent, Name) else "Someone"
        # Look up template-specific dialogue, with selection context:
        # the NPC's current activity plus whatever the game layer provides
        # (reputation tier, day phase) via the context_provider.
        context = {}
        if dialogue_service.context_provider is not None:
            context.update(dialogue_service.context_provider())
        activity = world.try_component(target_ent, Activity)
        if activity is not None:
            context["activity"] = activity.current_activity
        tid = world.try_component(target_ent, TemplateId)
        line = dialogue_service.get_line(tid.id if tid else "", context)
        world.dispatch_event("log_message", f"[color=yellow]{name}:[/color] {line}")
