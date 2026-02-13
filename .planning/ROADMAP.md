# Project Roadmap: Rogue Like RPG

## Summary

**Phases:** 4
**Depth:** Standard
**Coverage:** 14/14 requirements mapped ✓

| Phase | Goal | Requirements |
|-------|------|--------------|
| 1 - Game Foundation | Users can launch the game and begin a new play session. | GAME-001, GAME-002 |
| 2 - Core Gameplay Loop | Extend the basic framework with tile-based, turn-based mechanics and player party movement. | FEAT-003, FEAT-004, FEAT-005, FEAT-006, FEAT-007 |
| 3 - Core Gameplay Mechanics | Implement key interactive gameplay systems like Fog of War and expanded player actions. | (Implicit in Phase 3 plans) |
| 4 - Combat & Feedback | Players can fight monsters and receive textual feedback on actions. | UI-001, UI-002, ARCH-001, ENT-001, MECH-001, MECH-002, MECH-003 |

## Success Criteria

### Phase 1: Game Foundation
1.  The game application launches without errors.
2.  A title screen is displayed upon launching the game.
3.  A "New Game" option is visible and selectable on the title screen.
4.  Selecting "New Game" transitions the user into a playable game state.

### Phase 2: Core Gameplay Loop
1. The game world is represented by a grid of tiles.
2. The game progresses in turns.
3. The player controls a party of up to 3 heroes that move as a single unit on the tile-based map.
4. The game uses sprite-based graphics with multiple layers.
5. The tile size is configurable.

### Phase 3: Core Gameplay Mechanics
1. The map is obscured by a Fog of War that is revealed through exploration.
2. A clear visual indicator shows when it is the player's turn to act.
3. The player can perform multiple types of actions on their turn (e.g., move, cast spell, use item).

### Phase 4: Combat & Feedback
1. A message log is visible at the bottom of the screen.
2. Actions (like movement or attacks) generate colored log messages.
3. Player can reduce a monster's HP by bumping into it.
4. Monsters turn into corpses upon death.
5. Player can walk over corpses.

## Plans

### Phase 1: Game Foundation
- [x] 01-01-PLAN.md — Set up the basic structure of the game, including a functional title screen and the ability to start a new game.

### Phase 2: Core Gameplay Loop
- [x] 02-01-PLAN.md — Create the foundational data structures for the tile-based map system.
- [x] 02-02-PLAN.md — Implement the rendering of the tile-based world.
- [x] 02-03-PLAN.md — Introduce the concept of a player-controlled party.
- [x] 02-04-PLAN.md — Introduce a fundamental turn-based system.

### Phase 3: Core Gameplay Mechanics
- [x] 03-01-PLAN.md — Refactor the core structure to use the `esper` ECS library.
- [x] 03-02-PLAN.md — Implement 4-state Fog of War and Recursive Shadowcasting LoS.
- [x] 03-03-PLAN.md — Build persistent UI Header and Sidebar for game state and actions.
- [x] 03-04-PLAN.md — Implement the Action System with targeting and resource consumption.
- [x] 03-05-PLAN.md — Implement map memory (Forgotten state) and transition logic.

### Phase 4: Combat & Feedback
- [ ] 04-01-PLAN.md — Implement Message Log UI and Event System.
- [ ] 04-02-PLAN.md — Implement Monster Entity and Spawning logic.
- [ ] 04-03-PLAN.md — Implement Bump Combat and Damage calculation.
- [ ] 04-04-PLAN.md — Implement Death System and Corpse handling.