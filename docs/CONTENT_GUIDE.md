# Rogue Like RPG Engine — Technische Dokumentation (ECS Data-Driven Guide)

**Version:** 1.1 (Code-Stand: 23.06.2026)
**Zweck:** Zentrales Regelwerk für Content-Erstellung via JSON. Diese
Dokumentation dient als Spezifikation für die Generierung valider
JSON-Game-Data und als Leitfaden für das Hinzufügen neuer Inhalte.

> Die kanonische Architektur-Referenz ist `CLAUDE.md` im Projektwurzel. Bei
> Abweichungen gilt der Code (`config/`, `game/components.py`,
> `game/services/`) als Quelle der Wahrheit.

---

# 1. Engine Architektur & Feature-Übersicht

## 1.1 ECS-Architektur

Die Engine basiert auf **Entity-Component-System (ECS)** unter Verwendung der
Python-Bibliothek `esper` (3.x, Modul-Level-API — es gibt **keine**
`World`-Instanz, alle Aufrufe gehen direkt über das `esper`-Modul). Jede
Spielentität ist eine reine Integer-ID. Eigenschaften werden durch
**Component-Dataclasses** beschrieben; Verhalten von **Systemen**.

- **Entities:** Integer-IDs, erzeugt via `esper.create_entity(*components)`
- **Components:** Plain `@dataclass`-Objekte, ausschliesslich Daten, keine
  Logik. Persistenz: automatisch JSON-serialisierbar.
- **Systeme:** Vier Kategorien (siehe 2.2) — nicht alle sind `esper.Processor`.
- **Templates (Flyweights):** Geteilte, unveränderliche Daten pro Entitätstyp —
  geladen aus JSON via `ResourceLoader` in Registry-Instanzen.
- **Factories:** `EntityFactory` und `ItemFactory` instantiieren ECS-Entities
  aus Registries zur Laufzeit.

**Determinismus:** Alle run-bezogene Zufälligkeit (Ökonomie-Jitter,
Crafting-Qualität, Gossip-Auswahl, Wildnis-Streuung) leitet sich aus einem
einzigen `ctx.world_seed` ab — `core/rng.py::derive_seed(seed, label)` erzeugt
pro Subsystem einen stabilen Teilseed. `--seed` setzt ihn; ein Seed
reproduziert denselben Spielverlauf.

## 1.2 Kern-Feature-Liste

### Welt & Exploration
- **Multi-Layer Maps:** Mehrere Kartenlayer (Boden, Dekoration, Entity, Dach)
  mit Portalen zwischen Innen- und Aussenbereichen
- **Siedlungen (Settlements):** Prozedural generiert aus JSON-Szenarien mit
  Gebäuden, NPCs, Ökonomie
- **Points of Interest (POI):** Dungeons (Old Ruins, Sunken Crypt, Bandit Camp,
  Abandoned Mine) — eigene `world.json`-Knoten vom `type: "poi"`, thematisiert
  über `monsters`/`cache`/`resources`-Felder
- **Wildnis (Wilderness):** Biom-basierte prozedurale Generierung mit Flora,
  Fauna und Ressourcen-Knoten
- **Versteckte Geheimnisse (Hidden):** Entitäten mit `Hidden`-Component werden
  erst bei Näherung sichtbar (perception-gated)
- **Tag-/Nacht-Zyklus:** Lichtquellen (Fackeln, Lagerfeuer) brennen von
  Dämmerung bis Morgengrauen; Sichtradius via `VisibilitySystem`
- **Zweistufige Ortsentdeckung:** Orte sind erst unbekannt, dann **`heard`**
  (man weiss, dass es sie gibt — ein Lead) und schliesslich **`discovered`**
  (Route bekannt, bereisbar). Wissen verbreitet sich über NPC-Gespräche
  (Wegauskunft / Rumors). Beide Stufen werden gespeichert.

### Kampf & Status
- **Rundenbasiertes Kampfsystem:** Spielerzug -> Gegnerzug, initiiert via
  `TurnSystem`
- **Schadensberechnung:** Angriffskraft +/- Varianz - Verteidigung; minimale
  Schadensgrenze `COMBAT_MIN_DAMAGE`
- **Kritische Treffer:** Chance via `COMBAT_CRIT_CHANCE`, verdoppelter Schaden +
  `Bleeding`-Status
- **Bluten (Bleeding):** Verlust von HP pro Runde für `BLEED_TURNS` Runden
- **EffectiveStats-Pattern:** Basisstats + Ausrüstungsboni +
  Tageszeitmultiplikator (perception) — berechnet vom `EquipmentSystem`

### Inventar & Ausrüstung
- **Traglast (Encumbrance):** Jedes Item hat Gewicht (`Portable`); max.
  Tragkraft in `Stats.max_carry_weight`
- **Ausrüstungsslots:** Kopf, Rumpf, Waffenhand, Schildhand, Füsse, Accessoire
- **Stat-Modifikatoren:** Ausrüstungsgegenstände modifizieren HP, Kraft,
  Verteidigung, Mana, Wahrnehmung, Intelligenz

### Ökonomie & Handel
- **Handelssystem:** Kaufe/Verkaufe Items bei NPCs mit `Merchant`-Component und
  `Purse` (Gold)
- **Lager-Wiederauffüllung:** `base_stock` definiert Grundsortiment;
  `MerchantRestockService` füllt stündlich auf — aber nur solange die Siedlung
  das Gut noch in abstraktem Bestand hat
- **Ökonomie-Simulation:** Pro Siedlung: Lagerbestände, Produktionsraten (mit
  `requires`-Lieferketten), Verbrauch, Wohlstand (Prosperity)

### Crafting
- **Crafting-Stationen:** **10 Stationstypen:** `forge`, `anvil`, `mill`,
  `oven`, `tannery`, `herbalist`, `jeweler`, `loom`, `sawmill`, `kitchen`
- **Rezepte:** Definiert Input-Items, Output-Item, Station, Dauer in Ticks
- **Metall-Lieferkette:** Die **forge** verhüttet nur Erz zu Barren
  (`iron_ore`/`silver_ore` → Barren, plus Stahlkette `iron_ore`+`coal` →
  `steel_ingot` — `coal` ist der einzige erlaubte Nicht-Erz-Forge-Input). Der
  **anvil** schmiedet nur Barren zu Waffen/Rüstung. Die Trennung spiegelt die
  Siedlungs-Lieferkette (Brackenfen=Mine/Forge, Eastmoor=Smithy/Anvil).
- **Qualitätssystem:** Equippable-Crafts erhalten ein benanntes Qualitätstier
  (Crude/Standard/Fine/Masterwork, beeinflusst Stats und Wert); nicht-Equippable
  skalieren stattdessen in Menge (`quantity_bonus`)
- **Skill-System:** Learn-by-doing: Handwerks- und Sammelaktionen trainieren den
  zugehörigen Skill (Level abgeleitet aus XP via `SkillService`)

