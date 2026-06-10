# Architektur-Konzept — Aufräumen statt Neubau

> **Stand:** Juni 2026 · Nachfolger von `REFACTORING_PLAN.md` ("Back on Track")
> **Befund-Basis:** Vollanalyse aller 112 Python-Dateien (~12.400 LOC), 134 grüne Tests
>
> **STATUS: UMGESETZT.** Alle Phasen R0–R6 sind implementiert (siehe Commits
> `test(R0)` bis `refactor(R6)`). Die Ziel-Verzeichnisstruktur aus Abschnitt 4.6
> ist live, die Schichtregel wird durch `tests/verify_layering.py` maschinell
> geprüft, und CLAUDE.md beschreibt die neue Architektur. Dieses Dokument
> bleibt als Begründung der Entwurfsentscheidungen erhalten.

---

## 1. Kurzfassung & Empfehlung

**Kein Neubau. Gezielter Umbau in 6 Phasen.**

Die Diagnose "zu verbaut" stimmt — aber sie betrifft fast ausschließlich die
**Orchestrierungsschicht** (Game-Loop, Input, Verdrahtung), nicht das Fundament:

| Schicht | Zustand |
|---|---|
| Daten-Layer (JSON, Registries, Factories) | ✅ solide, datengetrieben, behalten |
| ECS-Kern (Components, Systeme, Events) | ✅ solide Struktur, kleine Korrekturen |
| Services (Pathfinding, FOV, Clock, Dialogue) | ✅ fokussiert, behalten |
| Map-System (Container, Layer, freeze/thaw) | 🟡 funktioniert, API-Härtung nötig |
| **Orchestrierung** (`game_states.py`, `persist`-Dict, Initializer) | 🔴 hier sitzt der Schmerz |

Ein Rewrite würde ~12k Zeilen funktionierendes, getestetes Verhalten wegwerfen,
um am Ende dieselben Systeme wieder zu bauen — und erfahrungsgemäß dieselben
Orchestrierungsprobleme erneut zu erzeugen, weil das eigentliche Problem nie ein
fehlendes Framework war, sondern **fehlende Verdrahtungs-Regeln**. Die 134
grünen Tests sind genau das Sicherheitsnetz, das einen Umbau im Bestand
realistisch macht; bei einem Neubau wäre es wertlos.

---

## 2. Befund: Die fünf strukturellen Probleme

### P1 — Abgebrochenes Refactoring: doppeltes Input-Handling (KRITISCH)
`REFACTORING_PLAN.md` Task 2.1 wurde nur halb umgesetzt:
`services/game_input_handler.py` existiert mit der kompletten Input-Logik,
wird in `game_states.py:179` instanziiert — **aber nie aufgerufen**.
`Game.get_event()` nutzt weiterhin die eigenen Kopien:

- `handle_player_input()` — dupliziert (`game_states.py:238` ↔ `game_input_handler.py:38`)
- `pickup_item()` — dupliziert (`game_states.py:425` ↔ `game_input_handler.py:241`)
- `try_enter_portal()`, `move_player()` — ebenfalls dupliziert

Jede Änderung muss aktuell zweimal gemacht werden (bzw. wirkt nur in einer
der beiden Kopien — klassische Bug-Quelle).

### P2 — `Game`-Gott-Klasse (KRITISCH)
`game_states.py:88-561`: eine Klasse mit 5 Verantwortlichkeiten —
State-Management, Input-Dispatch, Spieler-Aktionen (Pickup/Portal inline mit
esper-Zugriffen), Game-Loop/Phasensteuerung und Rendering-Pipeline.

### P3 — `persist`-Dict als unsichtbares Gott-Objekt (HOCH)
Der gesamte Spielzustand wandert als untypisiertes `dict` mit String-Keys
durch alle States. `SystemInitializer.initialize()` macht daraus bei jedem
`startup()` ein fragiles Lazy-Init-und-Rewire-Ritual
(`turn_system.world_clock = world_clock` etc.). Niemand kann am Code ablesen,
was im Dict steckt und wer es mutiert. `MapTransitionService.initialize_context()`
bekommt dasselbe Dict noch einmal injiziert.

### P4 — Keine Regel für Events vs. Direktaufrufe (HOCH)
`log_message`, `change_map`, `entity_died` laufen als Events;
`end_player_turn()`, `perform_action()`, `ai_system.process()` als
Direktaufrufe — ohne erkennbares Prinzip. Folge: Kontrollfluss ist schwer
nachvollziehbar, neue Features kopieren zufällig eines der beiden Muster.

