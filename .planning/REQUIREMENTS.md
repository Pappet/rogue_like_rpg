# Requirements for Rogue Like RPG

This document outlines the requirements for version 1 of the Rogue Like RPG.

## Core Requirements

- `GAME-001`: The game must launch successfully and display a title screen.
- `GAME-002`: The player must be able to start a new game from the title screen.

## Placeholder for Additional Requirements
[Add requirements here with unique IDs, e.g., `FEAT-001: Description of feature.`]
- `FEAT-002`: The game will be using PyGame.
- `FEAT-003`: The game will be tile-based.
- `FEAT-004`: The game will be turn-based.
- `FEAT-005`: The player will control a group of up to 3 heroes, who move as a single unit.
- `FEAT-006`: The graphics will be sprite-based with different layers.
- `FEAT-007`: The tile size will be configurable.

## Combat & Feedback Requirements
- `UI-001`: The game must display a message log in the bottom screen area.
- `UI-002`: The message log must support colored text parsing.
- `ARCH-001`: An event system must broadcast game events to subscribers (like the log).
- `ENT-001`: The game must support Monster entities (e.g., Ork) with stats (HP, Power, Defense).
- `MECH-001`: The player must be able to attack monsters by moving into them (Bump Combat).
- `MECH-002`: Combat must calculate damage and apply it to the target's HP.
- `MECH-003`: Entities must die when HP reaches 0, changing visual to a corpse and becoming non-blocking.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GAME-001 | Phase 1 | Completed |
| GAME-002 | Phase 1 | Completed |
| FEAT-003 | Phase 2 | Completed |
| FEAT-004 | Phase 2 | Completed |
| FEAT-005 | Phase 2 | Completed |
| FEAT-006 | Phase 2 | Completed |
| FEAT-007 | Phase 2 | Completed |
| UI-001 | Phase 4 | Completed |
| UI-002 | Phase 4 | Completed |
| ARCH-001 | Phase 4 | Completed |
| ENT-001 | Phase 4 | Completed |
| MECH-001 | Phase 4 | Completed |
| MECH-002 | Phase 4 | Completed |
| MECH-003 | Phase 4 | Completed |