### NPCs & soziale Simulation
- **KI-System:** Zustandsautomat: `idle`, `wander`, `chase`, `talk`, `work`,
  `patrol`, `socialize`, `sleep`
- **Schedules (Tagespläne):** Zeitbasierte NPC-Routinen
- **Bedürfnisse (Needs):** Hunger steigt mit Spielzeit; über Schwellenwert
  unterbricht der NPC seinen Schedule zum Essen
- **Gossip-System:** NPCs unterhalten sich, erwähnen andere NPCs und
  Chronik-Ereignisse
- **Beziehungen (Relationships):** NPC-NPC-Affinitäten (-100..100) beeinflussen
  Gossip-Inhalte
- **Ortsgebundene Anker:** `HousingService` verteilt pro Siedlung echte
  Arbeits- (`work_anchors`) und Patrouillenwege (`patrol_route`) aus dem
  Szenario, damit Tagescrowds und Wachen die reale Karte bespielen

### Quests
- **Quest-Typen:** `deliver` (Items bringen), `kill` (Gegner töten), `visit`
  (Ort besuchen)
- **Quest-Ketten:** Voraussetzungen über `prerequisites` definierbar
- **Generierte Quests:** Wirtschaftsknappheiten und Chronik-Ereignisse erzeugen
  dynamisch Quests
- **Guide-Quests:** Freundliche Siedlungen vermitteln Quests für Nachbarorte;
  das Annehmen öffnet den Weg dorthin (`offer_location` ≠ `giver_location`)

### Fortbewegung & Reisen
- **Weltkarte:** Graph von Locations mit Reisekosten in Ticks; Routen sind
  bidirektional
- **Reise-Begegnungen:** Zufallsereignisse auf Reisen mit Spawns (Händler,
  Goblins, Banditen, Wolfsrudel)
- **Fraktionskämpfe (Skirmisher):** Begegnungen zwischen rivalisierenden
  Fraktionen

### Faktionssystem
- **Fraktionen:** `townsfolk`, `town_guard`, `bandits`, `monsters`, `wildlife`
- **Fraktionsbeziehungen:** Ally/Enemy-Matrix beeinflusst NPC-Verhalten
- **Ruf (Reputation):** Fraktions-spezifische Standpunkte des Spielers; sinkt
  das Standing auf `FACTION_HOSTILE`, werden die NPCs der Fraktion feindlich

### Persistenz
- **Speichern/Laden:** Serialisierung von ECS-Components, Entities, Karten,
  Quest-Status, Welt-/Fraktionsstand (F9/F10)
- **Transiente Components** werden über `MapBound`-freeze/thaw bzw. den Save
  rekonstruiert statt gespeichert (z.B. `MovementRequest`, `AttackIntent`,
  `Targeting`, `FCT`, `PathData`, `PatrolRoute`)

---

# 2. Component & System Registry

## 2.1 Vollständige Component-Registry

Alle Components sind `@dataclass`-Objekte, automatisch von
`save_serialization.py` kodiert/dekodiert.

### 2.1.1 Kern-Components (von EntityFactory/ItemFactory vergeben)

| Component | Felder | Beschreibung | Zugewiesen von |
|-----------|--------|--------------|----------------|
| `MapBound` | — | Marker: Entity gehört zur aktuellen Karte; freeze/thaw | Factory |
| `Position` | `x: int`, `y: int`, `layer: int = 0` | Koordinaten | Factory |
| `Renderable` | `sprite: str`, `layer: int`, `color: tuple = (255,255,255)` | Darstellung | Factory |
| `TemplateId` | `id: str = ""` | Referenz auf das Registry-Template | Factory |
| `Name` | `name: str` | Anzeigename | Factory |
| `Description` | `base: str`, `wounded_text: str = ""`, `wounded_threshold: float = 0.5` | Beschreibung mit Verletzungs-Variante | Factory |

### 2.1.2 Stats & Kampf

| Component | Felder | Beschreibung |
|-----------|--------|--------------|
| `Stats` | `hp, max_hp, power, defense, mana, max_mana, perception, intelligence: int`, `base_*: int = 0`, `max_carry_weight: float = 20.0` | Basis-Attribute mit Baseline-Speicherung |
| `EffectiveStats` | `hp, max_hp, power, defense, mana, max_mana, perception, intelligence: int` | Laufzeit-Attribute nach Ausrüstung/Tageszeit |
| `StatModifiers` | `hp, power, defense, mana, perception, intelligence: int = 0` | Ausrüstungs-Boni |
| `Skills` | `xp: dict[str, int] = {}` | Skill-XP pro Skill-ID (Level abgeleitet) |
| `Quality` | `tier: int = 1` | Crafting-Qualitätstier (1 = Standard) |
| `Bleeding` | `damage_per_turn: int = 1`, `turns_left: int = 3` | Status: HP-Verlust pro Runde |
| `AttackIntent` | `target_entity: int`, `power_multiplier: float = 1.0` | Transient: Kampfabsicht |

### 2.1.3 Inventar & Items

| Component | Felder | Beschreibung |
|-----------|--------|--------------|
| `Inventory` | `items: list = []` | Liste von Item-Entity-IDs |
| `Equipment` | `slots: dict[SlotType, int\|None]` | Belegte Ausrüstungsslots |
| `Portable` | `weight: float` | Gewicht in kg |
| `Equippable` | `slot: SlotType` | Ausrüstungsslot |
| `ItemMaterial` | `material: str` | Materialtyp (z.B. 'iron', 'wood') |
| `Value` | `amount: int = 0` | Handelswert in Gold |
| `Consumable` | `effect_type: str`, `amount: int`, `consumed_on_use: bool = True` | Verbrauchs-Effekt (`heal_hp`, `heal_mana`) |

SlotType-Enum: `head`, `body`, `main_hand`, `off_hand`, `feet`, `accessory`

### 2.1.4 KI & Verhalten

| Component | Felder | Beschreibung |
|-----------|--------|--------------|
| `AI` | — | Marker: Entity hat KI |
| `AIBehaviorState` | `state: AIState`, `alignment: Alignment` | KI-Zustand und Ausrichtung |
| `Activity` | `current_activity: str = "IDLE"`, `target_pos`, `home_pos`, `need_override: str\|None` | Aktuelle Aktivität |
| `ChaseData` | `last_known_x, last_known_y: int`, `turns_without_sight: int = 0` | Verfolgungs-Status |
| `PathData` | `path: list[tuple]`, `destination: tuple` | A*-Pfad (transient) |
| `Schedule` | `schedule_id: str` | Referenz auf ScheduleTemplate |
| `PatrolRoute` | `waypoints: list[tuple]`, `index: int = 0` | Patrouillen-Wegpunkte (transient, jede Nacht neu) |
| `Needs` | `hunger, hunger_rate=2.0, eat_threshold=70.0, eat_duration_ticks=30, eating_ticks_left=0` | Physische Bedürfnisse |
| `WanderData` | — | Stub für Wander-Verhalten |

