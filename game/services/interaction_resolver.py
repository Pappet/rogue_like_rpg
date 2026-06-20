from enum import Enum, auto

from game.components import (
    Activity,
    AIBehaviorState,
    AIState,
    Alignment,
    Animal,
    AttackIntent,
    Innkeeper,
    Merchant,
    Name,
    QuestGiver,
    ResourceNode,
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
    QUESTS = auto()
    REST = auto()
    HARVEST = auto()


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

            # Animals don't talk — bumping wildlife is a hunting strike
            if world.has_component(target_ent, Animal):
                return InteractionType.ATTACK

            # Non-hostile innkeepers offer a room (rest)
            if world.has_component(target_ent, Innkeeper):
                return InteractionType.REST

            # Non-hostile merchants open their shop
            if world.has_component(target_ent, Merchant):
                return InteractionType.TRADE

            # Quest givers open their request board
            if world.has_component(target_ent, QuestGiver):
                return InteractionType.QUESTS

            # Neutral/Friendly entities are talked to
            if behavior.alignment in [Alignment.NEUTRAL, Alignment.FRIENDLY]:
                return InteractionType.TALK

        # Resource nodes (herb patch, ore vein, grain field) are harvested
        if world.has_component(target_ent, ResourceNode):
            return InteractionType.HARVEST

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

        elif interaction == InteractionType.QUESTS:
            InteractionResolver._say_line(world, target_ent)
            world.dispatch_event("quests_requested", target_ent)

        elif interaction == InteractionType.REST:
            InteractionResolver._say_line(world, target_ent)
            # Sanctioned request: the movement layer must not know about UI —
            # the gameplay state opens the rest window.
            world.dispatch_event("rest_requested", {"source": "innkeeper"})

        elif interaction == InteractionType.HARVEST:
            # Sanctioned request: the movement layer raises it, the gameplay
            # state (with ctx access) runs the harvest rules.
            world.dispatch_event("harvest_requested", target_ent)

    @staticmethod
    def _say_line(world, target_ent: int) -> None:
        name = world.component_for_entity(target_ent, Name).name if world.has_component(target_ent, Name) else "Someone"
        # Locals give directions out of the current town the first time you ask
        # — this is how new places enter the travel map. Takes priority.
        if dialogue_service.directions_provider is not None:
            directions = dialogue_service.directions_provider()
            if directions:
                world.dispatch_event("log_message", f"[color=yellow]{name}:[/color] {directions}")
                return
        # Otherwise NPCs sometimes share a rumor about the wider world instead
        # of their usual smalltalk (Phase E3).
        if dialogue_service.rumor_provider is not None:
            rumor = dialogue_service.rumor_provider()
            if rumor:
                world.dispatch_event("log_message", f"[color=yellow]{name}:[/color] {rumor}")
                return
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
