# Requirements: Rogue Like RPG

**Defined:** 2026-02-14
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat

## v1.1 Requirements

Requirements for the Investigation System milestone. Each maps to roadmap phases.

### Investigation Action

- [ ] **INV-01**: Player can select the "Investigate" action from the action list to enter targeting mode
- [ ] **INV-02**: Investigation targeting range is derived from the player's perception stat
- [ ] **INV-03**: Investigation does not consume a turn (free action)
- [ ] **INV-04**: Player can cancel investigation with Escape and return to normal play

### Tile Inspection

- [ ] **TILE-01**: Player can see the tile name and description when confirming investigation on a tile
- [ ] **TILE-02**: SHROUDED tiles show remembered tile name but no entity information
- [ ] **TILE-03**: UNEXPLORED tiles cannot be investigated

### Entity Inspection

- [ ] **ENT-01**: Player can see entity names and descriptions at the investigated position
- [ ] **ENT-02**: Entity descriptions reflect dynamic HP state (e.g., "looks wounded" when below threshold)
- [ ] **ENT-03**: Multiple entities at the same tile are all listed in the output
- [ ] **ENT-04**: Entities without Stats (portals, corpses) show base description without crash

### UI & Feedback

- [ ] **UI-01**: Investigation results are displayed as formatted colored text in the message log
- [ ] **UI-02**: Header displays "Investigating..." when in investigation targeting mode
- [ ] **UI-03**: Investigation cursor uses a distinct color from the combat targeting cursor

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Investigation Enhancements

- **INV-05**: Cursor snaps to nearest visible entity on investigation activation
- **INV-06**: Mouse click to investigate a tile (requires mouse input system)
- **INV-07**: Investigation detail level scales with player intelligence stat

## Out of Scope

| Feature | Reason |
|---------|--------|
| Dedicated description sidebar panel | Adds UI complexity beyond MVP; message log output sufficient for v1.1 |
| Scrollable examination history | Message log already persists results; separate history adds low value |
| Showing exact stat numbers (HP, power) | Breaks information asymmetry; Description threshold system preferred |
| Look at SHROUDED entity positions | Breaks FOV gameplay contract; only tile names for shrouded tiles |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INV-01 | Phase 12 | Pending |
| INV-02 | Phase 13 | Pending |
| INV-03 | Phase 12 | Pending |
| INV-04 | Phase 12 | Pending |
| TILE-01 | Phase 14 | Pending |
| TILE-02 | Phase 14 | Pending |
| TILE-03 | Phase 13 | Pending |
| ENT-01 | Phase 14 | Pending |
| ENT-02 | Phase 14 | Pending |
| ENT-03 | Phase 14 | Pending |
| ENT-04 | Phase 14 | Pending |
| UI-01 | Phase 14 | Pending |
| UI-02 | Phase 12 | Pending |
| UI-03 | Phase 12 | Pending |

**Coverage:**
- v1.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-02-14*
*Last updated: 2026-02-14 after roadmap creation*
