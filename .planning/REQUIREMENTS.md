# Requirements: v1.3 Debug Overlay System

## Debug Infrastructure

| REQ-ID | Requirement | Phase | Status |
|--------|-------------|-------|--------|
| DBG-01 | Global debug toggle via F-key hotkey | 19 | Pending |
| DBG-02 | Toggle state survives state transitions (persist dict) | 19 | Pending |
| DBG-03 | DebugRenderSystem as dedicated ECS system (explicit-call, not esper-registered) | 19 | Pending |
| DBG-04 | Pre-allocated SRCALPHA overlay surface (no per-tile allocation) | 19 | Pending |
| DBG-05 | Zero performance impact when debug disabled (early return) | 19 | Pending |

## Core Overlays

| REQ-ID | Requirement | Phase | Status |
|--------|-------------|-------|--------|
| OVL-01 | Player FOV tile highlight (green tint on VISIBLE tiles) | 20 | Pending |
| OVL-02 | NPC AI state label (W/C/I/T text above entities) | 20 | Pending |
| OVL-03 | Last-known position marker (orange rect at ChaseData coordinates) | 20 | Pending |
| OVL-04 | Overlays render within viewport clip region only | 20 | Pending |

## Extended Overlays

| REQ-ID | Requirement | Phase | Status |
|--------|-------------|-------|--------|
| EXT-01 | Chase vector arrows (NPC to last-known position) | 21 | Pending |
| EXT-02 | Turns-without-sight counter on state label | 21 | Pending |
| EXT-03 | NPC FOV cone visualization (per-NPC shadowcast tint) | 21 | Pending |
| EXT-04 | Per-overlay toggle (extend single bool to dict) | 21 | Pending |

## Traceability

| REQ-ID | Phase | Plan | Verified |
|--------|-------|------|----------|
| DBG-01 | 19 | — | — |
| DBG-02 | 19 | — | — |
| DBG-03 | 19 | — | — |
| DBG-04 | 19 | — | — |
| DBG-05 | 19 | — | — |
| OVL-01 | 20 | — | — |
| OVL-02 | 20 | — | — |
| OVL-03 | 20 | — | — |
| OVL-04 | 20 | — | — |
| EXT-01 | 21 | — | — |
| EXT-02 | 21 | — | — |
| EXT-03 | 21 | — | — |
| EXT-04 | 21 | — | — |

---
*Created: 2026-02-15 for v1.3 Debug Overlay System*
