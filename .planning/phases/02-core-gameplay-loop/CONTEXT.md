# Context for Phase 2: Core Gameplay Loop

This document captures the key decisions made for the implementation of the core gameplay loop.

## Tile & Map Appearance

- **Map Containers:** The game world is organized into "map containers", which represent areas like dungeons or towns. A container can hold multiple layers (levels).
- **Map Layers:** Each container can have one or more layers, which are the individual tilemaps (e.g., floors of a building).
- **Transitions:** Players can transition between layers within a container (e.g., using stairs) and between different containers (e.g., entering a house). These transitions can have visual effects.
- **Map Generation:** Maps within a container will have determinate dimensions but can be generated in different sizes.
- **Visual Style:** The game will use a tilemap-based visual style (e.g., pixel art).
- **Fog of War:** The map will be covered by a "fog of war" that is revealed as the player explores.
- **"See-Through" Feature:** It should be possible to see the layer below the player's current position through holes or other visual effects.
- **Special Effects:** The game should support special effects animations on tiles, such as animated water, poison fog, cold areas, and explosions.

## Turn-Based Flow

- **Turn Order:** The player always acts first. After the player's turn, all enemies act based on an initiative order.
- **Initiative:** Initiative will be calculated based on a character attribute and other modifiers.
- **Player Actions:** A player's turn can consist of one of the following actions:
    - Moving (which also triggers enemy turns).
    - Casting a defensive spell (e.g., healing, buffs).
    - Using a potion from inventory.
    - Using the "investigation mode" to examine a tile.
    - Using the "range-attack mode" for ranged attacks or spells.
- **Waiting:** The player can choose to wait, which ends their turn without any other action.
- **Buffs/Debuffs:** Buffs and debuffs will have a duration measured in a number of turns.
- **Turn Indicator:** A text-based indicator will be displayed to inform the player that it is their turn to act.

## Player Party & Movement

- **UI Layout:** The screen will be divided into sections, including a map view and a party list UI.
- **Party Representation:** The player's party is represented as a single sprite on a single tile on the map.
- **Party Control:** The party is always selected by default and moves as a single unit. Movement animation will be a simple slide.
- **Individual Hero Status:** The party list UI will display the status of each hero. The player can select a hero from this list to use their specific actions.
- **Hero Death:** When a hero dies, they are marked as "dead" in the party list and can no longer be selected for actions.
- **Roster Management:** The player's party roster is not fixed. The player can hire new heroes and leave others behind.

## Sprite Layering

- **Layer System:** A tile can contain multiple sprites, but each must be on a different layer.
- **Layer Order:** There is a fixed rendering order for the layers:
    - Layer 0: Ground (e.g., floor, walls)
    - Layer 1: Decor (Bottom) (e.g., rugs)
    - Layer 2: Traps
    - Layer 3: Items
    - Layer 4: Corpses
    - Layer 5: Entities (Player and Enemies)
    - Layer 6: Decor (Top) (e.g., chandeliers)
    - Layer 7: Effects (e.g., explosions)
- **Flexibility:** The system should be flexible enough to allow for new layers to be added later.
- **Corpse Sprites:** Dead enemies are represented by a corpse sprite that does not despawn.
- **UI Element:** The UI will include an element that displays the stack of sprites on the tile the player is currently standing on.
