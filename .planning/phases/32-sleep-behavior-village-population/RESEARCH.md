# Research: Sleep Behavior & Village Population

## Objective
Implement sleep mechanics for NPCs and populate a village scenario with NPCs following daily routines.

## Sleep Mechanics

### 1. State: `AIState.SLEEP`
- NPCs in `SLEEP` state should:
    - Skip their AI turn (no movement).
    - Disable player detection (blind and deaf).
- Implementation: Modify `AISystem._dispatch` and `AISystem.process` to handle `AIState.SLEEP`.

### 2. Visual Feedback
- Sleeping NPCs should be visually distinct.
- Options:
    - Dim the sprite (multiply color by 0.5).
    - Add a "z" overlay sprite.
- Implementation: Modify `RenderSystem` to check for `AIState.SLEEP`.

### 3. Wake-up Triggers
- **Bumping:** If the player tries to move into a sleeping NPC's tile.
- **Combat:** If the NPC is attacked or if combat happens in an adjacent tile.
- Implementation:
    - `ActionSystem`: Detect bumps and change `AIState.SLEEP` to `AIState.IDLE` or `AIState.CHASE`.
    - `CombatSystem`: Wake NPC on attack.
    - Event `entity_attacked`: Could be used to wake nearby NPCs too?

### 4. Home Positions
- NPCs should go to a "home" coordinate before sleeping.
- Implementation: Add `home_pos` to `Activity` or `Schedule` component. `ScheduleSystem` should prioritize `home_pos` when the activity is `SLEEP`.

## Village Population

### 1. New Entity Types
- Villagers, Guards, Shopkeepers.
- Data-driven via `assets/data/entities.json`.

### 2. Village Scenario
- A map representing a village with houses, shops, and patrol routes.
- NPCs assigned schedules that make them move between work, social, and home.

## Implementation Tasks (Planned)

### Plan 32-01: Sleep Mechanics & Visuals
- Update `AIState` and `AISystem` to handle sleep.
- Add dimming/overlay logic to `RenderService` or `RenderSystem`.
- Implement wake-up triggers for bumping and direct attacks.

### Plan 32-02: Home Positions & Schedule Refinement
- Update `Activity` component to include `home_pos`.
- Update `ScheduleSystem` to route NPCs to `home_pos` when SLEEP starts.
- Ensure NPCs stay at `home_pos` while sleeping.

### Plan 32-03: Village Population & Routines
- Define Villager, Guard, and Shopkeeper in `entities.json`.
- Create a `village_scenario.json` (or similar) or update `ResourceLoader` to populate a village map.
- Define full daily routines in `schedules.json`.

### Plan 32-04: Verification
- Comprehensive tests for sleep, waking, and village routines.
