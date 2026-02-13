from services.map_service import MapService
from map.map_container import MapContainer

def test_map_service():
    service = MapService()
    
    # Create and register two maps
    map1 = service.create_sample_map(10, 10, map_id="level_1")
    map2 = service.create_sample_map(10, 10, map_id="level_2")
    
    assert len(service.maps) == 2
    assert service.get_map("level_1") == map1
    assert service.get_map("level_2") == map2
    
    # Test active map
    assert service.get_active_map() is None
    
    service.set_active_map("level_1")
    assert service.active_map_id == "level_1"
    assert service.get_active_map() == map1
    
    service.set_active_map("level_2")
    assert service.get_active_map() == map2
    
    # Test error case
    try:
        service.set_active_map("non_existent")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
        
    print("Verification PASSED")

if __name__ == "__main__":
    test_map_service()
