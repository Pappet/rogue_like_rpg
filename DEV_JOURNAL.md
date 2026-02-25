# Rogue Like RPG — Development Journal

> *This document preserves the rich history and architectural evolution of the project from its inception through v1.6. It replaces the legacy `.planning/` directory, serving as a permanent record of our design decisions, milestones, and technical journey.*

---

## 1. Project Inception & Core Vision
The core value of this project has always been to provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat. From the start, we committed to a focused, single-threaded Pygame loop built purely in Python, avoiding heavy external engines to maintain complete control over the application state.

## 2. Technology Stack & Architecture
Our technology choices and architectural patterns were deliberate and have proven highly effective:
- **Core Engine:** Python 3.13.11 with **Pygame 1.x+** for rendering, input, and loop management.
- **Entity Component System (ECS):** We leveraged the **Esper** library to transition away from deeply nested inheritance trees. All entities (Player, NPCs, Items) are simply IDs with attached `@dataclass` components (`Position`, `Stats`, `Renderable`, `ActionList`).
- **State Machine Pattern:** High-level game flow is managed by state classes (`TitleScreen`, `Game`, `WorldMapState`), while in-game flow is directed by `TurnSystem` (`PLAYER_TURN`, `ENEMY_TURN`, `TARGETING`).
- **Data-Driven Assets:** We built a robust **JSON pipeline pattern** (data file → ResourceLoader → Registry → Factory). For instance, `TileType` acts as a dataclass flyweight—preventing memory bloat without risking shared state corruption.

## 3. The Milestone Journey (v1.0 – v1.6)

Between early February and February 21, 2026, the game rapidly evolved through 36 distinct planning phases spanning 7 major version milestones.

### v1.0 MVP (Phases 1-11) — *Shipped Feb 14, 2026*
We laid down the foundation: the game loop, basic ECS setup, Map rendering, simple movement, and collision detection. The barebones player character could navigate a static grid, validating our Pygame + Esper approach.

### v1.1 Investigation System (Phases 12-14) — *Shipped Feb 14, 2026*
Introduced a "Look" mode. We implemented a dedicated cyan cursor distinguishing investigation from combat. Critically, we made investigation a "free action" that does not end the player's turn, using the player's Perception stat to define the scan range.

### v1.2 AI Infrastructure (Phases 15-18) — *Shipped Feb 15, 2026*
NPCs gained brains. We established the `AISystem` and separated the AI tag from its behavior state (`AIBehaviorState`). 
- **Key Decision:** AI targets coordinates rather than entity IDs. This prevented stale reference bugs during map transitions (freeze/thaw cycles). 
- **Optimization:** We added a transient `claimed_tiles` set to prevent multiple NPCs from targeting the exact same hex/tile simultaneously.

### v1.3 Debug Overlay System (Phases 19-22) — *Shipped Feb 15, 2026*
A developer toolkit was embedded directly into the game. We created an overlay to visualize line-of-sight (LOS), entity data, pathfinding routes, and ECS load.

### v1.4 Item & Inventory System (Phases 23-26) — *Shipped Feb 16, 2026*
Items transitioned from simple map features into full ECS entities.
- **Effective Stats Pattern:** Equipment cleanly modifies base fields (`base_hp`, `base_power`) dynamically.
- Entities drop into inventory seamlessly. `ConsumableService` ensures validation, preventing players from wasting healing potions at full HP.

### v1.5 World Clock & NPC Schedules (Phases 27-32) — *Shipped Feb 20, 2026*
The world came alive. We added day/night visual cycles tinting the environment. We introduced a schedule data pipeline yielding time-based NPC behaviors (e.g., villagers going to sleep at night).
- **Architecture Win:** Reused the player's FOV service for NPC sight, ensuring logical consistency without duplicating calculations.

### v1.6 UI/UX Architecture & Input Overhaul (Phases 33-36) — *Shipped Feb 21, 2026*
We tore down the monolithic `ui_system.py` and rebuilt the interface to be modular and stateful.
- **Controls Menu & Floating Combat Text:** Damage now floats neatly above units.
- **Context-Sensitive Bumping:** Moving into an enemy triggers an attack, while bumping a friendly triggers dialogue.
- **Stateful Modals:** `InventoryScreen` and `CharacterScreen` pause the game state, layering over the viewport cleanly.

## 4. Architectural Victories & Patterns to Preserve

1. **Map Freeze/Thaw System:** 
   When entering a portal, all non-player entities on the old map are frozen and safely tucked away. The new map instances are thawed. This completely circumvented cross-map rendering leaks.
2. **Action Validation vs Execution:**
   The `ActionSystem` properly validates mana costs, cooldowns, and targeting *before* committing the turn, dramatically reducing edge-case bugs.
3. **Visibility Memory:** 
   Tiles shift from `VISIBLE` to `SHROUDED` to `FORGOTTEN` based on a timer (`rounds_since_seen > player.intelligence * 5`). This created a highly immersive "fog of war" memory decay.

## 5. End of an Era (The `.planning/` Cleanup)
The exhaustive documentation approach inside `.planning/` served us incredibly well through the foundational stages of the engine. It allowed us to predict integration pain points and rigorously build the ECS flow. However, as the architecture solidified and the system modularity proved itself, the rigid documentation structure became overhead. 

We now rely on self-documenting code, `CLAUDE.md`, and agile iterations. This journal stands as a testament to the rigorous design that got our foundation right the first time.

---
*Generated: 2026-02-25 / Marking the transition to Agile Development.*
