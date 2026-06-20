# Refactoring Plan — Roguelike RPG "Back on Track"

> **STATUS: HISTORISCH / ABGELÖST.** Dieser Plan wurde von
> `docs/ARCHITECTURE_CONCEPT.md` ("Aufräumen statt Neubau", Phasen R0–R6,
> umgesetzt) abgelöst. Er beschreibt den Stand *vor* dem Refactoring und
> referenziert Dateien, die es heute nicht mehr gibt (z. B. das aufgelöste
> `game_states.py` Gott-Objekt → heute `game/states/` + Controller). Bleibt
> als Beleg der Ausgangslage und der erledigten Schuldenliste erhalten.
>
> **Ziel (damals):** Codebase stabilisieren, technische Schulden abbauen, klare Architektur für zukünftige Features schaffen.
> **Methode:** Phase für Phase mit Claude Code durcharbeiten. Jede Phase hat klare Tasks, Akzeptanzkriterien und eine Validierung.

---

## Bestandsaufnahme: Was ist schief gelaufen?

### 🔴 Kritisch (Architektur-Probleme)

1. **`game_states.py` ist ein God-Object (~815 Zeilen)**
   - `Game` Klasse enthält: Input-Handling, Map-Transitions, Item-Pickup, UI-Management, Portal-Logik, Examine-Tooltips, Debug-Toggles, System-Initialisierung
   - `startup()` allein ist ~130 Zeilen — jedes System wird mit `if not persist.get("system"):` lazy-init oder re-konfiguriert
   - Jedes neue Feature wird hier reingequetscht

2. **`map_service.py` hat zu viele Verantwortlichkeiten**
   - Map-Registry, Map-Erstellung, Village-Szenario-Hardcoding, Prefab-Loading, Monster-Spawning, Terrain-Variety
   - Village-Layout ist komplett hardcoded mit Magic Numbers

3. **Inkonsistente System-Registrierung**
   - `TurnSystem`, `MovementSystem`, `CombatSystem` etc. → registriert als esper Processors
   - `AISystem`, `ScheduleSystem`, `RenderSystem`, `UISystem` → manuell aufgerufen
   - `DeathSystem` → registriert als Processor, aber `process()` ist ein No-Op (arbeitet nur über Events)
   - `RenderSystem` und `UISystem` werden bei jedem `startup()` neu erstellt (nicht in `persist`), andere Systems hingegen schon

4. **`freeze()`/`thaw()` greift auf esper-Internals zu**
   - `map_container.freeze()` nutzt `actual_world._entities` — bricht bei esper-Updates
   - Doppelte Indirektion: `world._world` check + `_entities` access (Zeile 77-80)

### 🟡 Mittel (Code-Qualität)

1. **Legacy-Code**: `entities/monster.py` existiert noch (manuelles `create_orc()`)
2. **`config.py` ist eine Sammelstelle** für alles: Farben, UI-Konstanten, Enums, Game-Settings
3. **Inkonsistentes Error-Handling**: Mix aus `try/except KeyError`, `esper.try_component()`, direkte Zugriffe
4. **Inline-Imports**: Innerhalb von Methoden in `combat_system.py` (Zeile 34) und `action_system.py` (Zeile 272)
5. **Hardcoded Werte**: Positionen in `map_service.py`, `party_service.py` Stats-Werte
6. **Debug via `print()`** statt strukturiertes Logging

### 🟢 Niedrig (Verbesserungen)

1. **Keine Input-Abstraktion für UI-Windows**: Jedes Window reimplementiert Event-Handling
2. **Render-Performance**: Visibility iteriert alle Tiles, Debug-Overlay neu-erstellt jeden Frame
3. **Stub-Features**: Talk-Interaction, Spells, Ranged → tun nichts Sinnvolles
4. **Kein Player-Death-Handling**

---

## Phase 0: Vorbereitung & Sicherheitsnetz