### P5 — Globaler Zustand überall (MITTEL, langfristig teuer)
esper ist modul-global (esper-3.x-Design, akzeptierbar), aber zusätzlich sind
alle Registries (`TileRegistry`, `EntityRegistry`, `ItemRegistry`,
`ScheduleRegistry`, `DialogueService`) Klassen-Singletons. Tests müssen manuell
`reset_world()` + `clear()` aufrufen; Vergessen erzeugt Heisenbugs.

*(Kleinere Punkte: duplizierte Magic-Rects `(140, 100, 1000, 500)` an 6+
Stellen, toter `get_world()`-Shim, Fallback-Mapgenerierung in
`map_transition_service.py:70`.)*

---

## 3. Grundsatzentscheidung: Spiel, kein Framework

Das "zu verbaut für beides"-Gefühl entsteht, weil das Projekt unentschieden
zwischen Engine und Spiel steht. Die Entscheidung:

> **Es ist ein Spiel.** Wiederverwendbarkeit ist kein Ziel, sondern ein
> Nebenprodukt sauberer Schichtung.

Statt Framework-Ambitionen gibt es **eine** harte Regel, die denselben Effekt
hat:

```
core/   (spielagnostisch: ECS-Glue, Input-Mapping, Rendering-Primitives,
         Daten-Lader, UI-Stack, Kamera, FOV, Pathfinding, Clock)
game/   (alles Roguelike-Spezifische: Components, Systeme, States,
         Spielregeln, Content-Verdrahtung)

Regel: core/ importiert NIEMALS aus game/. game/ darf alles aus core/ nutzen.
```

Sollte je ein zweites Spiel entstehen, ist `core/` automatisch der
wiederverwendbare Teil — ohne dass dafür heute Framework-Abstraktionen
gebaut werden müssen.

---

## 4. Zielarchitektur

### 4.1 Schichten und Abhängigkeitsrichtung

```
main.py (Bootstrap / Composition Root)
   │  baut GameContext, lädt Content, verdrahtet alles GENAU EINMAL
   ▼
states/ (dünne Zustands-Hüllen: Title, Gameplay, WorldMap, GameOver)
   │  delegiert nur — kein esper, keine Spielregeln
   ▼
controller-Schicht (pro Gameplay-Aspekt eine Klasse)
   ├── InputController     Events → Commands → PlayerActionService
   ├── TurnOrchestrator    Phasenablauf (PLAYER_TURN → ENEMY_TURN → …)
   └── RenderPipeline      Map → Entities → Debug → Tint → UI
   ▼
systems/ + services/ (Spiellogik, wie heute — aber mit klaren Verträgen)
   ▼
core/ (ECS-Glue, Daten, Primitives)
```

### 4.2 `GameContext` statt `persist`-Dict

Ein typisiertes Objekt ersetzt das String-Key-Dict:

```python
@dataclass
class GameContext:
    """Alle langlebigen Objekte einer Spielsitzung. Wird im Bootstrap
    einmal gebaut und an States/Controller injiziert."""
    content: ContentDatabase          # Registries als Instanzen
    map_service: MapService
    world_clock: WorldClockService
    camera: Camera
    ui_stack: UIStack
    input_manager: InputManager
    systems: Systems                  # dataclass, nicht dict
    player_entity: int | None = None
    debug_flags: DebugFlags = field(default_factory=DebugFlags)
```

- `SystemInitializer` wird zur echten, einmaligen **Factory**
  (`build_systems(ctx) -> Systems`); das Lazy-Init-Rewire-Muster entfällt.
- `Systems` ist eine dataclass mit benannten Feldern statt `systems["ai_system"]`.
- States erhalten `ctx` in `startup()` — der Inhalt ist ab dann per IDE
  navigierbar und statisch prüfbar (mypy).

### 4.3 Command-Pfad für Spieleraktionen

Heute: Input-Handler greifen direkt in esper (Pickup-Gewichtsrechnung im
Input-Code!). Ziel: drei klar getrennte Stufen.

```
pygame.Event ──InputManager──▶ InputCommand (existiert schon)
InputCommand ──InputController──▶ Aufruf PlayerActionService
PlayerActionService ──▶ Spielregel ausführen (esper, Komponenten, Turn-Ende)
```

