
import esper
from services.map_service import MapService
from ecs.components import Position, Portal, Name
from config import SpriteLayer

def test_village_refactor():
    import esper
    world = esper
    esper.clear_database()
    service = MapService()
    
    # Create scenario
    service.create_village_scenario(world)
    
    # Check Village exists
    village = service.get_map("Village")
    assert village is not None
    assert village.width == 40
    assert village.height == 40
    
    # Check ground layer has expected floor tile sprites (variety uses floor_stone → sprite '.')
    ground_sprites = {
        tile.sprites[SpriteLayer.GROUND]
        for row in village.layers[0].tiles
        for tile in row
        if SpriteLayer.GROUND in tile.sprites
    }
    assert '.' in ground_sprites or '#' in ground_sprites, "Village ground layer has no tiles"
    
    # Check houses exist
    for h_id in ["Cottage", "Tavern", "Shop"]:
        h = service.get_map(h_id)
        assert h is not None, f"Map {h_id} missing"
    
    # Check portals in Village
    # Since Village is active and thawed, entities should be in world
    portals = world.get_components(Position, Portal, Name)
    village_portals = []
    for ent, (pos, portal, name) in portals:
        village_portals.append(name.name)
    
    assert "Portal to Cottage" in village_portals
    assert "Portal to Tavern" in village_portals
    assert "Portal to Shop" in village_portals
    
    # Check interior of Cottage (needs to be thawed first)
    # 1. Freeze Village
    service.get_active_map().freeze(world)
    
    # 2. Set active House and Thaw
    service.set_active_map("Cottage")
    service.get_active_map().thaw(world)
    
    cottage_portals = []
    portals = world.get_components(Position, Portal, Name)
    for ent, (pos, portal, name) in portals:
        cottage_portals.append(name.name)
        
    assert "Portal to Village" in cottage_portals
    assert "Stairs Up" in cottage_portals # Cottage has 2 floors
    
    print("Village refactor verification PASSED")

if __name__ == "__main__":
    test_village_refactor()
