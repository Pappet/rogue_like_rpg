from ecs.components import Position, Portal

def test_components():
    pos = Position(x=10, y=20, layer=1)
    print(f"Position: {pos}")
    assert pos.x == 10
    assert pos.y == 20
    assert pos.layer == 1

    portal = Portal(target_map_id="dungeon_2", target_x=5, target_y=5, target_layer=0, name="Stairs Down")
    print(f"Portal: {portal}")
    assert portal.target_map_id == "dungeon_2"
    assert portal.target_x == 5
    assert portal.target_y == 5
    assert portal.target_layer == 0
    assert portal.name == "Stairs Down"

    # Test default values
    pos_default = Position(x=0, y=0)
    assert pos_default.layer == 0
    
    portal_default = Portal(target_map_id="test", target_x=1, target_y=1)
    assert portal_default.target_layer == 0
    assert portal_default.name == "Portal"

    print("Verification PASSED")

if __name__ == "__main__":
    test_components()
