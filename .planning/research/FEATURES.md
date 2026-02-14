# Feature Research

**Domain:** Roguelike RPG — Investigation / Look / Examine System
**Researched:** 2026-02-14
**Confidence:** HIGH (based on established roguelike conventions and direct codebase analysis)

---

## Context

This research covers features for adding an investigation action: the classic roguelike "look" or "examine" command. The player activates a free-move cursor, points it at tiles and entities, and receives descriptive text. This is a read-only operation that does not consume a turn.

The project already has:
- A `Targeting` component with `origin_x/y`, `target_x/y`, `range`, `mode`, `action` fields
- A `TARGETING` game state in `GameStates` enum
- `ActionSystem` methods: `start_targeting`, `move_cursor`, `cycle_targets`, `confirm_action`, `cancel_targeting`
- `Description` component with HP-threshold dynamic text (`base`, `wounded_text`, `wounded_threshold`)
- `RenderSystem.draw_targeting_ui` that renders a yellow range highlight and cursor box
- FOV with `VISIBLE`, `SHROUDED`, `UNEXPLORED` tile states
- Message log with color-tag markup support (`[color=green]...[/color]`)
- `Name` component on entities

The investigation system must reuse this infrastructure without conflating combat targeting with information gathering.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features every roguelike player assumes exist. Missing these makes the "look" command feel broken or uselessly incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Activate look mode with dedicated key (`x` or `l`) | Every roguelike since Rogue. Muscle memory for genre players. | LOW | Add `K_x` / `K_l` handler in `handle_player_input`. Does NOT end player turn. |
| Free-move cursor via arrow keys | Players must be able to point at any visible tile, not just entities. | LOW | Reuses `move_cursor` logic but without range restriction — the investigation cursor roams the entire visible area. |
| Cursor renders distinctly from combat cursor | Players must know they are in look mode, not attack mode. | LOW | Use a different color (e.g. cyan) vs yellow combat cursor. One constant in `config.py`. |
| Cancel with Escape and return to player turn | Standard for any modal state in roguelikes. | LOW | Dispatch to existing `cancel_targeting` or a parallel `cancel_investigation`. |
| Status bar / header updates to show "Look Mode" | Without mode feedback, players are confused whether look is active. | LOW | The header already shows "Targeting..." — add "Look Mode" branch for the new state. |
| Tile name displayed when cursor moves | Players expect "You see: stone floor" or equivalent on any tile they hover over. | LOW | Read tile's registry key or a `name` field; write to message log or a dedicated status line. |
| Entity name displayed when cursor is on an entity | Core of the look command — "You see: a Goblin" | LOW | Query `Name` component for entities at cursor tile. |
| Entity description displayed | Without description text, name alone is useless. The `Description` component exists and already supports HP-based dynamic text. | LOW | Call `description.get(stats)` if entity has `Stats`; fall back to `description.base` otherwise. |
| Only reveal info for VISIBLE entities | Showing shrouded entity names breaks FOV gameplay contract. | LOW | Check `VisibilityState.VISIBLE` before reporting entity info. Tile names for SHROUDED tiles are acceptable (you remember the floor type). |
| Look mode does NOT consume a turn | Examining the world is free in virtually all roguelikes. Consuming a turn would punish curiosity and confuse players. | LOW | Do not call `turn_system.end_player_turn()` when entering or exiting look mode. |

### Differentiators (Competitive Advantage)