> **Ziel:** Bevor wir refactoren, brauchen wir ein Sicherheitsnetz.

### Task 0.1 — Smoke-Test Suite erstellen

```python
Erstelle tests/test_smoke.py:
- Test: Village-Szenario wird erstellt, alle Registries gefüllt
- Test: Player-Entity hat alle erwarteten Components
- Test: Ein Turn-Zyklus (PLAYER_TURN → ENEMY_TURN → PLAYER_TURN) läuft durch
- Test: Alle Player-Aktionen können problemlos ausgeführt werden
- Test: Map freeze/thaw roundtrip verliert keine Entities (zählt Entities vor/nach)
```

**Akzeptanz:** `python -m pytest tests/test_smoke.py -v` läuft grün.

**Hinweis:** Pygame-Abhängigkeit via `os.environ["SDL_VIDEODRIVER"] = "dummy"` vor dem Import mocken.

### Task 0.2 — Dependencies formalisieren

Erstelle requirements.txt:

```python
pygame>=2.5
esper>=3.0
pathfinding>=1.0
```

Optional: requirements-dev.txt mit pytest

### Task 0.3 — Git-Strategie

- Erstelle Branch: refactor/phase-X für jede Phase
- Jede Phase endet mit einem Merge in main
- Smoke-Tests müssen vor jedem Merge grün sein

---

## Phase 1: Config & Konstanten aufräumen

> **Ziel:** `config.py` entflechten, Magic Numbers eliminieren.

### Task 1.1 — Config in Module aufteilen

config.py aufteilen in:

```python
├── config/
│   ├── __init__.py          # Re-exportiert alles für Rückwärtskompatibilität
│   ├── game.py              # SCREEN_*, TILE_SIZE, TICKS_PER_HOUR, DN_SETTINGS
│   ├── ui.py                # UI_*, HEADER_HEIGHT, LOG_HEIGHT, SIDEBAR_WIDTH
│   ├── colors.py            # COLOR_*, UI_COLOR_*
│   ├── debug.py             # DEBUG_*
│   └── enums.py             # SpriteLayer, GameStates, LogCategory, LOG_COLORS
```

