import pytest
import esper
from ecs.components import (
    Position, AIBehaviorState, Activity, AIState, 
    Alignment, Schedule, PathData, Stats, Name, AI
)
from ecs.systems.schedule_system import ScheduleSystem
from entities.schedule_registry import schedule_registry, ScheduleTemplate, ScheduleEntry
from services.world_clock_service import WorldClockService
from unittest.mock import MagicMock

class MockMap:
    def __init__(self, width=20, height=20):
        self.width = width
        self.height = height
        self.layers = [MockLayer(width, height)]
    
    def get_tile(self, x, y, layer):
        return MagicMock(walkable=True)
    
    def is_walkable(self, x, y, layer=0):
        return True

class MockLayer:
    def __init__(self, width, height):
        self.tiles = [[MagicMock(walkable=True) for _ in range(width)] for _ in range(height)]

@pytest.fixture
def world():
    esper.clear_database()
    return esper

def test_npc_moves_home_before_sleeping(world):
    # Setup
    schedule_system = ScheduleSystem()
    clock = WorldClockService()
    mock_map = MockMap()
    
    # Register a schedule
    home_pos = (10, 10)
    entries = [
        ScheduleEntry(start=0, end=6, activity="SLEEP", target_meta="home"),
        ScheduleEntry(start=6, end=22, activity="WORK", target_pos=(15, 15)),
        ScheduleEntry(start=22, end=24, activity="SLEEP", target_meta="home")
    ]
    template = ScheduleTemplate(id="test_home_schedule", name="Test Home", entries=entries)
    schedule_registry.register(template)
    
    # Create NPC at (5, 5) with home at (10, 10)
    npc = esper.create_entity(
        Position(5, 5),
        AIBehaviorState(state=AIState.IDLE, alignment=Alignment.NEUTRAL),
        Activity(current_activity="WORK", target_pos=(15, 15), home_pos=home_pos),
        Schedule(schedule_id="test_home_schedule"),
        AI(), # Required for AI system to process but we'll mock it or just check components
        Stats(hp=10, max_hp=10, power=1, defense=0, mana=0, max_mana=0, perception=5, intelligence=5),
        Name("Test NPC")
    )
    
    # Set time to 23:00 (Bedtime)
    clock.total_ticks = 23 * 60
    
    # Run ScheduleSystem. This should trigger the transition to SLEEP activity
    schedule_system.process(clock, mock_map)
    
    # Verify NPC is in SLEEP activity but NOT in SLEEP AIState because not at home
    activity = esper.component_for_entity(npc, Activity)
    ai_state = esper.component_for_entity(npc, AIBehaviorState)
    
    assert activity.current_activity == "SLEEP"
    assert activity.target_pos == home_pos
    assert ai_state.state == AIState.IDLE # Not SLEEP yet!
    
    # Verify PathData was added
    assert esper.has_component(npc, PathData)
    path_data = esper.component_for_entity(npc, PathData)
    assert path_data.destination == home_pos
    
    # Simulate movement (manually for this test or use AISystem)
    # Move NPC to home_pos
    pos = esper.component_for_entity(npc, Position)
    pos.x, pos.y = home_pos
    
    # Run ScheduleSystem again
    schedule_system.process(clock, mock_map)
    
    # Verify NPC is now in SLEEP AIState
    ai_state = esper.component_for_entity(npc, AIBehaviorState)
    assert ai_state.state == AIState.SLEEP

def test_npc_wakes_up_and_moves_to_work(world):
    # Setup
    schedule_system = ScheduleSystem()
    clock = WorldClockService()
    mock_map = MockMap()
    
    home_pos = (10, 10)
    work_pos = (15, 15)
    
    # Create NPC at home, sleeping
    npc = esper.create_entity(
        Position(10, 10),
        AIBehaviorState(state=AIState.SLEEP, alignment=Alignment.NEUTRAL),
        Activity(current_activity="SLEEP", target_pos=home_pos, home_pos=home_pos),
        Schedule(schedule_id="test_home_schedule"),
        Stats(hp=10, max_hp=10, power=1, defense=0, mana=0, max_mana=0, perception=5, intelligence=5),
        Name("Test NPC")
    )
    
    # Set time to 08:00 (Work time)
    clock.total_ticks = 8 * 60
    
    # Run ScheduleSystem
    schedule_system.process(clock, mock_map)
    
    # Verify NPC is in WORK state and heading to work
    activity = esper.component_for_entity(npc, Activity)
    ai_state = esper.component_for_entity(npc, AIBehaviorState)
    
    assert activity.current_activity == "WORK"
    assert activity.target_pos == work_pos
    assert ai_state.state == AIState.WORK
    
    assert esper.has_component(npc, PathData)
    path_data = esper.component_for_entity(npc, PathData)
    assert path_data.destination == work_pos