AIState-Enum: `idle`, `wander`, `chase`, `talk`, `work`, `patrol`, `socialize`, `sleep`
Alignment-Enum: `hostile`, `neutral`, `friendly`

### 2.1.5 Ökonomie & Interaktion

| Component | Felder | Beschreibung |
|-----------|--------|--------------|
| `Purse` | `gold: int = 0` | Getragenes Gold (separat von Merchant) |
| `Merchant` | `stock: list[str]`, `base_stock: list[str]` | Verkaufs-Sortiment + Wiederauffüllungsbasis |
| `QuestGiver` | — | Marker: NPC bietet Quests an |
| `Innkeeper` | — | Marker: NPC bietet Rast/Schlaf an |

> **Hinweis:** `Merchant` trägt **kein** `gold`-Feld; das `merchant.gold` aus
> dem Template/Szenario wird in eine separate `Purse` übersetzt. Dialoge sind
> kein Component, sondern liegen im `DialogueService`.

### 2.1.6 Umwelt & Welt

| Component | Felder | Beschreibung |
|-----------|--------|--------------|
| `Portal` | `target_map_id: str`, `target_x, target_y: int`, `target_layer: int = 0`, `name: str = "Portal"`, `travel_ticks: int = 1` | Kartenübergang |
| `LightSource` | `radius: int`, `night_only: bool = False` | Lichtquelle (`night_only` = nur Dämmerung..Morgengrauen) |
| `Blocker` | — | Marker: Blockiert Bewegung |
| `Corpse` | — | Marker: Tote Entity |
| `Hidden` | `reveal_radius: int = 2` | Verborgen bis Spielernähe (perception-gated) |
| `Animal` | — | Marker: Wildtier (kein Dialog, Kampf beim Berühren) |
| `Skirmisher` | `side: str = ""` | Fraktionskampf-Seite (Reise-Begegnungen) |
| `ResourceNode` | `item: str`, `skill: str`, `respawn_ticks: int = 240`, `ready_at: int = 0` | Erntbarer Rohstoff-Knoten |
| `Faction` | `faction_id: str = ""` | Zugehörige Fraktion |
| `Relationships` | `affinity: dict[str, int] = {}` | NPC-NPC-Affinität (-100..100) |
| `Residence` | `hearth_pos`, `housed: bool = True`, `gather_pos`, `work_pos`, `patrol_route: list\|None` | Wohn-/Anker-Info (HousingService) |

> `Residence.work_pos` ist der Tages-Arbeitsplatz (aus dem Szenario-`work_anchors`),
> `Residence.patrol_route` der von `HousingService` für *diese* Siedlung
> gebackene Wachweg (aus dem Szenario-`patrol_route`). Beide werden hier
> persistiert, weil die transiente `PatrolRoute` jede Nacht abgeräumt wird.

### 2.1.7 UI & Aktionen

| Component | Felder | Beschreibung |
|-----------|--------|--------------|
| `Action` | `name: str`, `cost_mana: int = 0`, `cost_arrows: int = 0`, `range: int = 0`, `requires_targeting: bool = False`, `targeting_mode: str = "auto"`, `power_multiplier: float = 1.0` | Spieler-Aktion |
| `ActionList` | `actions: list[Action]`, `selected_idx: int = 0` | Verfügbare Aktionen |
| `Targeting` | `origin_x, origin_y, target_x, target_y, range, mode, action, potential_targets, target_idx` | Zielauswahl-Status |
| `MovementRequest` | `dx: int`, `dy: int` | Transient: Bewegungsanforderung |
| `PlayerTag` | — | Marker: Spieler-Entity |
| `TurnOrder` | `priority: int` | Reihenfolge der Zugverarbeitung |
| `FCT` | `text, color, vx, vy, ttl, max_ttl, offset_x, offset_y` | Floating Combat Text |
| `LootTable` | `entries: list[tuple[str, float]]` | Loot: (template_id, chance) |

## 2.2 Vollständige System-Registry

Die Engine kennt **vier Systemkategorien** (siehe CLAUDE.md / `system_initializer.py`).
Nur die Frame-Processors laufen tatsächlich jeden Frame über `esper.process()`;
die übrigen werden gezielt aufgerufen. Diese Unterscheidung bestimmt, wie ein
neues System verdrahtet wird.

### 2.2.1 Frame-Processors (`esper.add_processor`, jeden Frame)

| System | Beschreibung |
|--------|--------------|
| **TurnSystem** | Verwaltet Spieler-/Gegner-Zug und Rundenzähler |
| **EquipmentSystem** | Berechnet `EffectiveStats` aus Basis + Ausrüstung + Tageszeit |
| **VisibilitySystem** | FOV-Berechnung, Tile-Sichtbarkeit, Hidden-Reveal |
| **MovementSystem** | Verarbeitet Bewegung, löst Interaktionen bei Blockern aus |
| **CombatSystem** | Führt Attacken aus, berechnet Schaden, wendet Bluten an, spawnt FCT |
| **FCTSystem** | Bewegt und entfernt Floating Combat Text |

### 2.2.2 Phase-Systeme (vom `TurnOrchestrator` in der Gegnerphase aufgerufen)

Reihenfolge in der `ENEMY_TURN`-Phase: StatusEffectSystem (zuerst) → AISystem →
ScheduleSystem → NeedsSystem → GossipSystem (zuletzt; während Rest-Fastforward
übersprungen).

| System | Beschreibung |
|--------|--------------|
| **StatusEffectSystem** | Tickt Status-Effekte (Bleeding) pro Runde |
| **AISystem** | Gegner-KI: Verfolgung, Patrouille, Wandern, Scharmützel, Loitering |
| **ScheduleSystem** | Aktualisiert NPC-Pläne basierend auf Weltzeit |
| **NeedsSystem** | Hunger-Akkumulation und Essen-Override (preemptet Schedule) |
| **GossipSystem** | Ambient NPC-NPC-Gespräche |

### 2.2.3 Render-Systeme (von der `RenderPipeline` im `draw()` aufgerufen)

| System | Beschreibung |
|--------|--------------|
| **RenderSystem** | Zeichnet Tiles und Entities |
| **UISystem** | HUD, Message-Log, Statusanzeigen |
| **DebugRenderSystem** | Debug-Overlays (F3–F7) |

### 2.2.4 Event-Systeme (nur Handler via `esper.set_handler`, kein `process()`)

| System | Beschreibung |
|--------|--------------|
| **DeathSystem** | Reagiert auf `entity_died`: Loot-Drops, Corpse-Konvertierung, Skill-XP, Cleanup |

### 2.2.5 Action-Dispatch (von Controllern aufgerufen, kein Processor)

| System | Beschreibung |
|--------|--------------|
| **ActionSystem** | Führt Aktionen aus (Warten, Portal, Targeting-Modus), liefert Beschreibungen |

### 2.2.6 Service-Systeme (explizit aufgerufen)

