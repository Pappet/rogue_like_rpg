import sys
import os

# Add the project root to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import esper
from ecs.components import AIBehaviorState, AIState, Alignment, Stats, Name
from services.interaction_resolver import InteractionResolver, InteractionType

def test_interaction_resolver():
    # In esper 3.x, we clear the global database
    esper.clear_database()
    world = esper
    
    # 1. Hostile
    hostile = world.create_entity(AIBehaviorState(AIState.IDLE, Alignment.HOSTILE), Stats(10,10,5,5,5,5,1,1), Name("Monster"))
    assert InteractionResolver.resolve(world, 0, hostile) == InteractionType.ATTACK
    
    # 2. Sleeping
    sleeper = world.create_entity(AIBehaviorState(AIState.SLEEP, Alignment.NEUTRAL), Stats(10,10,5,5,5,5,1,1), Name("Villager"))
    assert InteractionResolver.resolve(world, 0, sleeper) == InteractionType.WAKE_UP
    
    # 3. Friendly
    friendly = world.create_entity(AIBehaviorState(AIState.IDLE, Alignment.FRIENDLY), Stats(10,10,5,5,5,5,1,1), Name("Friend"))
    assert InteractionResolver.resolve(world, 0, friendly) == InteractionType.TALK
    
    # 4. Neutral
    neutral = world.create_entity(AIBehaviorState(AIState.IDLE, Alignment.NEUTRAL), Stats(10,10,5,5,5,5,1,1), Name("NPC"))
    assert InteractionResolver.resolve(world, 0, neutral) == InteractionType.TALK
    
    # 5. Destructible (Stats, no AI)
    destructible = world.create_entity(Stats(10,10,5,5,5,5,1,1), Name("Crate"))
    assert InteractionResolver.resolve(world, 0, destructible) == InteractionType.ATTACK

    print("All tests passed!")

if __name__ == "__main__":
    test_interaction_resolver()
