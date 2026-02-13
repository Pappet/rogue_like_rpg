from ecs.components import Position, Renderable, Stats, Name, Blocker, AI
from config import SpriteLayer

def create_orc(world, x, y):
    orc = world.create_entity()
    world.add_component(orc, Position(x, y))
    world.add_component(orc, Renderable(sprite="O", color=(0, 255, 0), layer=SpriteLayer.ENTITIES.value))
    world.add_component(orc, Stats(
        hp=10, 
        max_hp=10, 
        power=3, 
        defense=0, 
        mana=0, 
        max_mana=0, 
        perception=5, 
        intelligence=5
    ))
    world.add_component(orc, Name("Orc"))
    world.add_component(orc, Blocker())
    world.add_component(orc, AI())
    return orc