| Service | Beschreibung |
|---------|--------------|
| **QuestService** | Quest-Lebenszyklus: laden, anbieten, annehmen, Fortschritt, abgeben, generieren |
| **CraftingService** | Crafting-Regeln: Rezepte, Materialcheck, Output, Qualität, Skill-Training |
| **GatherService** | Ressourcen-Ernte: Node-Verbrauch, Skill-Bonus, Respawn |
| **SkillService** | Skill-Level aus XP, XP-Vergabe |
| **WorldGraphService** | Weltgraph: Locations, Routen, Entdeckung (heard/discovered), Reisekosten |
| **MapGenerator** | Karten-Generierung: Szenarien, Wildnis, Dungeons, Gebäude, Shelter, Dekoration |
| **DialogueService** | Dialog-Linien: konditionale Auswahl aus JSON |
| **RumorService** | Wegauskunft (Directions) + Rumors/Leads über andere Orte |
| **ContentDatabase** | Fassade für alle Content-Registries |
| **ResourceLoader** | JSON-Parsing und Registry-Befüllung |
| **FactionService** | Fraktionsdisposition, Spieler-Ruf, Alignment-Sync |
| **EconomyService** | Siedlungsökonomie: Lager, Produktion (`requires`), Wohlstand |
| **ReputationService** | Spieler-Standing pro Siedlung (Preise/Dialog) |
| **WorldSimulationService** | Off-Screen-NPC-Simulation, Schedule-Abgleich bei Ankunft |
| **WorldChronicleService** | Per-Location-Eventlog ("Word around town") |
| **MapTransitionService** | Kartenwechsel, Freeze/Thaw von Entities |
| **HousingService** | Wohnungszuweisung, work_anchors/patrol_route-Verteilung |
| **SocialService** | NPC-Beziehungen, Namensgebung |
| **MerchantRestockService** | Stündliche Lager-Wiederauffüllung |
| **PathfindingService** | A*-Pfadfindung |
| **SpawnService** | Monster-/NPC-Spawning (inkl. POI-Themen) |
| **TravelEncounterService** | Reise-Begegnungen |
| **InteractionResolver** | Bestimmt Interaktionstyp beim Berühren |

---

# 3. JSON Data Reference & Constraints

## 3.1 Globale Regeln

### 3.1.1 Dateistruktur

Alle Game-Data-Dateien liegen unter `assets/data/`:

| Datei | Format | Inhalt |
|-------|--------|--------|
| `world.json` | JSON Object | Weltgraph: Locations, Routes, Start-Location |
| `entities.json` | JSON Array | Entity-Templates (NPCs, Monster, Tiere) |
| `items.json` | JSON Array | Item-Templates |
| `tile_types.json` | JSON Array | Tile-Templates |
| `recipes.json` | JSON Array | Crafting-Rezepte |
| `schedules.json` | JSON Array | NPC-Tagespläne |
| `dialogues.json` | JSON Object | Dialog-Linien per Template-ID |
| `factions.json` | JSON Object | Fraktionsdefinitionen und Beziehungen |
| `quests.json` | JSON Array | Authored Quest-Definitionen |
| `biomes.json` | JSON Object | Biom-Definitionen für Wildnis-Generation |
| `player.json` | JSON Object | Spieler-Startwerte und Aktionen |
| `travel_encounters.json` | JSON Array | Reise-Begegnungs-Templates |
| `world_events.json` | JSON Array | Chronik-Eventpool (Off-Screen-Ereignisse) |
| `names.json` | JSON Object | Vornamen-Pool für Townsfolk (SocialService) |
| `scenarios/*.json` | JSON Object | Szenario-Dateien pro Siedlung |
| `prefabs/*.json` | JSON Object | Vordefinierte Raum-Layouts |

### 3.1.2 ID-Namenskonventionen

- **Einzigartigkeit:** Alle IDs müssen global eindeutig sein.
- **Format:** `snake_case`. Keine Leerzeichen. (Ausnahme: Location-IDs dürfen
  PascalCase sein, müssen aber `world.json` entsprechen.)
- **Beispiele:** Entity `orc`/`villager`; Item `iron_sword`/`health_potion`;
  Tile `floor_stone`/`station_forge`; Recipe `smelt_iron_ingot`; Schedule
  `villager_routine`; Location `Village`/`Eastmoor`; Quest `taste_of_home`.

### 3.1.3 Referenz-Regeln

- **Entity-Templates** → `schedule_id`→ScheduleRegistry, `faction`→Factions
- **Items** → keine externen Referenzen (`slot` muss zu `SlotType` passen)
- **Recipes** → `station`→`STATION_TILES`, `inputs`/`output`→ItemRegistry
- **Scenarios** → NPC `type`→EntityRegistry, `station`→`STATION_TILES`,
  `resources[].kind`→`RESOURCE_NODES`, `biome`→biomes.json
- **Quests** → `giver_location`→WorldLocation.id, `target.item`→ItemRegistry,
  `target.template`→EntityRegistry, `target.location`→WorldLocation.id,
  `prerequisites`→Quest.id
- **Dialogues** → Top-Level-Key→EntityTemplate.id (oder `_default`, `_gossip*`)
- **Biomes** → `base`/`patches`/`features`→TileRegistry, `spawns`→EntityRegistry,
  `resources`→`RESOURCE_NODES`-Keys
- **World.json** → `routes[].between`→Location.id, `friends`→Location.id,
  `scenario`→Szenario-Dateiname (ohne `.json`); POI-`monsters`→EntityRegistry,
  `cache`→ItemRegistry, `resources`→`RESOURCE_NODES`-Keys

### 3.1.4 Hardcoded Constraints (zwingend)

1. **Entity `alignment`:** Nur `hostile`, `neutral`, `friendly`.
2. **Entity `default_state`:** Nur `idle`, `wander`, `chase`, `talk`, `work`,
   `patrol`, `socialize`, `sleep`.
3. **Entity `sprite_layer`:** `GROUND`, `DECOR_BOTTOM`, `TRAPS`, `ITEMS`,
   `CORPSES`, `ENTITIES`, `DECOR_TOP`, `EFFECTS`.
4. **Item `slot`:** Falls vorhanden: `head`, `body`, `main_hand`, `off_hand`,
   `feet`, `accessory`.
5. **Item `material`:** Freier String (Anzeige/Description).
6. **Tile `crafting_station`:** Falls gesetzt: `forge`, `anvil`, `mill`, `oven`,
   `tannery`, `herbalist`, `jeweler`, `loom`, `sawmill`, `kitchen`.
7. **Recipe `station`:** Muss in `STATION_TILES` existieren.
8. **Schedule `activity`:** `WORK`, `PATROL`, `SOCIALIZE`, `SLEEP`, `IDLE`,
   `WANDER`.