Features that improve the look system meaningfully beyond genre minimum.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Dynamic status text that updates in-place as cursor moves | Instead of spamming the message log with every tile, show current tile info in a dedicated status area (e.g. bottom bar or header sub-line). Spamming the log with look info clutters combat history. | MEDIUM | Requires a "current look description" string tracked in UI state, rendered each frame in `UISystem`. Separate from the persistent message log. |
| HP-aware entity description via existing `Description` component | "A goblin — wounded, bleeding" vs "A goblin — looks healthy." This is already modeled. Surfacing it in look mode gives Description real utility. | LOW | Already implemented. Just wire `description.get(stats)` into the look output. Zero new logic. |
| Tile description lookup from tile registry | Show "Mossy stone wall" not just "wall". Tile registry already exists — adding a `description` or `name` field to tile JSON is a small data change. | LOW | Add `description` field to tile JSON templates. Read in `TileRegistry`. Output in look mode. |
| Multiple entities at same tile listed | Corpses under enemies, items on the floor. Players need to know what's stacked. | MEDIUM | Query all entities at `(cursor_x, cursor_y)` not just first match. Format as list in status area. |
| Cursor snaps to nearest visible entity on activation | Speed of use: when you press `x`, cursor jumps to the closest visible enemy rather than staying on the player. Same UX as the combat auto-targeting already present. | LOW | Reuse `find_potential_targets` or a simpler distance sort. Optional — cursor-on-player-tile is acceptable too. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Show entity stats (HP numbers, power, defense) during look | Players want to make tactical decisions. | Destroys information asymmetry. If you can read exact enemy HP you never need the `Description` threshold system. Undermines `Stats`-based game balance. | Use the `Description` component thresholds. "Looks healthy", "Looks wounded", "Near death" gives tactical info without removing fog-of-war on numbers. |
| Show tile coordinates in look output | Useful for debugging, requested for "orientation." | Clutters output, makes the UI feel like a dev tool, adds nothing to gameplay feel. | Show tile name and type only. Coordinates live in debug mode if needed. |
| Mouse-based look on hover | Modern-feeling, lower friction than keyboard cursor. | In a turn-based keyboard-driven game, hover events fire constantly and spam the status area with every mouse movement. Requires separate hover-state management that conflicts with keyboard look mode. | If mouse support is ever added, gate it on click, not hover. Keep keyboard look mode canonical for this milestone. |
| Scrollable examination history | Some roguelikes log every entity you've looked at. | Adds UI complexity for low benefit. Look output is ephemeral by nature. | The message log already persists important information. Look results are transient status-bar content. |
| Look at SHROUDED entities | Players sometimes want to check entities they remember seeing. | Breaks FOV contract. Memory of a position is different from current knowledge. | Show tile name for shrouded tiles (you remember the floor type). Never show entity info for shrouded/forgotten positions. |

---

## Feature Dependencies

```
[Look Mode State (LOOKING)]
    └──requires──> [New GameStates.LOOKING enum value]
                       └──requires──> [game_states.py handler branch]

[Cursor movement in look mode]
    └──reuses──> [ActionSystem.move_cursor logic]
                     └──but──> [No range restriction — roam full visible area]

[Entity description display]
    └──requires──> [Name component on entity] (already exists)
    └──requires──> [Description component on entity] (already exists)
    └──enhances via──> [Description.get(stats)] (already works)

[Tile name display]
    └──requires──> [Tile name/description field in tile registry JSON]
    └──requires──> [TileRegistry exposes that field]

[Dynamic status line (in-place update)]
    └──requires──> [UISystem tracks a "look_text" string]
    └──conflicts──> [Using message log for per-cursor-move output]
                        (log spam vs. clean status line — choose one)

[Cursor snap to nearest entity on activation]
    └──reuses──> [ActionSystem.find_potential_targets]
    └──optional──> enhances speed-of-use but not required for table stakes
```

### Dependency Notes

- **Look Mode requires a new GameStates.LOOKING value:** The existing `TARGETING` state is coupled to action execution (`confirm_action` costs mana, ends turn). Reusing `TARGETING` for look mode would require branching every action-system method on whether there is a real action. A clean `LOOKING` state avoids that coupling entirely.
- **Tile name display requires tile registry data change:** Currently tiles have no user-facing name field. This is a small JSON schema addition but it is a prerequisite — without it, look at tile can only show "walkable" or "blocked."
- **Dynamic status line conflicts with message log for look output:** Choose one. Log spam is the most common beginner mistake in roguelike look implementations. A dedicated status line (updated in-place in `UISystem.process`) is the correct pattern. The existing log is for events, not for live cursor state.
- **Description.get(stats) already works:** The `Description` component is wired; look mode just needs to call it. No new component logic required.

---

## MVP Definition

### Launch With (v1 — this milestone)

Minimum viable look command. Covers all table stakes.

