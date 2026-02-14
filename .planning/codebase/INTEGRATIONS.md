# External Integrations

**Analysis Date:** 2026-02-14

## APIs & External Services

**No External APIs:**
- This is a single-player, standalone game with no network connectivity
- No API calls to external services detected
- No SDK integrations for third-party services

## Data Storage

**Databases:**
- Not used - Game data exists entirely in memory

**File Storage:**
- Local filesystem only - Not currently used for game saves
- Asset loading: Not implemented (game uses procedural generation and hardcoded sprites as ASCII characters)

**Caching:**
- None - No caching layer implemented
- ECS entities stored in Esper's in-memory database only

## Authentication & Identity

**Auth Provider:**
- Not applicable - Single-player game with no user system

**Identity Management:**
- Not applicable - No user accounts or authentication needed

## Monitoring & Observability

**Error Tracking:**
- Not implemented - No error tracking service

**Logs:**
- Console output only via `pygame` and standard output
- Message log system for in-game events: `ui/message_log.py`
  - Rich text parsing with color tags: `[color=red]text[/color]`
  - Stored messages: 100 max (configurable)
  - Rendered to game UI layer

**Debugging:**
- Print statements used throughout for development debugging
- Frame rate tracking: 60 FPS target via `pygame.time.Clock()`

## CI/CD & Deployment

**Hosting:**
- Standalone desktop application (local machine)
- No server/cloud deployment

**CI Pipeline:**
- None detected - No automated testing or build pipeline

**Build/Distribution:**
- Direct Python execution - `python main.py`
- Could be packaged with PyInstaller (not currently implemented)

## Environment Configuration

**Required Packages:**
- pygame - Graphics rendering framework
- esper - ECS framework

**Installation:**
- Via pip: `pip install pygame esper`
- No requirements.txt file present (manual dependency management)

**Secrets Location:**
- Not applicable - No authentication or secrets in this application

## Webhooks & Callbacks

**Incoming:**
- Not applicable - No network services

**Outgoing:**
- Not applicable - No external service calls

## Inter-Process Communication

**Game State Communication:**
- Event passing via Pygame event queue: `pygame.event.get()` in `main.py:46`
- System-to-system coordination via ECS components and events
- State persistence via `persist` dictionary passed between game states: `game_states.py:24-32`

## Asset Management

**Sprites/Graphics:**
- Procedural generation using ASCII characters
- No external asset loading
- Sprite library: Single characters and symbols (e.g., `@` for player, `#` for walls, `.` for ground)
- Color system: RGB tuples, hardcoded palette in `ui/message_log.py:5-24`

## Testing Infrastructure

**Test Execution:**
- Manual verification scripts in `tests/` directory
- No automated test framework integration (unittest used but not integrated with CI)
- Tests are standalone Python scripts

---

*Integration audit: 2026-02-14*