9. **Farben:** RGB-Tupel `[R, G, B]`, Integer 0-255.
10. **Loot Tables:** `[["template_id", chance], ...]`, chance Float 0.0-1.0.
11. **Zahlenwerte:** `hp`, `max_hp`, `power`, `defense`, `mana`, `max_mana`,
    `perception`, `intelligence` sind Integers.
12. **Coordinate Arrays:** Positionen immer `[x, y]` Integer-Arrays.

### 3.1.5 Zahlen-Constraints (Code-Stand, `config/game.py`)

| Parameter | Wert | Beschreibung |
|-----------|------|--------------|
| `TICKS_PER_HOUR` | 60 | 60 Ticks = 1 Spielstunde |
| `COMBAT_MIN_DAMAGE` | 1 | Minimaler Schaden pro Treffer |
| `COMBAT_DAMAGE_VARIANCE` | 0.2 | +/- 20% Variation |
| `COMBAT_CRIT_CHANCE` | 0.1 | 10% Krit-Chance |
| `COMBAT_CRIT_MULTIPLIER` | 2 | x2 Schaden bei Krit |
| `BLEED_DAMAGE_PER_TURN` | 1 | HP-Verlust pro Blutungsrunde |
| `BLEED_TURNS` | 3 | Blutungsdauer in Runden |
| `COMBAT_XP_PER_KILL_BASE` | 10 | Flat-Combat-XP pro Kill (+ max HP des Gegners) |
| `GOSSIP_CHANCE` | 0.3 | Chance pro berechtigtem Zug |
| `GOSSIP_COOLDOWN_TICKS` | 8 | Mindestabstand zwischen Snippets |
| `GOSSIP_HEAR_RADIUS` | 6 | Spieler-Hörweite in Tiles |
| `GOSSIP_PAIR_RADIUS` | 2 | NPC-Abstand für "im Gespräch" |
| `GOSSIP_TOPICAL_CHANCE` | 0.5 | Chronik-Event vs. generisches Gerede |
| `AI_LOITER_RADIUS` | 3 | Loiter-Radius um den Anker |
| `AI_LOITER_MOVE_CHANCE` | 0.5 | Schrittwahrscheinlichkeit beim Loitern |
| `WILDERNESS_SIZE` | 40 | Kantenlänge generierter Wildnis-Maps |
| `GATHER_XP_PER_HARVEST` | 12 | Sammel-Skill-XP pro Ernte |
| `SKILL_BASE_XP` / `SKILL_XP_GROWTH` / `SKILL_MAX_LEVEL` | 100 / 1.4 / 10 | Skill-XP-Kurve |
| `FACTION_TRUSTED` / `FACTION_HOSTILE` | 50 / -50 | Fraktions-Standing-Schwellen |
| `CRAFT_QUALITY_SWING` / `CRAFT_QUANTITY_LEVELS_PER_BONUS` | 1.5 / 3 | Crafting-Qualität/-Menge |

---

# 4. Content Creation Guide (Templates & Workflows)

## 4.1 Entity-Template JSON

**Datei:** `assets/data/entities.json` (JSON-Array)

### 4.1.1 Vollständiges Entity-Template-Schema

```json
{
  "id": "string (snake_case, unique)",
  "name": "string",
  "sprite": "string (1-char ASCII)",
  "color": [R, G, B],
  "sprite_layer": "ENTITIES",
  "hp": int, "max_hp": int, "power": int, "defense": int,
  "mana": int, "max_mana": int, "perception": int, "intelligence": int,
  "ai": bool (default: true),
  "blocker": bool (default: true),
  "default_state": "idle|wander|chase|talk|work|patrol|socialize|sleep" (default: "wander"),
  "alignment": "hostile|neutral|friendly" (default: "hostile"),
  "description": "string (optional)",
  "wounded_text": "string (optional)",
  "wounded_threshold": float (default: 0.5),
  "loot_table": [["item_template_id", chance], ...] (optional),
  "schedule_id": "schedule_template_id" (optional),
  "home_pos": [x, y] (optional),
  "merchant": {"stock": ["item_template_id", ...], "gold": int} (optional),
  "needs": {"hunger_rate": float, "eat_threshold": float, "eat_duration_ticks": int} (optional),
  "quest_giver": bool (default: false),
  "animal": bool (default: false),
  "innkeeper": bool (default: false),
  "faction": "faction_id" (optional)
}
```

### 4.1.2 Beispiel (Monster)

```json
{
  "id": "goblin", "name": "Goblin", "sprite": "g", "color": [50, 200, 50],
  "sprite_layer": "ENTITIES",
  "hp": 6, "max_hp": 6, "power": 3, "defense": 0,
  "mana": 0, "max_mana": 0, "perception": 6, "intelligence": 3,
  "ai": true, "default_state": "wander", "alignment": "hostile", "blocker": true,
  "description": "A small, nasty goblin",
  "loot_table": [["dagger", 0.6], ["health_potion", 0.5]],
  "faction": "monsters"
}
```

### 4.1.3 Beispiel (NPC mit voller Simulation)

```json
{
  "id": "blacksmith", "name": "Blacksmith", "sprite": "B", "color": [150, 150, 150],
  "sprite_layer": "ENTITIES",
  "hp": 15, "max_hp": 15, "power": 4, "defense": 2,
  "mana": 0, "max_mana": 0, "perception": 5, "intelligence": 6,
  "ai": true, "default_state": "wander", "alignment": "neutral", "blocker": true,
  "description": "A burly blacksmith",
  "schedule_id": "blacksmith_routine", "home_pos": [8, 8],
  "needs": {"hunger_rate": 3.0, "eat_threshold": 70.0, "eat_duration_ticks": 30},
  "merchant": {"stock": ["dagger", "iron_sword", "iron_ingot"], "gold": 250},
  "faction": "townsfolk"
}
```

> `Hidden`, `Skirmisher`, `ResourceNode`, `LightSource`, `PatrolRoute` werden
> **nicht** im Entity-Template gesetzt, sondern von Szenarien/Services vergeben.

## 4.2 Item-Template JSON

**Datei:** `assets/data/items.json` (JSON-Array)

```json
{
  "id": "string (snake_case, unique)",
  "name": "string",
  "sprite": "string (1-char ASCII)",
  "color": [R, G, B],
  "sprite_layer": "ITEMS",
  "weight": float (kg),
  "material": "string",
  "description": "string (optional)",
  "slot": "head|body|main_hand|off_hand|feet|accessory" (optional),
  "stats": {"hp": int, "power": int, "defense": int, "mana": int, "perception": int, "intelligence": int} (optional),
  "consumable": {"effect_type": "heal_hp|heal_mana", "amount": int, "consumed_on_use": bool} (optional),
  "value": int (Gold, default: 0)
}
```

> **Verteilungsregel:** `tests/verify_item_distribution.py` verlangt, dass
> **jedes** Item erreichbar ist (in einem Merchant-`stock` oder einer
> `loot_table`). Neue Items also immer einem Händler-Sortiment oder einer
> Loot-Tabelle hinzufügen.