`PlayerActionService` (neu, `game/services/`) übernimmt: `move`, `pickup`,
`enter_portal`, `use_hotbar_slot`, `select_action`, `start/confirm/cancel
targeting`. Der InputController kennt **kein esper** mehr — er übersetzt nur.
Damit wird die gesamte Spieler-Regel-Logik unit-testbar ohne Pygame.

### 4.4 Event-Policy (eine Regel, dokumentiert in CLAUDE.md)

> **Befehle nach unten, Fakten nach oben.**
> - *Direktaufruf*, wenn der Aufrufer ein Ergebnis braucht oder die Reihenfolge
>   garantieren muss (z. B. `perform_action()`, `orchestrator.end_player_turn()`).
> - *Event*, wenn etwas **passiert ist** und beliebig viele Beobachter
>   reagieren dürfen (`entity_died`, `map_changed`, `log_message`,
>   `player_died`, `item_picked_up`).
> - Events tragen Vergangenheits-Namen. Wer ein Event dispatcht, darf sich
>   nicht darauf verlassen, dass ein Handler existiert.

### 4.5 Registries als Instanzen (`ContentDatabase`)

```python
class ContentDatabase:
    tiles: TileRegistry
    entities: EntityRegistry
    items: ItemRegistry
    schedules: ScheduleRegistry
    dialogues: DialogueRegistry

    @classmethod
    def load(cls, data_dir: Path) -> "ContentDatabase": ...
```

Die Registry-Klassen bleiben, verlieren aber ihren Klassen-Zustand.
Tests bauen sich eine frische `ContentDatabase` (oder eine Mini-Variante mit
3 Tiles) — `clear()`-Disziplin entfällt. Factories bekommen die Registry
injiziert statt sie zu importieren.

### 4.6 Ziel-Verzeichnisstruktur

```
main.py                      # nur Entry: pygame.init + bootstrap + loop
bootstrap.py                 # Composition Root: baut GameContext
core/
├── ecs.py                   # reset_world etc. (ersetzt ecs/world.py-Shim)
├── data/                    # Loader, Registry-Basisklasse
├── input/                   # InputManager, InputCommand
├── render/                  # RenderService, Camera, Primitives
├── ui/                      # UIStack, Window-Basis, MessageLog
└── services/                # FOV, Pathfinding, WorldClock
game/
├── components.py
├── content/                 # ContentDatabase, Factories
├── systems/                 # wie heute (Frame/Phase/Render/Event-Kategorien)
├── services/                # PlayerActionService, MapTransition, Spawn, …
├── controllers/             # InputController, TurnOrchestrator, RenderPipeline
└── states/                  # title.py, gameplay.py, world_map.py, game_over.py
assets/data/                 # unverändert
tests/
├── conftest.py              # autouse-Fixture: reset_world + frische Registries
├── unit/                    # reine Logik, ohne Pygame/Map-Aufbau
└── integration/             # heutige verify_*-Tests
```

---

## 5. Migrationsplan (Strangler, jede Phase einzeln mergebar)

**Eiserne Regel jeder Phase:** Tests bleiben grün, Spiel bleibt startbar,
ein Commit pro Task (bestehende Projektregel).

### Phase R0 — Sicherheitsnetz härten *(0,5 Sessions, Risiko: keins)*
- `tests/conftest.py` mit autouse-Fixture: `reset_world()` + Registry-`clear()`
  vor jedem Test (ersetzt die manuelle Disziplin).
- `requirements.txt` + `requirements-dev.txt` anlegen.
- `ruff` als Lint-Standard festschreiben (Konfig existiert offenbar schon).
- **Akzeptanz:** Testlauf grün ohne dass Einzeltests selbst aufräumen müssen.

### Phase R1 — Duplikation eliminieren *(1 Session, Risiko: niedrig)* ⬅ Quick Win
- Task 2.1 des alten Plans **zu Ende führen**: `Game.get_event()` delegiert an
  `GameInputHandler`; die vier duplizierten Methoden aus `game_states.py`
  löschen. Vorher per Diff prüfen, welche Kopie die aktuellere ist
  (`game_input_handler.py` hat z. B. ein zusätzliches `end_player_turn()` nach
  Pickup — Verhalten bewusst entscheiden).
- Magic-Rect `(140, 100, 1000, 500)` → `config/ui.py` als `UI_WINDOW_RECT_*`.
- `ecs/world.py`-Shim: `get_world()`-Aufrufer auf direktes `import esper`
  umstellen, Shim auf `reset_world()` reduzieren.
