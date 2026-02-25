import esper
from ecs.components import AIBehaviorState, AIState, Alignment, Stats, AttackIntent, Name, TemplateId
from enum import Enum, auto
from services.dialogue_service import DialogueService

class InteractionType(Enum):
    NONE = auto()
    ATTACK = auto()
    WAKE_UP = auto()
    TALK = auto()

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
                name = world.component_for_entity(target_ent, Name).name if world.has_component(target_ent, Name) else "Someone"
                world.dispatch_event("log_message", f"You wake up {name}.")

        elif interaction == InteractionType.TALK:
            name = world.component_for_entity(target_ent, Name).name if world.has_component(target_ent, Name) else "Someone"
            # Look up template-specific dialogue
            tid = world.try_component(target_ent, TemplateId)
            line = DialogueService.get_line(tid.id if tid else "")
            world.dispatch_event("log_message", f"[color=yellow]{name}:[/color] {line}")

