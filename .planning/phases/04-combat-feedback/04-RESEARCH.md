# Phase 4: Combat & Feedback - Research

**Researched:** 2024-05-21
**Domain:** Event System, UI/Message Log, ECS Combat, AI
**Confidence:** HIGH

## Summary

Phase 4 focuses on closing the combat loop: Player attacks Monster -> Feedback in Log -> Monster Dies/Waits.

**Primary recommendation:** Use `esper`'s built-in event system for the Message Log to decouple logic from UI. Implement Combat via an `AttackIntent` component processed by a `CombatSystem`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `esper` | Latest | ECS & Event Bus | Already in use; has built-in lightweight event dispatching. |
| `pygame`| Latest | Rendering | Already in use; standard for 2D blitting. |

## Architecture Patterns

### Event Bus System
**Pattern:** Publisher-Subscriber using `esper.dispatch`.
**Why:** Decouples the "Game World" (Combat, AI) from the "Presentation" (Message Log). Systems don't need to know about the Log; they just shout "I hit something!".

**Implementation:**
```python
# events.py
EVENT_LOG_MESSAGE = "log_message"
EVENT_ENTITY_ATTACKED = "entity_attacked"
EVENT_ENTITY_DIED = "entity_died"

# usage in system
import esper
esper.dispatch(EVENT_LOG_MESSAGE, text="Welcome to the dungeon!", color=(255, 255, 255))
```

### ECS Combat Pattern
**Pattern:** `AttackIntent` Component.
**Why:** Keeps systems pure. `ActionSystem` doesn't resolve damage; it just signals *intent*. `CombatSystem` handles resolution (hit/miss, damage, death).

**Flow:**
1. Player bumps enemy.
2. `ActionSystem` adds `AttackIntent(target=enemy_id, damage=5)` to Player.
3. `CombatSystem` runs:
   - Reads `AttackIntent`.
   - Applies damage to target's `Stats`.
   - Dispatches `EVENT_LOG_MESSAGE`.
   - Checks for death.
   - Removes `AttackIntent`.

### Corpse Handling
**Pattern:** Entity Transformation (Swap Components).
**Why:** Preserves the Entity ID (useful if other systems reference it) and avoids allocation overhead.

**Method:**
1. Remove active components: `AI`, `Blocker`/`Collider`, `TurnOrder`.
2. Add `Corpse` component (tag).
3. Update `Renderable`:
   - Change sprite to "%" or corpse image.
   - **Critical:** Change `layer` to `LAYER_CORPSE` (ensure it draws *under* actors).
   - Change color to grey/dark red.

### Monster AI (Basic)
**Pattern:** State Machine in `AISystem`.
**Why:** Simple "Wait" state for Phase 4.
**Logic:**
- `TurnSystem` sets state to `ENEMY_TURN`.
- `AISystem` iterates entities with `AI` component.
- For Phase 4: Just print "Entity waits" or do nothing.
- Call `TurnSystem.end_enemy_turn()`.

## Rich Text Rendering (Pygame)

**Problem:** Pygame's `font.render` only supports one color per surface.
**Solution:** Parse "rich text" string into segments, render each, and blit sequentially.

**Format:** `You hit [color=red]Orc[/color]!`

**Parser Example:**
```python
import re

def parse_rich_text(text):
    # Split by tags, keeping the tags in the list
    tokens = re.split(r'(\[color=[^\]]+\]|\[/color\])', text)
    segments = []
    current_color = (255, 255, 255) # Default White
    
    for token in tokens:
        if token.startswith('[color='):
            color_name = token[7:-1]
            current_color = COLOR_MAP.get(color_name, (255, 255, 255))
        elif token == '[/color]':
            current_color = (255, 255, 255)
        elif token: # Text content
            segments.append((token, current_color))
            
    return segments
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event System | Custom Singleton | `esper.dispatch` | It's already there and thread-safe enough for this. |
| UI Library | Complex UI Framework | Custom simple render | Pygame-GUI is too heavy for just a log; simple blitting is faster to implement. |

## Common Pitfalls

### Pitfall 1: Event Handler Garbage Collection
**What goes wrong:** `esper` uses weak references for handlers. If you register a method `self.on_event` of a class instance that isn't stored elsewhere, the handler might silently disappear.
**How to avoid:** Ensure the object holding the handler (e.g., `MessageLogUI`) is kept alive (e.g., referenced in `main.py` or `World`).

### Pitfall 2: Corpse Blocking
**What goes wrong:** Player kills monster, monster turns to corpse, but player still can't walk there.
**Why:** Forgot to remove `Blocker` or `Collision` component.
**Verification:** Test "Kill and Walk Over".

### Pitfall 3: Z-Index Issues
**What goes wrong:** Corpses drawn *on top* of items or other monsters.
**How to avoid:** Explicit render layers.
- Layer 0: Floor
- Layer 1: Corpses
- Layer 2: Items
- Layer 3: Actors (Player/Monsters)
- Layer 4: Effects/Projectiles

## Code Examples

### Simple Combat System
```python
class CombatSystem(esper.Processor):
    def process(self):
        for ent, (intent, attacker_name) in self.world.get_components(AttackIntent, Name):
            target = intent.target
            if self.world.has_component(target, Stats):
                stats = self.world.component_for_entity(target, Stats)
                target_name = self.world.component_for_entity(target, Name).name
                
                # Apply Damage
                damage = intent.damage
                stats.hp -= damage
                
                # Log
                esper.dispatch("log_message", 
                             text=f"{attacker_name.name} hits [color=red]{target_name}[/color] for {damage} damage!")
                
                # Death Check
                if stats.hp <= 0:
                    esper.dispatch("entity_died", entity=target)
            
            # Remove intent so it doesn't trigger again
            self.world.remove_component(ent, AttackIntent)
```

## Open Questions

1.  **Damage Calculation:** Phase 4 implies fixed damage or basic stats?
    - *Assumption:* Use `Power - Defense` or simple fixed damage for now.
2.  **Turn Order:** Does killing an enemy remove them from the turn queue immediately?
    - *Recommendation:* Yes, `DeathSystem` should remove `TurnOrder` component.

## Sources

### Primary (HIGH confidence)
- [Esper Documentation](https://github.com/benmoran56/esper) - Event dispatching mechanics.
- Pygame Docs - Font rendering limitations.

### Secondary (MEDIUM confidence)
- Standard Roguelike Dev patterns (RoguelikeDev subreddit/tutorials) for Corpse handling.

## Metadata

**Confidence breakdown:**
- Event Bus: HIGH (Built-in)
- Combat Pattern: HIGH (Standard ECS)
- Text Parsing: HIGH (Simple regex)

**Research date:** 2024-05-21
**Valid until:** Phase 5