### 4.2.1 Beispiel (Waffe)

```json
{
  "id": "iron_sword", "name": "Iron Sword", "sprite": "/", "color": [200, 200, 200],
  "sprite_layer": "ITEMS", "weight": 2.5, "material": "iron",
  "description": "A simple but sturdy iron sword.",
  "slot": "main_hand", "stats": {"power": 5}, "value": 30
}
```

### 4.2.2 Beispiel (Consumable)

```json
{
  "id": "health_potion", "name": "Health Potion", "sprite": "!", "color": [255, 0, 0],
  "sprite_layer": "ITEMS", "weight": 0.5, "material": "glass",
  "description": "A red liquid that restores health.",
  "consumable": {"effect_type": "heal_hp", "amount": 10}, "value": 15
}
```

## 4.3 Tile-Template JSON

**Datei:** `assets/data/tile_types.json` (JSON-Array)

```json
{
  "id": "string (snake_case, unique)",
  "name": "string",
  "base_description": "string (optional)",
  "walkable": bool,
  "transparent": bool,
  "sprites": {"GROUND": "char", "DECOR_TOP": "char"},
  "color": [R, G, B],
  "bg_color": [R, G, B] (optional),
  "occludes_below": bool (default: false),
  "roof": bool (default: false),
  "provides_rest": bool (default: false),
  "crafting_station": "station_type" (default: "")
}
```

### 4.3.1 Beispiel (Crafting Station)

```json
{
  "id": "station_forge", "name": "Smelting Forge",
  "base_description": "A roaring forge with a crucible. You could smelt ore into ingots here.",
  "walkable": false, "transparent": true, "crafting_station": "forge",
  "sprites": {"GROUND": "♨"}, "color": [230, 130, 60], "bg_color": [52, 28, 20]
}
```

## 4.4 Recipe-Template JSON

**Datei:** `assets/data/recipes.json` (JSON-Array)

```json
{
  "id": "string (snake_case, unique)",
  "station": "forge|anvil|mill|oven|tannery|herbalist|jeweler|loom|sawmill|kitchen",
  "inputs": {"item_template_id": count, ...},
  "output": "item_template_id",
  "output_qty": int (default: 1),
  "ticks": int (default: 30)
}
```

> **Lieferketten-Trennung (geguardet von `tests/verify_crafting.py`):** Die
> `forge` nimmt nur Erz-Inputs (plus `coal` für die Stahlkette); der `anvil`
> nur Barren-Inputs. Beispiele unten.

### 4.4.1 Beispiele

```json
{ "id": "smelt_iron_ingot",  "station": "forge", "inputs": {"iron_ore": 2}, "output": "iron_ingot", "ticks": 20 }
{ "id": "smelt_steel_ingot", "station": "forge", "inputs": {"iron_ore": 2, "coal": 1}, "output": "steel_ingot" }
{ "id": "smith_steel_sword", "station": "anvil", "inputs": {"steel_ingot": 2}, "output": "steel_sword" }
```

## 4.5 Schedule-Template JSON

**Datei:** `assets/data/schedules.json` (JSON-Array)

```json
{
  "id": "string (snake_case, unique)",
  "name": "string",
  "entries": [
    {
      "start": int (0-23),
      "end": int (0-23),
      "activity": "WORK|PATROL|SOCIALIZE|SLEEP|IDLE|WANDER",
      "target_pos": [x, y] (optional),
      "target_meta": "home|hearth|work" (optional),
      "target_pool": [[x, y], ...] (optional, für WORK/SOCIALIZE-Verteilung),
      "route": [[x, y], ...] (optional, nur für PATROL — Fallback)
    }
  ]
}
```

**`target_meta`-Auflösung:**
- `"home"` → der authored `home_pos`/zugewiesene Schlafplatz
- `"hearth"` → `Residence.hearth_pos` (echtes Lagerfeuer/Taverne der Siedlung)
- `"work"` → `Residence.work_pos` (Arbeitsanker aus Szenario-`work_anchors`)

`work` und `route`/`patrol_route` greifen auf den schedule-eigenen
`target_pool`/`route` zurück, falls das Szenario keine Anker authored.

### 4.5.1 Beispiel

```json
{
  "id": "villager_routine", "name": "Standard Villager Day",
  "entries": [
    {"start": 0,  "end": 7,  "activity": "SLEEP",     "target_meta": "home"},
    {"start": 7,  "end": 12, "activity": "WORK",      "target_meta": "work"},
    {"start": 12, "end": 13, "activity": "SOCIALIZE", "target_meta": "hearth"},
    {"start": 13, "end": 19, "activity": "WORK",      "target_meta": "work"},
    {"start": 19, "end": 22, "activity": "SOCIALIZE", "target_meta": "hearth"},
    {"start": 22, "end": 24, "activity": "SLEEP",     "target_meta": "home"}
  ]
}
```

## 4.6 Dialogue JSON

**Datei:** `assets/data/dialogues.json` (JSON-Object, Keys = EntityTemplate-IDs)

**Legacy-Format:** `{"template_id": ["Line 1", "Line 2", ...]}`

**Konditionales Format:**

```json
{
  "template_id": {
    "default": ["Line 1"],
    "conditional": [{"when": {"key": "value"}, "lines": ["Line 3"]}]
  }
}
```

**Konditionale Keys für `when`:** `rep` (`beloved`/`notorious`), `phase`
(`night`/`day`), `activity` (`WORK`/`SOCIALIZE`/...), `prosperity`
(`struggling`/`thriving`), `guards` (`hostile`/`trusted`), `quest`
(`ready`/`active`).

**Spezielle Keys:** `_default` (Fallback), `_gossip` (`{subject}`-Platzhalter),
`_gossip_friend`, `_gossip_rival`, `innkeeper`.

## 4.7 Faction JSON

**Datei:** `assets/data/factions.json` (JSON-Object)

```json
{
  "factions": {
    "faction_id": {
      "name": "string",
      "player_start": int (default: 0),
      "relations": {"other_faction_id": "ally|enemy"}
    }
  }
}
```

### 4.7.1 Beispiel

```json
{
  "factions": {
    "bandits": {
      "name": "Bandits", "player_start": -100,
      "relations": {"townsfolk": "enemy", "town_guard": "enemy", "monsters": "enemy"}
    }
  }
}
```

> Die Matrix sollte symmetrisch gepflegt werden (bandits↔monsters sind
> beidseitig `enemy`). Nicht aufgeführte Paare gelten als `neutral`.

## 4.8 Quest JSON

**Datei:** `assets/data/quests.json` (JSON-Array)

```json
{
  "id": "string (snake_case, unique)",
  "title": "string",
  "description": "string",
  "quest_type": "deliver|kill|visit",
  "giver_location": "location_id",
  "target": {"item": "item_template_id", "count": int},   // deliver
  "target": {"template": "entity_template_id", "count": int}, // kill
  "target": {"location": "location_id"},                  // visit
  "reward_gold": int,
  "prerequisites": ["quest_id", ...] (optional)
}
```