Wichtig: config/**init**.py importiert alles → bestehende `from config import X`
brechen NICHT. Migration der Imports kann später schrittweise passieren.

**Akzeptanz:** Alle bestehenden `from config import ...` funktionieren weiterhin. Smoke-Tests grün.

### Task 1.2 — Player-Stats externalisieren

Erstelle assets/data/player.json:

```json
{
  "name": "Player",
  "sprite": "@",
  "hp": 100, "max_hp": 100,
  "power": 5, "defense": 2,
  "mana": 50, "max_mana": 50,
  "perception": 10, "intelligence": 10,
  "max_carry_weight": 20.0,
  "actions": [...],
  "hotbar": {...}
}
```

party_service.py lädt aus dieser Datei statt Hardcoding.

**Akzeptanz:** Änderungen an `player.json` wirken sich im Spiel aus ohne Code-Änderung.

### Task 1.3 — Legacy-Code entfernen

- Lösche entities/monster.py (komplett ersetzt durch EntityFactory)
- Suche nach allen Referenzen und entferne sie

**Akzeptanz:** `grep -r "from entities.monster\|import monster" --include="*.py"` = 0 Treffer.

---

## Phase 2: game_states.py entflechten

> **Ziel:** Die God-Class `Game` in fokussierte Module aufbrechen.
>
> **Abhängigkeit:** Task 3.3 (MapAware Mixin) sollte VOR Task 2.3 abgeschlossen sein,
> da `SystemInitializer` das einheitliche `set_map()` Interface voraussetzen sollte.

### Task 2.1 — Input-Handler extrahieren

Erstelle services/game_input_handler.py:

```python
class GameInputHandler:
    def __init__(self, action_system, turn_system, ui_stack, player_entity):
        ...

    def handle_player_input(self, command) -> None:
        # Gesamte handle_player_input() Logik aus Game hierher

    def handle_targeting_input(self, command) -> None:
        ...

    def handle_examine_input(self, command) -> None:
        ...
```

Game.get_event() delegiert an GameInputHandler.

**Akzeptanz:** `Game.get_event()` ist < 20 Zeilen. Alle Input-Tests laufen.

### Task 2.2 — Map-Transition-Logik extrahieren

Erstelle services/map_transition_service.py:

```python
class MapTransitionService:
    def __init__(self, map_service, world_clock):
        ...

    def transition(self, event_data, player_entity, systems: dict) -> MapContainer:
        # Gesamte transition_map() Logik aus Game hierher
        # systems dict enthält alle Systems die set_map() brauchen
```

Game registriert: esper.set_handler("change_map", self.map_transition.transition)

**Akzeptanz:** `transition_map()` existiert nicht mehr in `game_states.py`.

### Task 2.3 — System-Initialisierung extrahieren

Erstelle services/system_initializer.py:

```python
class SystemInitializer:
    @staticmethod
    def initialize(persist: dict) -> dict:
        """Erstellt oder aktualisiert alle ECS-Systeme.
        Returns dict mit allen System-Referenzen."""
        ...

    @staticmethod
    def register_processors():
        """Registriert Processors bei esper in korrekter Reihenfolge.
        Entfernt erst alle bestehenden um Duplikate zu verhindern."""
        for processor_type in [TurnSystem, EquipmentSystem, ...]:
            try:
                esper.remove_processor(processor_type)
            except KeyError:
                pass
        esper.add_processor(...)
```

Ersetzt das fragile `if not persist.get("system"):` Pattern in startup().
Game.startup() ruft SystemInitializer.initialize(self.persist) auf.

**Akzeptanz:** `Game.startup()` ist < 30 Zeilen. Kein `if not persist.get(...)` Pattern mehr.

### Task 2.4 — Examine/Tooltip-Logik extrahieren

Verschiebe update_examine_tooltip() in ui/windows/tooltip.py
als TooltipManager Klasse oder als Teil des ExamineSystem.

Game.update() ruft nur noch tooltip_manager.update() auf.

**Akzeptanz:** `game_states.py` Game-Klasse ist < 200 Zeilen total.

---

## Phase 3: System-Architektur vereinheitlichen

> **Ziel:** Klare, konsistente Regeln wie Systems arbeiten.

### Task 3.1 — System-Kategorien definieren und dokumentieren

Definiere in CLAUDE.md vier Kategorien:

1. FRAME-PROCESSORS: Registriert bei esper, laufen über esper.process()
   → TurnSystem, EquipmentSystem, VisibilitySystem, MovementSystem,
     CombatSystem, FCTSystem

2. PHASE-SYSTEMS: Manuell aufgerufen in spezifischen Game-Phasen
   → AISystem (ENEMY_TURN), ScheduleSystem (ENEMY_TURN)

3. RENDER-SYSTEMS: Manuell aufgerufen während draw(); werden bei jedem startup() neu erstellt
   → RenderSystem, UISystem, DebugRenderSystem

4. EVENT-SYSTEMS: Reagieren nur auf Events, kein process()
   → DeathSystem (entity_died)

### Task 3.2 — DeathSystem korrekt kategorisieren

DeathSystem ist aktuell beides: Processor UND Event-Handler.

- Entferne esper.add_processor(self.death_system) aus startup()
- DeathSystem ist nur noch Event-Handler (set_handler in **init** bleibt)
- Leere process() Methode entfernen
- DeathSystem muss weiterhin in persist gespeichert werden (wegen map_container Referenz)

**Akzeptanz:** `DeathSystem` hat keine leere `process()` mehr. Entity-Death funktioniert weiterhin.

### Task 3.3 — set_map() Pattern vereinheitlichen

Problem: Manche Systems bekommen map_container im Constructor,
manche über set_map(), manche beides.

Lösung: MapAwareSystem Mixin:

```python
class MapAwareSystem:
    def __init__(self):
        self._map_container = None

    def set_map(self, map_container):
        self._map_container = map_container
```

Alle Systems die Maps brauchen erben davon:
→ VisibilitySystem, MovementSystem, ActionSystem, DeathSystem, RenderSystem, DebugRenderSystem

Rule: Constructor nimmt KEIN map_container mehr. set_map() wird nach
Erstellung und bei jedem Map-Wechsel (MapTransitionService) aufgerufen.

**Akzeptanz:** Kein System hat `map_container` als Constructor-Parameter.

---

## Phase 4: Map-System stabilisieren

> **Ziel:** freeze/thaw sicher machen, MapService fokussieren.

### Task 4.1 — freeze/thaw ohne esper-Internals

Problem: map_container.freeze() greift auf actual_world._entities zu
(doppelte Indirektion:_world + _entities).

Empfohlene Lösung — MapBound Marker Component:

```python
@dataclass
class MapBound:
    """Marker: Entity gehört zu dieser Map und wird mitgefroren."""
    pass
```

Vorgehen:

1. Alle nicht-Party Entities beim Erstellen mit MapBound markieren
   (EntityFactory.create() setzt MapBound automatisch)
2. freeze() iteriert nur Entities mit MapBound:

```python
   def freeze(self, world, exclude_entities):
       self.frozen_entities = []
       for ent, _ in list(esper.get_component(MapBound)):
           if ent not in exclude_entities:
               self.frozen_entities.append(
                   [esper.component_for_entity(ent, t)
                    for t in KNOWN_COMPONENT_TYPES
                    if esper.has_component(ent, t)]
               )
               world.delete_entity(ent)
       world.clear_dead_entities()
```

KNOWN_COMPONENT_TYPES muss alle Component-Klassen kennen (zentrales Registry
in components.py oder via **subclasses**).

Vorteil gegenüber Alternative: Keine Iteration aller Component-Typen nötig,
klar welche Entities zur Map gehören.

**Akzeptanz:** `freeze()`/`thaw()` nutzt keine `_`-prefixed Attribute von esper. Smoke-Test für freeze/thaw bleibt grün.

### Task 4.2 — MapService aufteilen

services/map_service.py aufteilen:

```python
services/
├── map_service.py            # Nur Map-Registry + aktive Map Verwaltung
├── map_generator.py          # Village-Szenario, Terrain-Variety, Prefabs
└── spawn_service.py          # Monster/NPC Spawning Logik
```

map_service.py behält:

- register_map(), get_map(), set_active_map(), get_active_map()

map_generator.py bekommt:

- create_village_scenario(), create_sample_map()
- apply_terrain_variety(), add_house_to_map()
- load_prefab()

spawn_service.py bekommt:

- spawn_monsters()
- NPC-Spawning aus create_village_scenario()

**Akzeptanz:** `map_service.py` ist < 80 Zeilen.

### Task 4.3 — Village-Szenario daten-getrieben machen

Erstelle assets/data/scenarios/village.json:

```json
{
  "id": "Village",
  "width": 40, "height": 40,
  "layers": 3,
  "base_tile": "floor_stone",
  "terrain_variety": { "chance": 0.1, "types": ["floor_stone"] },
  "structures": [
    {
      "id": "Cottage",
      "village_pos": [5, 5], "village_size": [6, 6],
      "interior_size": [10, 10], "floors": 2
    },
    ...
  ],
  "npcs": [
    { "template": "guard", "pos": [35, 35], "map": "Village" },
    { "template": "shopkeeper", "pos": [5, 5], "map": "Shop" },
    ...
  ]
}
```

map_generator.py liest diese Datei statt Hardcoding.

**Akzeptanz:** Neues Gebäude hinzufügen = nur JSON editieren.

---

## Phase 5: Konsistenz & Code-Qualität

> **Ziel:** Einheitliche Patterns, keine Inline-Imports, sauberes Error-Handling.

### Task 5.1 — Inline-Imports auflösen

Bekannte Stellen:

- combat_system.py Zeile 34: `from ecs.components import AIBehaviorState, AIState` innerhalb process()
- action_system.py Zeile 272: `from ecs.components import AIBehaviorState, AIState, Name` in wake_up()

Strategie:

- Echte zirkuläre Abhängigkeiten über Interface/Protocol lösen
- Lazy Imports nur wo wirklich nötig, mit Kommentar warum

**Akzeptanz:** `grep -rn "^\s\+from\|^\s\+import" --include="*.py" ecs/ services/` zeigt keine Imports innerhalb von Funktionsbodies (außer dokumentierte Ausnahmen).

### Task 5.2 — Error-Handling Pattern vereinheitlichen

Definiere klares Pattern:

1. Component-Zugriff wo Entity garantiert Component hat:
   → esper.component_for_entity(ent, Comp)  (KeyError = Bug)

2. Component-Zugriff wo Component optional ist:
   → esper.try_component(ent, Comp)  (Returns None)

3. NICHT: try/except KeyError um component_for_entity()
   (Ausnahme: Legacy-Code der schrittweise migriert wird)

Durchsuche alle Systems und migriere zu diesem Pattern.

**Akzeptanz:** Keine `try/except KeyError` um `component_for_entity()` Aufrufe mehr (außer wo explizit kommentiert).

### Task 5.3 — Logging statt print()

Nutze Python logging Modul (kein neues Service nötig):

- Konfiguriere Logger am Programmstart in main.py
- Logger pro Modul: logging.getLogger(**name**)
- Level: DEBUG für AI/Pathfinding, INFO für Map/Combat-Events, WARNING für unerwartetes
- Debug-Toggles steuern Log-Level zur Laufzeit
- Ersetze alle print() Aufrufe

**Akzeptanz:** `grep -rn "^\s*print(" --include="*.py" ecs/ services/ game_states.py` = 0 Treffer.

---

## Phase 6: Feature-Stubs vervollständigen

> **Ziel:** Halbfertige Features entweder fertig machen oder sauber entfernen.

### Task 6.1 — Talk-Interaction

Aktuell: "You bump into X. They look at you."
Minimal-Lösung: Einfaches Dialogue-System

Erstelle:

- assets/data/dialogues.json (template_id → dialogue lines)
- services/dialogue_service.py
- Dialogue Component für NPCs
- UI-Anzeige im Message Log oder als Window

**Akzeptanz:** Bump auf NEUTRAL NPC zeigt mindestens eine kontextuelle Dialogue-Zeile an.

### Task 6.2 — Ranged/Spells Action

Aktuell: print(f"Executed {targeting.action.name} at (...)")
Minimal-Lösung:

- Ranged: AttackIntent auf Ziel-Entity erstellen → CombatSystem verarbeitet
- Spells: Einfacher Effekt (Damage in Area, Heal, Buff)
- Erstelle services/ability_service.py für Action-Execution

**Akzeptanz:** Ranged-Action trifft Ziel und verursacht Schaden über CombatSystem. Spell zeigt Effekt und verbraucht Mana.

### Task 6.3 — Player Death

Aktuell: Kein Handling wenn Player HP ≤ 0 — Spiel läuft ohne Reaktion weiter.
Minimal-Lösung:

- DeathSystem.on_entity_died() prüft ob gestorbene Entity PlayerTag hat
- → Dispatch "player_died" Event
- → Game-Over Screen (neuer GameState) oder Respawn-Logik

**Akzeptanz:** Wenn Player HP ≤ 0 erreicht, erscheint Game-Over Screen oder Respawn.

### Task 6.4 — Audit aller TODO/FIXME/Stub-Kommentare

```python
grep -rn "TODO\|FIXME\|HACK\|STUB\|XXX" --include="*.py"
→ Für jeden Treffer: Fix, Remove, oder in .planning/quick/ als separates Task-File anlegen
```

**Akzeptanz:** `grep` liefert 0 Treffer oder alle verbleibenden Kommentare haben einen `.planning/quick/` Eintrag.

---

## Phase 7: Dokumentation & Projekt-Hygiene

> **Ziel:** Projekt ist für zukünftige Entwicklung bereit.

### Task 7.1 — CLAUDE.md aktualisieren

Nach allen Refactoring-Phasen CLAUDE.md updaten:

- Neue Projektstruktur (config/, map_generator.py, spawn_service.py, etc.)
- System-Kategorien (Frame-Processor, Phase-System, Render-System, Event-System)
- MapBound Component dokumentieren
- MapAwareSystem Mixin dokumentieren
- Neue Konventionen (Logging, Error-Handling)

### Task 7.2 — README.md erstellen

- Projekt-Beschreibung
- Screenshot/GIF
- Setup-Anleitung
- Feature-Liste
- Architektur-Übersicht (kurz)

### Task 7.3 — Pre-Commit Hooks (optional)

- Linting (ruff)
- Type-Checking (mypy, zumindest partial)
- Test-Run (nur Smoke-Tests für schnelles Feedback)

---

## Ausführungsreihenfolge & Aufwand

| Phase   | Beschreibung                  | Tasks | Risiko  | Aufwand        |
|---------|-------------------------------|-------|---------|----------------|
| 0       | Sicherheitsnetz               | 3     | Niedrig | 1 Session      |
| 1       | Config aufräumen              | 3     | Niedrig | 1 Session      |
| 3.3     | MapAware Mixin                | 1     | Mittel  | 0.5 Session    |
| 2       | game_states.py entflechten    | 4     | Hoch    | 2-3 Sessions   |
| 3.1+3.2 | System-Kategorien + Death     | 2     | Niedrig | 0.5 Session    |
| 4       | Map-System                    | 3     | Hoch    | 2 Sessions     |
| 5       | Code-Qualität                 | 3     | Niedrig | 1-2 Sessions   |
| 6       | Feature-Stubs                 | 4     | Mittel  | 2-3 Sessions   |
| 7       | Dokumentation                 | 3     | Niedrig | 1 Session      |

Total: **~12-15 Sessions mit Claude Code**

---

## Wie mit Claude Code arbeiten

### Pro Task

```bash
1. "Lies dir Phase X, Task X.Y durch und zeig mir deinen Plan"
2. Claude Code analysiert betroffene Dateien
3. Review des Vorschlags
4. "Implementiere es"
5. python -m pytest tests/test_smoke.py -v
6. Commit: "refactor(phase-X): Task X.Y — [Beschreibung]"
```

### Wichtige Prompts für Claude Code

```bash
- "Zeig mir alle Stellen die von dieser Änderung betroffen sind"
- "Welche Tests brauchen wir bevor wir anfangen?"
- "Implementiere nur Task X.Y, ändere nichts anderes"
- "Validiere dass die Smoke-Tests noch grün sind"
```

### Reihenfolge-Regeln

- Phase 0 IMMER zuerst (Sicherheitsnetz)
- Phase 1 vor Phase 2 (Config muss sauber sein bevor Game aufgeteilt wird)
- **Task 3.3 vor Task 2.3** (MapAware Mixin muss feststehen bevor SystemInitializer gebaut wird)
- Phase 4 nach Phase 3 (System-Patterns müssen feststehen)
- Phase 5 kann jederzeit nach Phase 2 laufen
- Phase 6 nach Phase 2-5 (saubere Basis für neue Features)
- Phase 7 ganz am Ende
