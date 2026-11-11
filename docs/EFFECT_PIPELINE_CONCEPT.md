# Effekt-Pipeline — ein Ausführer statt vier Schalter

> **Stand:** November 2026 · **STATUS: VORSCHLAG** — noch nichts davon ist umgesetzt.
>
> **Befund-Basis:** Review des Stands `1ad693f` (536 grüne Tests, 90 % Coverage).
> Die tragenden Annahmen sind mit einem Wegwerf-Prototyp gegen den echten Code
> geprüft (Abschnitt 9).
>
> **Einordnung:** Architekturregeln stehen in `CLAUDE.md`, die Richtung in
> `ROADMAP.md`. Dieses Dokument begründet einen Entwurf. Die übrigen Befunde des
> Reviews sind als Issues erfasst; der Tracker ist [#100].

---

## 1. Kurzfassung & Empfehlung

**Ein gemeinsames, datengetriebenes Effektmodell — eingeführt in fünf einzeln
mergebaren Phasen, ohne Save-Bruch und ohne Balance-Änderung.**

Alles, was im Spiel „etwas mit einer Entity macht", läuft heute über vier
getrennte, fest verdrahtete Stellen: Angriffe, Fähigkeiten, Verbrauchsgüter und
Statuseffekte. Jede kennt genau die Fälle, die jemand hineingeschrieben hat.
Deshalb kostet ein neues Item eine JSON-Zeile, eine neue *Wirkung* aber einen
Umbau an mehreren Stellen.

| Baustein | Aufgabe |
|---|---|
| `EffectSpec` | Datensatz „was soll passieren": Art + Parameter. Kommt aus JSON, liegt in Komponenten, wird ohne Sonderfall gespeichert. |
| `EffectService` | Der eine Ausführer: Liste von Specs + Quelle + Ziel hinein, Ergebnis heraus. |
| Handler-Tabelle | Eine Funktion pro Effekt-Art (`damage`, `heal`, `restore_mana`, `apply_status`, `remove_status`). |
| `statuses.json` + `StatusEffects` | Statuseffekte als Daten: Dauer, Stapelregel, Tick-Effekte, Stat-Modifikatoren. |
| `abilities.json` | Fähigkeiten als Daten: Ziel, Kosten, Effektliste. |

Danach gilt: **Neue Kombination = JSON. Neue Effekt-Art = ein Handler, eine
Tabellenzeile, ein Test.**

Das ist der größte Hebel für die Tiefe des Spiels, weil fast alle offenen
Punkte daran hängen: Gegnerfähigkeiten, Statusvielfalt, Nahrung mit Wirkung,
Rast, Munition, Fallen (Abschnitt 8).

---

## 2. Befund: vier Schalter, sechs Folgen

### 2.1 Die vier Stellen

| Stelle | Heute | Fest verdrahtet |
|---|---|---|
| Angriff | `AttackIntent` → `CombatSystem.process()` (`combat_system.py:36-121`) | Formel, Krit → `Bleeding`, Log-Texte, FCT |
| Fähigkeit | `Action` → `ActionSystem` (`action_system.py:84-121`, `238-337`) | Verteilung über `action.name == "Wait"`; einzige Wirkung ist `power_multiplier` |
| Verbrauchsgut | `Consumable` → `ConsumableService.use_item()` (`consumable_service.py:32-62`) | `if/elif` über `effect_type`, zwei Fälle |
| Statuseffekt | `Bleeding` → `StatusEffectSystem.process()` (`status_effect_system.py:22-40`) | genau ein Status, als eigene Komponentenklasse |

### 2.2 Was daraus folgt

Alle sechs Punkte sind am laufenden Spiel nachgeprüft, nicht nur gelesen.

1. **Ein Tippfehler frisst Items.** `use_item` hat nach dem `if/elif` keinen
   Fehlerfall. Ein unbekannter `effect_type` (etwa `heal_hpp`) gibt `True`
   zurück und löscht das Item ohne Wirkung.
2. **Wer verblutet, zählt nicht.** `StatusEffectSystem` meldet `ENTITY_DIED`
   ohne Angreifer (`status_effect_system.py:40`). Ein Wolf, der nach einem
   kritischen Treffer des Spielers verblutet, gibt 0 Kampf-XP und 0
   Quest-Fortschritt; derselbe Kill direkt gibt 17 XP und zählt ([#105]).
3. **12 von 13 Verbrauchsgütern sind „heile N HP".** Brot, Verband und
   Heiltrank unterscheiden sich nur in einer Zahl, und alle melden „You drink
   the …" (`consumable_service.py:46`). Die Kochkette über drei Werkstätten hat
   mechanisch nichts zu erzählen.
4. **Gegner können nur zuschlagen.** NPCs erzeugen ausschließlich
   `AttackIntent`. Alle acht feindlichen Vorlagen haben Mana 0 und kein
   einziges eigenes Merkmal außer Zahlenwerten.
5. **Der Spieler hat eine aktive Fähigkeit.** Mehr als „Schaden × Faktor" kann
   `Action` nicht ausdrücken: kein Selbst-Buff, keine Heilung, kein Status.
6. **Tote Felder.** `cost_arrows` wird angezeigt (`ui_system.py:273`), aber nie
   verbraucht; `SpriteLayer.TRAPS` hat keinen Nutzer.

---

## 3. Leitentscheidungen

**L1 — Effekte sind Daten, die Ausführung ist zentral.**
Vier Stellen, die HP schreiben, Log-Zeilen bauen und den Tod melden, werden zu
einer. Systeme entscheiden nur noch, *wann* Effekte ausgelöst werden.

**L2 — Vorlagen in Registries, Instanzen als Kopie.**
`statuses.json` und `abilities.json` sind Flyweight-Vorlagen wie Tiles, Items
und Schedules. In Komponenten liegt eine Kopie der Effektliste — genau wie
`Stats` und `StatModifiers` heute aus der Vorlage kopiert werden. Das hält alte
Spielstände lesbar und lässt die 21 Stellen in sieben Testdateien unberührt,
die `Action(...)` direkt konstruieren.

**L3 — Verhalten hängt an IDs und Enums, nie an Anzeigenamen.**
`EffectKind` ist ein `str`-Enum wie `GameEvent`. Ein Guard-Test nach dem Muster
von `verify_events.py` stellt sicher, dass jede Art genau einen Handler und ein
Parameter-Schema hat. Ein Tippfehler im JSON scheitert beim Laden mit
Fundstelle statt still im Spiel.

**L4 — Eine Status-Komponente mit Liste, keine Klasse pro Status.**
Eine Komponentenklasse je Status (`Bleeding`, `Poisoned`, `Stunned`) wäre
ECS-typisch, aber wieder ein geschlossener Schalter: neue Klasse, neuer
Systemcode, neue Zeile in der Aufräumliste des `DeathSystem`.

**L5 — Keine Entity-IDs in gespeicherten Effektdaten.**
`freeze()`/`thaw()` vergeben neue IDs (`map_container.py:105-139`). Ein Status
merkt sich deshalb nicht, *wer* ihn verursacht hat, sondern nur, *ob es der
Spieler war* (`by_player`). Mehr brauchen die heutigen Abnehmer nicht; sobald
es stabile IDs gibt ([#107]), kann daraus eine echte Referenz werden.

**L6 — Befehle nach unten, Fakten nach oben.**
Der Ausführer wird direkt aufgerufen, weil der Aufrufer das Ergebnis braucht
(„wurde das Item benutzt?"). Er meldet Fakten wie bisher als Event
(`ENTITY_DIED`). Ein Event-getriebener Ausführer scheidet aus: esper ruft
Handler in undefinierter Reihenfolge auf ([#101]), und Events liefern nichts
zurück.

**L7 — Ein Seed, feste Würfelreihenfolge.**
Der Ausführer bekommt einen aus dem Weltseed abgeleiteten RNG. Die Reihenfolge
der Würfe (erst Varianz, dann Krit) ist tragend und wird von einem Golden-Test
festgehalten — dieselbe Idee wie die Terrain-Fingerabdrücke in
`verify_world_seed.py`.

**L8 — Die Kampfformel wird austauschbar, aber nicht ausgetauscht.**
Die Minderung durch Rüstung wandert in eine reine Funktion. Ob sie Subtraktion
bleibt, entscheidet [#116] — nicht diese Migration.

---

## 4. Zielbild

### 4.1 Datenmodell (`game/components.py`)

```python
class EffectKind(str, Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    RESTORE_MANA = "restore_mana"
    APPLY_STATUS = "apply_status"
    REMOVE_STATUS = "remove_status"


@dataclass
class EffectSpec:
    """One thing an effect list does. Plain data, parsed and validated at load."""

    kind: EffectKind
    params: dict[str, float | int | str | bool] = field(default_factory=dict)
    chance: float = 1.0  # rolled once per application
    applies_to: str = "target"  # "target" | "source" (e.g. lifesteal heals the source)


@dataclass
class ActiveStatus:
    status_id: str  # template id in statuses.json
    turns_left: int
    stacks: int = 1
    potency: float = 1.0
    by_player: bool = False  # attribution that survives freeze/thaw (L5)


@dataclass
class StatusEffects:
    """Every status currently on an entity."""

    active: list[ActiveStatus] = field(default_factory=list)
```

Bestehende Komponenten werden nur erweitert:

| Komponente | Neu | Bleibt als Altlast lesbar |
|---|---|---|
| `Consumable` | `effects: list[EffectSpec]`, `verb: str = "use"` | `effect_type`, `amount` |
| `Action` | `id: str = ""`, `effects: list[EffectSpec]` | `power_multiplier` |
| `AttackIntent` (flüchtig) | `effects: list[EffectSpec] \| None`, `origin: str` | — |
| `Bleeding` | — | ganze Klasse, bis zum nächsten Save-Versionssprung |

Die Parameter sind bewusst ein flaches Dict statt fester Felder: Eine neue
Effekt-Art bringt eigene Parameter mit, ohne dass `EffectSpec` wächst. Die
Typsicherheit kommt aus dem Schema (4.4), nicht aus dem Dataclass.

### 4.2 Daten

**Verbrauchsgut** (`items.json`) — vorher und nachher:

```json
"consumable": {"effect_type": "heal_hp", "amount": 12}
```

```json
"consumable": {
  "verb": "eat",
  "effects": [
    {"type": "heal", "amount": 12},
    {"type": "apply_status", "status": "well_fed"}
  ]
}
```

**Statuseffekt** (`statuses.json`, neu):

```json
[
  {
    "id": "bleeding",
    "name": "Bleeding",
    "duration": 3,
    "stacking": "refresh",
    "tags": ["wound"],
    "on_tick": [{"type": "damage", "amount": 1, "mitigation": "none"}],
    "messages": {"tick": "{target} bleeds for {amount} damage."},
    "color": [200, 40, 40]
  },
  {
    "id": "well_fed",
    "name": "Well Fed",
    "duration": 240,
    "stacking": "refresh",
    "modifiers": {"defense": 1},
    "messages": {"apply": "{target} feels well fed.", "expire": "{target} is hungry again."}
  }
]
```

| Feld | Bedeutung |
|---|---|
| `duration` | Runden (1 Runde = 1 Tick = 1 Spielminute) |
| `stacking` | `refresh` (Dauer zurücksetzen — das heutige Verhalten von `Bleeding`), `stack` (bis `max_stacks`), `ignore` |
| `tags` | Gruppen für `remove_status`: ein Verband entfernt alles mit `wound` |
| `modifiers` | Stat-Änderung pro Stapel, solange der Status aktiv ist |
| `on_apply` / `on_tick` / `on_expire` | Effektlisten |

**Fähigkeit** (`abilities.json`, neu):

```json
[
  {
    "id": "basic_attack",
    "name": "Attack",
    "effects": [
      {"type": "damage", "scale_stat": "power", "variance": true, "can_crit": true, "crit_status": "bleeding"}
    ]
  },
  {
    "id": "power_strike",
    "name": "Power Strike",
    "cost_mana": 8,
    "range": 1,
    "requires_targeting": true,
    "targeting_mode": "auto",
    "effects": [
      {"type": "damage", "scale_stat": "power", "scale": 2.0, "variance": true, "can_crit": true, "crit_status": "bleeding"}
    ]
  },
  {
    "id": "second_wind",
    "name": "Second Wind",
    "cost_mana": 12,
    "effects": [{"type": "heal", "amount": 8}]
  }
]
```

`player.json` verweist dann nur noch per ID:
`"abilities": ["investigate", "power_strike"]`. Eine Fähigkeit ohne
`requires_targeting` wirkt auf den Anwender selbst.

### 4.3 Der Ausführer (`game/services/effects/`)

```python
class EffectService:
    def apply(self, effects, *, source, target, origin, potency=1.0, by_player=None) -> EffectReport: ...
    def can_apply(self, effects, *, source, target) -> bool: ...
```

Ablauf pro Spec, immer in dieser Reihenfolge:

1. **Empfänger bestimmen** (`applies_to`); ohne `Stats` wird der Effekt
   übersprungen — dieselbe Regel wie heute im `CombatSystem`.
2. **Chance würfeln** — nur wenn `chance < 1.0`, damit Effekte ohne Chance den
   RNG nicht bewegen.
3. **Handler ausführen**; er schreibt den Zustand und gibt ein `EffectOutcome`
   zurück (`applied`, `amount`, `crit`, `lethal`).
4. **Rückmeldung** an genau einer Stelle (`feedback.py`): Log-Zeile und FCT.
5. **Tod melden**, falls `lethal`: `ENTITY_DIED(ziel, angreifer)`. Angreifer ist
   die Quelle, sonst der Spieler, wenn `by_player` gesetzt ist.

`can_apply` ist der Trockenlauf dazu. Er trägt die heutige Regel „bei vollem
Leben wird der Trank nicht verbraucht" und dient später der KI zur Auswahl
einer Fähigkeit.

Die Stufen eines Schadenseffekts, so wie `CombatSystem` sie heute rechnet:

```
Basis        Wurf         Minderung      Krit         Anwenden      Folgen
amount     → ±20 %      → − Defense    → × 2        → Stats.hp    → Status bei Krit
+ Stat × k   (1. Wurf)    mind. 1        (2. Wurf)    aufwecken     Tod melden
```

Basis und Minderung liegen als reine Funktionen in `combat_math.py`. Das ist
die eine Stelle, an der [#116] später ansetzt.

### 4.4 Handler und Schema

```python
# game/services/effects/handlers.py
def heal(ctx: EffectContext, spec: EffectSpec) -> EffectOutcome:
    stats = ctx.world.component_for_entity(ctx.target, Stats)
    eff = ctx.world.try_component(ctx.target, EffectiveStats)
    current = eff or stats
    amount = min(round(spec.params["amount"] * ctx.potency), current.max_hp - current.hp)
    if amount <= 0:
        return EffectOutcome(applied=False)
    stats.hp += amount
    if eff is not None:
        eff.hp += amount
    return EffectOutcome(applied=True, amount=amount)


HANDLERS: dict[EffectKind, Handler] = {
    EffectKind.DAMAGE: Handler(damage),
    EffectKind.HEAL: Handler(heal, usable=has_missing_hp),
    EffectKind.RESTORE_MANA: Handler(restore_mana, usable=has_missing_mana),
    EffectKind.APPLY_STATUS: Handler(apply_status),
    EffectKind.REMOVE_STATUS: Handler(remove_status, usable=has_matching_status),
}
```

Was im JSON stehen *darf*, liegt getrennt vom Verhalten in
`game/content/effect_schema.py` (Art → Parametername → Typ, Pflicht oder
Standardwert). `parse_effects()` dort wird vom `ResourceLoader` benutzt. So
bleibt der Content-Layer frei von Regelcode, und es entsteht kein Importzyklus.

Parameter der ersten fünf Arten:

| Art | Parameter |
|---|---|
| `damage` | `amount`, `scale_stat`, `scale`, `variance`, `mitigation` (`defense` \| `none`), `can_crit`, `crit_status` |
| `heal` / `restore_mana` | `amount` |
| `apply_status` | `status`, optional `duration` |
| `remove_status` | `status` oder `tag` |

### 4.5 Statuseffekte im Ablauf

- **Tick** wie heute: `StatusEffectSystem.process()` läuft zuerst in der
  Gegnerphase, einmal pro Runde, für Spieler und NPCs. Pro aktivem Status:
  `on_tick` ausführen, Dauer senken, bei 0 `on_expire` ausführen und entfernen.
- **Stat-Modifikatoren** fließen dort ein, wo heute die Ausrüstung einfließt:
  `EquipmentSystem` summiert Ausrüstung und Status zu `EffectiveStats`. Erlaubt
  sind zunächst `power`, `defense`, `perception`, `intelligence`. `hp` und
  `mana` bleiben draußen, damit ein auslaufender Buff niemanden unter 0
  drückt. Eine gemeinsame Feldliste für die Stats ([#109]) macht daraus wenige
  Zeilen.
- **Zeit ohne Runden** lässt Status ablaufen, ohne zu ticken. Das betrifft
  eingefrorene Karten (ein Wolf blutet nicht Tage später weiter) und Reisen
  (ein 4-Stunden-Buff überlebt keine 12-Stunden-Reise). Beides hat denselben
  Haken in `MapTransitionService`, der die verstrichenen Ticks schon kennt.
- **Rast** läuft über `advance_turns` und tickt damit von allein.
- **Tod**: `StatusEffects` ersetzt `Bleeding` in der Aufräumliste des
  `DeathSystem`.

### 4.6 Wer was ändert

| Datei | Änderung | Phase |
|---|---|---|
| `game/components.py` | neue Typen aus 4.1; `Consumable`/`Action` erweitert | E1–E3 |
| `game/content/effect_schema.py` (neu) | Parameter-Schema, `parse_effects()` | E1 |
| `game/content/status_registry.py`, `ability_registry.py` (neu) | Vorlagen, eingehängt in `ContentDatabase` | E2, E3 |
| `game/content/resource_loader.py` | lädt und validiert Effektlisten und die beiden neuen Dateien | E1–E3 |
| `game/services/effects/` (neu) | `effect_service.py`, `handlers.py`, `statuses.py`, `combat_math.py`, `feedback.py` | E1–E3 |
| `game/services/consumable_service.py` | nur noch: Effekte holen, ausführen, Item verbrauchen | E1 |
| `game/systems/status_effect_system.py` | generischer Tick über `StatusEffects` | E2 |
| `game/systems/equipment_system.py` | Status-Modifikatoren in `EffectiveStats` | E2 |
| `game/systems/death_system.py` | Aufräumliste | E2 |
| `game/services/map_transition_service.py` | Status-Ablauf beim Auftauen und Reisen | E2 |
| `game/systems/combat_system.py` | löst `AttackIntent` über den Ausführer auf | E3 |
| `action_system.py`, `player_action_service.py`, `input_controller.py` | Verteilung über `Action.id`; Selbst-Fähigkeiten | E3 |
| `bootstrap.py`, `game_context.py`, `system_initializer.py` | `ctx.effects` als Pflichtfeld, Seed, Verdrahtung | E1 |
| `CLAUDE.md`, `docs/CONTENT_GUIDE.md` | Rezepte, Schemas, Komponententabelle | jede Phase |

### 4.7 Speichern

`save_serialization` arbeitet über die Typannotationen der Dataclasses. Die
neuen Typen brauchen dort keinen Sonderfall (Abschnitt 9).

Alte Spielstände bleiben ohne Versionssprung ladbar:

- Ein gespeichertes `Consumable` ohne `effects` wird über **eine**
  Übersetzungsfunktion gelesen (`heal_hp` → `heal`). Dasselbe für eine `Action`
  ohne `effects`: Sie gilt als Schaden mit `power_multiplier`.
- Ein gespeichertes `Bleeding` wird beim ersten Tick in einen `ActiveStatus`
  umgewandelt. Es lebt höchstens drei Runden.
- Die Altlasten fallen mit dem nächsten bewussten Save-Versionssprung weg
  ([#110]).

---

## 5. Migrationsplan (jede Phase einzeln mergebar)

**Eiserne Regel jeder Phase:** Tests bleiben grün, das Spiel bleibt startbar,
ein Commit pro Task. Bis einschließlich E4 ändert sich **kein Zahlenwert** im
Kampf.

### Phase E0 — Sicherheitsnetz *(0,5 Sessions, Risiko: keins)*
- Golden-Test `tests/verify_combat_golden.py`: eine feste Folge von Treffern mit
  festem Seed gegen die Wertepaare aus `entities.json`; erwartet werden exakte
  HP, Krit-Positionen und die RNG-Position danach.
- Charakterisierungstests für Verbrauchsgüter: Heilung klemmt am Maximum, volles
  Leben verbraucht nichts, Mana-Trank.
- **Akzeptanz:** Suite grün; die Zahlen, an denen E3 gemessen wird, sind
  eingecheckt.

### Phase E1 — Kern und Verbrauchsgüter *(1–2 Sessions, Risiko: niedrig)* ⬅ erster sichtbarer Nutzen
- `EffectKind`, `EffectSpec`, Schema, `EffectService` mit `heal` und
  `restore_mana`; `ctx.effects`.
- Alle 13 Verbrauchsgüter in `items.json` auf `effects` + `verb` umstellen. Der
  Loader lehnt unbekannte Arten und Parameter mit Fundstelle ab.
- `ConsumableService` ruft den Ausführer. Item-Nutzung läuft über
  `PlayerActionService.use_item()`; das Fenster ruft nur noch auf ([#112]).
- Guard-Tests aus Abschnitt 6.
- **Sichtbar:** „You eat the Loaf of Bread." statt „You drink …" ([#104]). Ein
  Tippfehler scheitert beim Start, statt Items zu fressen.
- **Akzeptanz:** Keine Abfrage von `effect_type` mehr außer in der
  Übersetzungsfunktion. Ein Spielstand von vorher lädt, und seine Tränke wirken.

### Phase E2 — Statuseffekte *(1–2 Sessions, Risiko: mittel)*
- `statuses.json`, `StatusRegistry`, `StatusEffects`, `apply_status`,
  `remove_status`, generischer Tick.
- Der Krit im `CombatSystem` ruft `apply_status("bleeding")` statt eine
  `Bleeding`-Komponente anzuhängen. Die Formel bleibt noch, wo sie ist.
- `by_player`: Wer am Treffer des Spielers verblutet, zählt ([#105]).
- Status-Modifikatoren in `EffectiveStats`; Ablauf beim Auftauen und Reisen.
- `verify_combat_depth.py` auf `StatusEffects` umstellen; `BLEED_*` wandert aus
  `config/game.py` in die Daten.
- Zwei neue Inhalte als Beweis, reines JSON: `well_fed` am Eintopf, und der
  Verband entfernt `wound`.
- **Akzeptanz:** Ein neuer Status entsteht ohne Python-Änderung. Verbluten gibt
  XP und Quest-Fortschritt. Ein Spielstand mit blutender Entity lädt.

### Phase E3 — Angriffe und Fähigkeiten *(1–2 Sessions, Risiko: mittel)*
- `damage`-Handler und `combat_math.py`; `CombatSystem` löst `AttackIntent` über
  den Ausführer auf. Der Golden-Test aus E0 bleibt **unverändert** grün.
- `abilities.json`, `AbilityRegistry`; `player.json` verweist per ID; Power
  Strike ist Daten.
- Die Namensschalter in `ActionSystem.perform_action`, `InputController` und
  `PlayerActionService` weichen IDs.
- Eine Selbst-Fähigkeit als Beweis (`second_wind`).
- `wake_up` wird eine freie Funktion. Damit entfallen die Durchreichung von
  `action_system` und die zweite Implementierung im `InteractionResolver`.
- RNG aus `derive_seed(world_seed, "effects")`.
- **Akzeptanz:** `CombatSystem` enthält keine Formel und keinen Statusnamen. Kein
  `action.name ==` im Produktivcode.

### Phase E4 — Auslöser an Items und Gegnern *(1 Session, Risiko: niedrig)*
- Waffen bekommen `on_hit` (ein Dolch lässt mit 20 % bluten).
- Entity-Vorlagen bekommen `attack` (der Wolfsbiss blutet, das Skelett nicht).
- **Akzeptanz:** Zwei Gegner mit unterschiedlichen Angriffen, nur durch JSON.

### Phase E5 — Ausbau *(eigene Arbeitspakete, siehe Abschnitt 8)*
Flächenziele, Munition als Kosten, Verhaltens-Flags wie Betäubung, Fallen,
Quest-Belohnungen als Effekte.

---

## 6. Tests

| Datei | Prüft |
|---|---|
| `verify_combat_golden.py` | Zahlengleichheit des Kampfs über die ganze Migration |
| `verify_effects.py` | Ausführer und Handler: Klemmen, Chance, `applies_to`, Trockenlauf, Reihenfolge der Würfe |
| `verify_statuses.py` | Anwenden, Auffrischen, Stapeln, Ablauf, Modifikatoren, Zuordnung, freeze/thaw und Save-Roundtrip |
| `verify_effect_content.py` | Guard über die Daten (siehe unten) |

Der Daten-Guard, nach dem Muster von `verify_events.py` und
`verify_item_distribution.py`:

- `EffectKind`, Handler-Tabelle und Schema haben dieselben Mitglieder.
- Jede Effektliste in `items.json`, `abilities.json`, `statuses.json` und
  `entities.json` lässt sich parsen.
- Jeder referenzierte Status existiert; kein Status wendet sich selbst an.
- Jedes Verbrauchsgut hat mindestens einen Effekt.

---

## 7. Was bewusst NICHT gemacht wird

| Idee | Warum nicht |
|---|---|
| Formeln als Strings im JSON (`"amount": "power * 2 + level"`) | Nicht typprüfbar, nicht testbar, eine zweite Sprache im Projekt. Parameter plus Handler reichen. |
| Modifikator-Stapel mit Abfängern („Schild halbiert eingehenden Schaden") | Erst wenn ein Inhalt ihn braucht. Zahlen-Buffs laufen über `EffectiveStats`. |
| Eine Komponentenklasse pro Status | Siehe L4. |
| Ausführer über Events (`damage_requested`) | Siehe L6. |
| Balance-Änderungen während E0–E4 | Der Golden-Test soll genau das verhindern. Balance ist [#116]. |
| KI-Umbau | Eigenes Thema ([#113], [#115]). Die Pipeline liefert nur die Bausteine. |

---

## 8. Was das freischaltet

| Thema | Wie die Pipeline es trägt | Issue |
|---|---|---|
| Gegnerfähigkeiten und -rollen | Fähigkeiten und Angriffe sind Daten; `can_apply` dient der Auswahl | [#115] |
| Reaktion auf Angriffe | Der Ausführer ist die eine Stelle, die ein Faktum `ENTITY_DAMAGED` melden kann | [#113] |
| Rüstungsformel | `combat_math.mitigate()` ist eine Funktion | [#116] |
| Kampf-Skill mit Wirkung | zusätzlicher Skalierungsfaktor im `damage`-Handler | [#117] |
| Rast, die heilt | Schlafen wendet einen Status mit Heilung pro Runde an | [#118] |
| Nahrung mit Charakter | Buffs und `remove_status` statt zwölf Heilzahlen | — |
| Munition | Kosten einer Fähigkeit; `cost_arrows` bekommt einen Nutzer | — |
| Fallen | ein Auslöser „Feld betreten" mit Effektliste; `SpriteLayer.TRAPS` existiert schon | — |
| Quest-Belohnungen | Belohnung als Effektliste (Gold, Item, Ruf) | [#114] |

---

## 9. Nachweis aus dem Prototyp

Geprüft mit einem Wegwerf-Skript gegen den echten Code (nicht im Repository):

- **Speichern.** `StatusEffects`, ein `Consumable` mit Effektliste und eine
  `ActionList` mit Effekten gehen über echtes JSON verlustfrei durch
  `save_serialization` — einschließlich Enum und Parameter-Dict, ohne Änderung
  am Serializer. Ein altes `Consumable` ohne `effects` dekodiert mit leerer
  Liste.
- **Zahlengleichheit.** 20 000 Zufallstreffer (Power und Defense 0–20, HP 1–40,
  Multiplikator 1–2,5, mit und ohne `EffectiveStats`) durch den heutigen
  `CombatSystem` und durch einen `damage`-Handler mit demselben RNG: identische
  HP, Krits, Tode und RNG-Position, keine Abweichung.
- **Blutung.** Die Tick-Folge eines Status mit `on_tick: damage 1` ist
  identisch zur heutigen `Bleeding`-Komponente.

---

## 10. Offene Entscheidungen

| Entscheidung | Optionen | Tendenz |
|---|---|---|
| Form von `EffectSpec` | flaches `params`-Dict mit Schema / feste Felder | Dict — offen für neue Arten, Typprüfung beim Laden |
| Effekte am Item | Kopie in der Komponente / Nachschlagen in der Vorlage per `TemplateId` | Kopie — erlaubt später Tränke unterschiedlicher Stärke; Preis: Balance-Patches erreichen alte Spielstände nicht |
| Blutung und Rüstung | ignoriert Defense (heute) / wird gemindert | heute beibehalten, in den Daten über `mitigation` wählbar |
| Krit-Status | global / pro Angriff | pro Angriff (`crit_status`), ab E4 pro Waffe |
| Status-Ablauf ohne Runden | still entfernen / `on_expire` ausführen | still entfernen |
| `AttackIntent` umbenennen | `EffectIntent` / Name behalten | behalten; 13 Dateien für einen Namen umzuschreiben lohnt nicht |

---

## Anhang: die zwei Rezepte, die in `CLAUDE.md` landen

**Neuer Statuseffekt (kein Code)**

1. Eintrag in `assets/data/statuses.json`.
2. Irgendwo anwenden: `{"type": "apply_status", "status": "<id>"}` an einem
   Item, einer Fähigkeit oder einem Angriff.
3. `python -m pytest tests/verify_effect_content.py`.

**Neue Effekt-Art**

1. Mitglied in `EffectKind`.
2. Parameter in `game/content/effect_schema.py`.
3. Handler-Funktion und eine Zeile in `HANDLERS`.
4. Testfall in `tests/verify_effects.py`.
5. Mindestens ein Inhalt, der die Art benutzt — eine Art ohne Nutzer ist ein
   toter Draht.

[#100]: https://github.com/Pappet/rogue_like_rpg/issues/100
[#101]: https://github.com/Pappet/rogue_like_rpg/issues/101
[#104]: https://github.com/Pappet/rogue_like_rpg/issues/104
[#105]: https://github.com/Pappet/rogue_like_rpg/issues/105
[#107]: https://github.com/Pappet/rogue_like_rpg/issues/107
[#109]: https://github.com/Pappet/rogue_like_rpg/issues/109
[#110]: https://github.com/Pappet/rogue_like_rpg/issues/110
[#112]: https://github.com/Pappet/rogue_like_rpg/issues/112
[#113]: https://github.com/Pappet/rogue_like_rpg/issues/113
[#114]: https://github.com/Pappet/rogue_like_rpg/issues/114
[#115]: https://github.com/Pappet/rogue_like_rpg/issues/115
[#116]: https://github.com/Pappet/rogue_like_rpg/issues/116
[#117]: https://github.com/Pappet/rogue_like_rpg/issues/117
[#118]: https://github.com/Pappet/rogue_like_rpg/issues/118