> **Quest-Ketten:** Eine Quest mit `prerequisites` bleibt verborgen, bis alle
> gelisteten Quests `turned_in` sind. **Guide-Quests** (generiert, nicht
> authored) trennen `offer_location` (wo angeboten) von `giver_location` (wo
> abgegeben / das Ziel) — das Annehmen entdeckt das Ziel.

### 4.8.1 Beispiel

```json
{
  "id": "lifeline_larder", "title": "Empty Larders",
  "description": "Bring 3 loaves of bread from the Village.",
  "quest_type": "deliver", "giver_location": "Brackenfen",
  "target": {"item": "bread", "count": 3}, "reward_gold": 45
}
```

## 4.9 Biome JSON

**Datei:** `assets/data/biomes.json` (JSON-Object)

```json
{
  "biome_id": {
    "name": "string",
    "base": "tile_type_id",
    "patches": [["tile_type_id", chance], ...] (optional),
    "features": [["tile_type_id", chance], ...],
    "big_trees": int,
    "spawns": [["entity_template_id", count], ...],
    "resources": [["resource_node_kind", count], ...]
  }
}
```

### 4.9.1 Resource Node Kinds (hardcoded in `gather_service.RESOURCE_NODES`)

| Kind | Item | Skill | Glyph | Color | Name | Respawn |
|------|------|-------|-------|-------|------|---------|
| `herb_patch` | `herbs` | foraging | ♣ | (90,180,110) | Herb Patch | 240 |
| `iron_vein` | `iron_ore` | mining | ▲ | (150,130,110) | Iron Vein | 480 |
| `silver_vein` | `silver_ore` | mining | ▲ | (205,205,225) | Silver Vein | 600 |
| `grain_field` | `grain` | farming | ≈ | (210,190,90) | Grain Field | 360 |
| `timber_stand` | `log` | woodworking | ♠ | (110,150,80) | Timber Stand | 420 |
| `fishing_spot` | `raw_fish` | foraging | ≋ | (90,160,210) | Fishing Spot | 300 |
| `pasture` | `wool` | farming | Ψ | (225,225,215) | Sheep Pasture | 300 |
| `salt_pan` | `salt` | foraging | ░ | (235,235,240) | Salt Pan | 360 |
| `gem_vein` | `gemstone` | mining | ◊ | (120,200,230) | Gem Vein | 720 |
| `coal_seam` | `coal` | mining | ▓ | (70,70,75) | Coal Seam | 480 |

### 4.9.2 Beispiel

```json
{
  "forest": {
    "name": "Forest", "base": "floor_grass",
    "patches": [["floor_dirt", 0.12]],
    "features": [["tree", 0.09], ["tree_sapling", 0.04]],
    "big_trees": 6,
    "spawns": [["deer", 4], ["boar", 2], ["wolf", 2]],
    "resources": [["herb_patch", 8], ["timber_stand", 5], ["coal_seam", 2]]
  }
}
```

## 4.10 Travel Encounter JSON

**Datei:** `assets/data/travel_encounters.json` (JSON-Array)

```json
{
  "id": "string (snake_case, unique)",
  "weight": int,
  "message": "string ({destination} wird ersetzt)",
  "spawns": [
    {
      "template": "entity_template_id",
      "count": int,
      "placement": "mid_road|near_player",
      "skirmish_side": "string" (optional)
    }
  ]
}
```

## 4.11 World Events JSON

**Datei:** `assets/data/world_events.json` (JSON-Array) — der Chronik-Eventpool
für Off-Screen-Ereignisse (`WorldSimulationService`/`WorldChronicleService`).

```json
{
  "id": "string (snake_case, unique)",
  "weight": int,         // 0 = nur über Eskalation erreichbar
  "text": "string (Chronik-Zeile)",
  "effects": {           // optional
    "stock_delta": {"item_id": number, ...},
    "prosperity_delta": number
  },
  "escalation": {        // optional: löst Folgeevent aus
    "event_id": "other_event_id",
    "delay_hours": int
  }
}
```

## 4.12 Player JSON

**Datei:** `assets/data/player.json` (JSON-Object)

```json
{
  "name": "string", "sprite": "string (1-char)", "color": [R, G, B],
  "sprite_layer": "ENTITIES",
  "hp": int, "max_hp": int, "power": int, "defense": int,
  "mana": int, "max_mana": int, "perception": int, "intelligence": int,
  "max_carry_weight": float,
  "actions": [
    {
      "name": "string",
      "cost_mana": int (default: 0),
      "cost_arrows": int (default: 0),
      "range": int (default: 0),
      "requires_targeting": bool (default: false),
      "targeting_mode": "auto|manual|inspect" (default: "auto"),
      "power_multiplier": float (default: 1.0)
    }
  ],
  "gold": int
}
```

---

## 4.13 Workflow: Neue Siedlung (Location) hinzufügen

Der komplexeste Workflow — eine neue Siedlung erfordert **2 Pflicht-Dateien**
(Szenario + Weltgraph-Eintrag) und optional Dialoge/Quests.

### Schritt 1: Szenario-Datei `assets/data/scenarios/<settlement_id>.json`

```json
{
  "id": "SettlementId",
  "dimensions": {"width": int, "height": int},
  "arrival_pos": [x, y],
  "base_layer": "tile_type_id",
  "terrain_variety": {"chance": float, "choices": ["tile_type_id", ...]} (optional),
  "structures": [
    {
      "id": "GlobalUniqueStructureId",
      "v_pos": [x, y], "v_size": [w, h], "h_size": [w, h],
      "floors": int (>= 1),
      "beds": int (optional, Überschreibung der Bettenzahl),
      "npcs": [
        {"type": "entity_template_id", "pos": [x, y],
         "merchant": {"stock": [...], "gold": int} (optional)}
      ],
      "style": "home|tavern|shop",
      "station": "forge|anvil|..." (optional, Station im Inneren)
    }
  ],
  "village_npcs": [
    {"type": "entity_template_id", "pos": [x, y], "merchant": {...} (optional)}
  ],
  "economy": {
    "stock": {"item_id": count, ...},
    "rates_per_day": {
      "item_id": float,                                                   // +Produktion / -Verbrauch
      "item_id": {"per_day": float, "requires": {"input_item_id": count}} // verarbeitete Güter
    }
  } (optional),
  "biome": "biome_id" (optional, aktiviert Wildnis-Map via Portal),
  "stations":  [{"type": "forge|...", "pos": [x, y]}] (optional, lose Stationen),
  "shelters":  [{"station": "forge|...", "pos": [x, y], "size": [w, h]}] (optional, offene Werkstätten mit Dach),
  "resources": [{"kind": "resource_node_kind", "pos": [x, y]}] (optional),
  "work_anchors":  [[x, y], ...] (optional, Tages-Arbeitsplätze für die Crowd),
  "patrol_route":  [[x, y], ...] (optional, echter Wachweg dieser Siedlung),
  "lights":    [{"type": "torch|lantern|campfire", "pos": [x, y]}] (optional)
}
```