- [ ] `GameStates.LOOKING` — new enum value, separate from `TARGETING`
- [ ] Key `x` (or `l`) activates look mode, does not end turn
- [ ] Arrow keys move cursor freely across visible tiles
- [ ] Escape cancels look mode, returns to `PLAYER_TURN`
- [ ] Cursor renders in cyan (distinct from yellow combat cursor)
- [ ] Header shows "Look Mode" when `LOOKING` state is active
- [ ] Status line (not message log) shows tile name at cursor position
- [ ] Status line shows entity name + description at cursor position (VISIBLE entities only)
- [ ] `Description.get(stats)` called for entities with both `Description` and `Stats` components
- [ ] Tile registry JSON gains a `name` field; look mode reads and displays it

### Add After Validation (v1.x)

Once core look is working and feel is validated:

- [ ] Multiple entities at same tile — list all of them in status area
- [ ] Cursor snap to nearest visible entity on activation — quality-of-life improvement
- [ ] Tile `description` field (longer flavor text) separate from `name` field

### Future Consideration (v2+)

Defer until scope justifies the complexity:

- [ ] Mouse click to examine — only if mouse input is added to the game broadly
- [ ] Look at shrouded tile for tile name only (visible entity filtering still applies)
- [ ] Examine items on the floor once an inventory/item system is built

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| LOOKING game state | HIGH | LOW | P1 |
| Activate/cancel look mode | HIGH | LOW | P1 |
| Cursor movement (full visible area) | HIGH | LOW | P1 |
| Distinct cursor color | MEDIUM | LOW | P1 |
| Header "Look Mode" text | MEDIUM | LOW | P1 |
| Status line (in-place, not log) | HIGH | MEDIUM | P1 |
| Entity name + description display | HIGH | LOW | P1 |
| Tile name from registry | HIGH | LOW | P1 |
| HP-aware description via Description.get() | HIGH | LOW (already built) | P1 |
| Multiple entities at same tile | MEDIUM | MEDIUM | P2 |
| Cursor snap on activation | MEDIUM | LOW | P2 |
| Tile flavor description (long text) | LOW | LOW | P3 |
| Mouse click examine | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for this milestone — defines the feature
- P2: Should have, add after P1 is stable
- P3: Nice to have, future milestone

---

## Competitor Feature Analysis

Classic roguelikes this domain draws from:

| Feature | NetHack (`:`) | DCSS (`x`) | Brogue (`?`) | Our Approach |
|---------|--------------|------------|--------------|--------------|
| Free cursor movement | YES — full map | YES — full visible | YES — full visible | Full visible area only (respects FOV contract) |
| Tile name on cursor | YES | YES | YES | YES — from tile registry |
| Entity name on cursor | YES | YES | YES | YES — from Name component |
| Entity description | YES — verbose | YES — dynamic flavor | YES | YES — via Description.get(stats) |
| HP-aware flavor text | PARTIAL (status) | YES (explicit HP bar) | YES (via color) | YES — Description threshold system |
| Turn cost | NONE | NONE | NONE | NONE |
| Mode indicator | YES (prompt line) | YES (header) | YES (overlay) | YES — header text |
| Status line vs log | Status line | Status line | Overlay panel | Status line (avoid log spam) |
| Stat numbers shown | YES (in inventory) | YES (tab panel) | NO | NO — use Description thresholds |

---

## Sources

- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — `Targeting`, `Description`, `Name`, `Stats` components
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/ecs/systems/action_system.py` — `start_targeting`, `move_cursor`, `find_potential_targets`
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/ecs/systems/render_system.py` — `draw_targeting_ui`, cursor rendering
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/ecs/systems/ui_system.py` — header, sidebar, message log layout
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/config.py` — `GameStates` enum, screen constants
- Codebase analysis: `/home/peter/Projekte/rogue_like_rpg/game_states.py` — `handle_targeting_input`, game state dispatch pattern
- Roguelike convention: NetHack `:` look command, DCSS `x` examine cursor, Brogue examine overlay — canonical genre references (HIGH confidence, established 30+ year conventions)
- Roguelike convention: "Look mode is free / does not cost a turn" — universal in the genre, no known exception among major titles

---

*Feature research for: Roguelike RPG — Investigation / Look / Examine System*
*Researched: 2026-02-14*