- **Akzeptanz:** kein Codeblock existiert doppelt; `Game` < 300 Zeilen.

### Phase R2 — `GameContext` + Composition Root *(1–2 Sessions, Risiko: mittel)*
- `bootstrap.py` mit `build_game_context()`; `GameController` nutzt `ctx`.
- `persist`-Dict durch `GameContext` ersetzen; `SystemInitializer` →
  `build_systems(ctx)` (einmalig, kein Rewire), `Systems`-dataclass.
- `MapTransitionService.initialize_context()` entfällt — bekommt `ctx` im
  Konstruktor.
- **Akzeptanz:** kein `persist.get("...")` mehr im Code; mypy läuft über
  `bootstrap.py` + `states/` fehlerfrei.

### Phase R3 — Command-Pfad / `PlayerActionService` *(1–2 Sessions, Risiko: mittel)*
- `PlayerActionService` extrahieren (Pickup, Portal, Move, Hotbar, Targeting).
- `GameInputHandler` → `InputController`: nur noch Übersetzung
  Command → Service-Aufruf.
- Unit-Tests für die Service-Methoden (erste echte Unit-Tests im Projekt).
- **Akzeptanz:** `grep "import esper" game/controllers/` = 0 Treffer.

### Phase R4 — Zustands-Zerlegung + Event-Policy *(1–2 Sessions, Risiko: mittel)*
- `Game` → `GameplayState` als dünner Koordinator über `InputController`,
  `TurnOrchestrator` (übernimmt die ENEMY_TURN-Steuerung aus `update()`),
  `RenderPipeline` (übernimmt `draw()`).
- Event-Policy (4.4) in CLAUDE.md dokumentieren; bestehende Events auf
  Vergangenheits-Namen prüfen (`change_map` → dispatcht künftig
  `map_change_requested` oder bleibt Direktaufruf — nach Policy entscheiden).
- **Akzeptanz:** `game_states.py` existiert nicht mehr; kein State > 150 Zeilen.

### Phase R5 — `ContentDatabase` *(1 Session, Risiko: niedrig)*
- Registries auf Instanzen umstellen, `ContentDatabase.load()` im Bootstrap,
  Injektion in Factories. Übergangsweise dürfen die alten Klassen-APIs als
  deprecated Wrapper bestehen bleiben, bis alle Aufrufer migriert sind.
- **Akzeptanz:** kein `clear()`-Aufruf in Tests mehr nötig.

### Phase R6 — `core/` vs. `game/` Reorganisation *(1 Session, Risiko: niedrig)*
- Rein mechanisches Verschieben gemäß 4.6 (git mv + Import-Update) —
  **bewusst zuletzt**, wenn die Verantwortlichkeiten schon sauber sind.
- Import-Linter-Check (oder simpler Test): `core/` importiert nichts aus `game/`.
- CLAUDE.md vollständig aktualisieren.
- **Akzeptanz:** Schichtregel maschinell geprüft, Tests grün.

**Gesamtaufwand: ~6–9 Sessions.** Nach R1 ist der akuteste Schmerz weg,
nach R3 ist neue Feature-Entwicklung bereits deutlich billiger — R4–R6 können
entspannt zwischen Feature-Arbeit geschoben werden.

---

## 6. Was bewusst NICHT gemacht wird

- **Kein esper-Wrapper / keine eigene ECS-Abstraktion.** esper-3.x ist
  modul-global by design; ein Wrapper würde nur API-Lärm erzeugen. Die
  Test-Isolation lösen conftest-Fixtures.
- **Kein DI-Container.** `bootstrap.py` als handgeschriebene Composition Root
  reicht bei dieser Projektgröße völlig.
- **Kein Engine-/Plugin-System.** Die `core/`-Regel liefert Modularität ohne
  Framework-Kosten.
- **Kein Big-Bang-Umbau der Tests.** Die `verify_*`-Integrationstests bleiben
  als Sicherheitsnetz; Unit-Tests wachsen dort, wo Logik extrahiert wird.

---

## 7. Arbeitsweise

Wie beim alten Plan: pro Task ein Commit, Smoke-Tests vor jedem Merge grün,
eine Phase pro Branch (`refactor/r1-input-dedup` usw.). Jede Phase endet mit
einem CLAUDE.md-Update, damit die Doku nie wieder hinter den Code zurückfällt
(genau das ist beim letzten Plan mit Task 2.1 passiert: Doku sagte "extracted
from Game", Code sagte etwas anderes).