**Wichtige Constraints:**

1. **Structure-IDs müssen GLOBAL eindeutig sein** — nicht nur im Szenario.
2. `v_pos`/`v_size` = Overlay auf der Dorfkarte; `h_size` = tatsächliche
   Innengrösse.
3. `arrival_pos` muss auf einem begehbaren Tile liegen.
4. NPC-Positionen in `structures[].npcs` sind relativ zum Innenraum
   (0,0 .. h_size); in `village_npcs` relativ zur Dorfkarte (0,0 .. dimensions).
5. `biome` muss in `biomes.json` existieren.
6. `station` (in einer Struktur), `stations` (lose) und `shelters` (überdachte
   Werkstatt mit Cutaway-Rendering) sind drei Wege, eine Crafting-Station zu
   platzieren.
7. `work_anchors` werden von `HousingService` an Common-Folk als
   `Residence.work_pos` verteilt; `patrol_route` an Wachen als
   `Residence.patrol_route`. Schedules mit `target_meta: "work"` bzw. einem
   PATROL-Eintrag nutzen sie.
8. `resources[].kind` muss ein `RESOURCE_NODES`-Key sein; `MapGenerator`
   dekoriert den Knoten (Feld/Fels/Teich) und hält die vier orthogonalen
   Nachbarn frei (bump-erreichbar).

### Schritt 2: Weltgraph `assets/data/world.json`

Location-Eintrag:

```json
{
  "id": "SettlementId", "name": "Anzeigename",
  "type": "settlement",
  "scenario": "settlement_id",
  "discovered": false,
  "map_pos": [x, y],
  "friends": ["AndereSettlementId", ...]
}
```

Route-Eintrag (bidirektional):

```json
{"between": ["SettlementId", "AnderesSettlementId"], "travel_ticks": int}
```

**Constraints:** `travel_ticks` > 0; `scenario` = Dateiname ohne `.json`;
`friends`/`between` referenzieren existierende Location-IDs; `friends` müssen
route-verbunden sein (sonst kann keine Guide-Quest dorthin zeigen).

> **POI-Knoten** verwenden `"type": "poi"` und thematisieren den Dungeon über
> `"monsters": [entity_id, ...]` (Spawn-Pool), `"cache": [item_id, ...]`
> (versteckter Fund) und — für Minen — `"resources": [node_kind, ...]`. POIs
> haben keine Szenario-Datei; `MapGenerator` generiert den Dungeon.

### Schritt 3 & 4 (optional)

- Dialoge für neue NPC-Template-IDs in `dialogues.json`.
- Quests, die in der neuen Siedlung beginnen/enden, in `quests.json`.

### Vollständiges Szenario-Beispiel (Ausschnitt)

```json
{
  "id": "Foxhollow",
  "dimensions": {"width": 45, "height": 45},
  "arrival_pos": [22, 42],
  "base_layer": "floor_grass",
  "structures": [
    {"id": "Foxhollow Weaving Hall", "v_pos": [28, 12], "v_size": [8, 7],
     "h_size": [12, 10], "floors": 2, "station": "loom",
     "npcs": [{"type": "weaver", "pos": [6, 5]}], "style": "shop"}
  ],
  "village_npcs": [
    {"type": "guard", "pos": [22, 40]},
    {"type": "mayor", "pos": [20, 20]}
  ],
  "economy": {
    "stock": {"wool": 8, "cloth": 4, "bread": 6},
    "rates_per_day": {"cloth": {"per_day": 2, "requires": {"wool": 2}}, "bread": -1.5}
  },
  "biome": "plains",
  "resources": [{"kind": "pasture", "pos": [38, 30]}],
  "work_anchors": [[20, 18], [30, 22], [12, 28]],
  "patrol_route": [[6, 6], [40, 6], [40, 40], [6, 40]],
  "lights": [{"type": "campfire", "pos": [22, 22]}]
}
```

## 4.14 Workflow: Neues Item

1. Eintrag in `items.json` (4.2).
2. Falls craftbar: Rezept in `recipes.json` (4.4).
3. **Pflicht:** Item in mindestens einen Merchant-`stock` oder eine
   `loot_table` aufnehmen (Erreichbarkeits-Guard).

## 4.15 Workflow: Neues Entity-Template

1. Eintrag in `entities.json` (4.1).
2. Optional: Dialoge (`dialogues.json`, Key = Entity `id`).
3. Optional: Schedule (`schedules.json`) + `schedule_id` im Template.
4. Optional: Fraktion zuweisen (muss in `factions.json` existieren).

## 4.16 Workflow: Neues Biom

1. Eintrag in `biomes.json` (4.9).
2. Alle referenzierten Tile-/Entity-IDs müssen existieren.
3. `resources`-Kinds müssen in `RESOURCE_NODES` (`gather_service.py`) existieren.

---

# Anhang A: Sprite-Layer-Referenz

| Layer | Enum-Name | Wert | Verwendung |
|-------|-----------|------|------------|
| Ground | GROUND | 0 | Terrain, Boden |
| Decor Bottom | DECOR_BOTTOM | 1 | Niedrige Dekoration |
| Traps | TRAPS | 2 | Fallen |
| Items | ITEMS | 3 | Gegenstände auf dem Boden |
| Corpses | CORPSES | 4 | Leichen |
| Entities | ENTITIES | 5 | Lebende Wesen, NPCs, Monster |
| Decor Top | DECOR_TOP | 6 | Hohe Dekoration (Baumkronen) |
| Effects | EFFECTS | 7 | Partikel, Projektile |

# Anhang B: Content-Pipeline

```
assets/data/
  entities.json    -> EntityRegistry    -> EntityFactory.create()
  items.json       -> ItemRegistry      -> ItemFactory.create()
  tile_types.json  -> TileRegistry      -> Tile.set_type()
  recipes.json     -> RecipeRegistry    -> CraftingService.craft()
  schedules.json   -> ScheduleRegistry  -> ScheduleSystem.process()
  dialogues.json   -> DialogueService   -> dialogue_service.get_line()
  factions.json    -> FactionService    -> Disposition/Alignment
  quests.json      -> QuestService      -> Quest Lifecycle
  biomes.json      -> (direkt)          -> MapGenerator.create_wilderness()
  player.json      -> (direkt)          -> Player Entity Setup
  world_events.json-> (direkt)          -> WorldSimulation/Chronicle
  names.json       -> (direkt)          -> SocialService
  travel_encounters.json -> (direkt)    -> TravelEncounterService
  world.json       -> WorldGraphService -> Locations, Routes, POIs
  scenarios/*.json -> MapGenerator      -> Settlement maps
  prefabs/*.json   -> MapGenerator      -> Prefab stamping
```

---

**ENDE DER DOKUMENTATION**
