# Context for Phase 3: Core Gameplay Mechanics

This document defines the implementation decisions for Phase 3, integrating the shift to an Entity Component System (ECS) and the expansion of gameplay systems.

## Architecture: ECS Refactoring
- **Core Decision:** The existing object-oriented services (Party, Turn, Map) will be refactored into an **Entity Component System (ECS)** pattern to handle complex interactions between heroes, enemies, and effects.
- **Entities:** Heroes, Enemies, Items, Traps, and Special Effects.
- **Components:** `Position`, `Renderable`, `Stats` (HP, Mana, Perception, Intelligence), `Inventory`, `TurnOrder`, `LightSource`.
- **Systems:** `MovementSystem`, `TurnSystem`, `RenderSystem`, `VisibilitySystem` (FoW), `ActionSystem`.

## Fog of War & Memory System
- **Visibility States:**
    1. **Visible:** Currently within sight range and Line of Sight (LoS).
    2. **Hidden (Shroud):** Previously explored, currently out of sight. Rendered with the original tile sprite but tinted grey.
    3. **Forgotten:** Explored in the past, but the party has "forgotten" the details. Represented by a unique "Forgotten" sprite (e.g., vage outlines). Triggers upon leaving the Map Container.
    4. **Unexplored:** Completely unknown. Rendered with a solid black/unexplored sprite.
- **Logic:**
    - **Sigh Range:** Based on the maximum `Perception` attribute of active (living) party members.
    - **Line of Sight:** Walls and obstacles block visibility.
    - **Memory Logic:** When leaving a container, tiles are "forgotten" based on a calculation of elapsed rounds and the maximum `Intelligence` of the party.

## UI & Turn Indicator
- **Turn Header:** A fixed UI header displaying the global round counter and current turn status ("Player Turn" vs. "Environment Turn").
- **Action List:** A permanently visible sidebar listing available actions (Move, Investigate, Ranged, Spells, Items). 
    - Actions that are unavailable (e.g., no mana for spells, no arrows for ranged) are greyed out and skipped during navigation.
- **Feedback:** No audio feedback for turn changes; visual text-based updates only.

## Action System & Targeting
- **Action Flow:** `Select Action from List` -> `Select Target (if required)` -> `Confirm`.
- **Modes:**
    - **Normal/Aggressive:** Bump-to-attack or move.
    - **Investigation:** Move cursor to a specific tile (LoS applies). High-level skills might check a radius (e.g., 3x3).
    - **Ranged/Spells:** 
        - Uses **Auto-Targeting** for entities: The cursor cycles through valid targets (enemies/allies) within range and LoS.
        - Uses **Manual Target** for area effects: Cursor moves freely within max range.
- **Visuals:** 
    - **Targeting Cursor:** A distinct sprite/frame.
    - **Range/Area:** Tiles within range are tinted. AoE radii and beam paths are highlighted.
- **Resources:** Actions consume resources (Mana, Arrows, Items). Costs and current totals are displayed in the spell/item overlays.

## Interaction & Controls
- **ESC Key:** Standard key to cancel current mode (e.g., exit spell selection or targeting) and return to the main action list.
- **Turn Consumption:** Any successful action (Moving, Casting, Using Item, Investigating) counts as the player's turn and advances the game state.
