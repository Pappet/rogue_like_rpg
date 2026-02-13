import esper
from map.map_container import MapContainer
from ecs.components import Position, Name

def test_persistence():
    # Reset esper world
    esper.clear_database()
    
    # Create an entity to be frozen
    ent1 = esper.create_entity(Position(1, 2), Name("Frozen One"))
    
    # Create an entity to be excluded (e.g. Player)
    player = esper.create_entity(Position(0, 0), Name("Player"))
    
    # Create MapContainer (with empty layers for this test)
    container = MapContainer(layers=[])
    
    # Freeze
    print(f"Entities before freeze: {list(esper._entities.keys())}")
    container.freeze(esper, exclude_entities=[player])
    print(f"Entities after freeze: {list(esper._entities.keys())}")
    
    assert esper.entity_exists(player)
    assert not esper.entity_exists(ent1)
    assert len(container.frozen_entities) == 1
    
    # Thaw
    container.thaw(esper)
    print(f"Entities after thaw: {list(esper._entities.keys())}")
    
    assert len(esper._entities) == 2
    
    # Verify components of thawed entity
    found = False
    for ent, (pos, name) in esper.get_components(Position, Name):
        if name.name == "Frozen One":
            assert pos.x == 1
            assert pos.y == 2
            found = True
    assert found
    
    assert len(container.frozen_entities) == 0
    print("Verification PASSED")

if __name__ == "__main__":
    test_persistence()
