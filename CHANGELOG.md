# Changelog

All notable changes to texastoast are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] — 2026-08-24

The game structure release. 0.4.0 made the *hardware* buildable without
hardware; 0.5.0 makes the *game* buildable without flag soup. Until now every
example hand-rolled its modal state — the template kept `paused` and
`showing_dialogue` globals, early-returned from `update()` while either was
set, and dispatched keys down an if-chain. This release ships the systems
that subsume the pattern: scenes, entity groups, and player seats, plus
audio, theming, and the camera break committed in 0.4.0's deprecation.

### Added

- **Scene stack** (`texastoast.scene`). Modality as a stack instead of flags:
  **pushing a scene freezes the scenes below by construction**, so `paused`
  simply stops existing. A scene is anything with `update(dt)` and
  `render()` — no base class, per the house rule; lifecycle hooks
  (`on_enter`/`on_exit`/`on_pause`/`on_resume`), `handle_key`, and the
  `update_below`/`render_below` overlay flags are optional and detected by
  presence. All stack operations are deferred to the next frame — one rule,
  which is what lets a scene pop itself mid-update, and lands a key-event
  push before that frame renders. The stack imports nothing, never binds
  anything, and is wired by the game: `game.set_update(stack.update)`.
  `examples/game_template.py` is rewritten as the reference — its flag soup
  and dispatch chain are gone.
- **EntityGroup** (`texastoast.world.group`). Nothing iterated entities
  before; every game hand-rolled the loop. The group drives `update(dt)`,
  defers add/remove so mutation mid-pass cannot skip a neighbor (the classic
  first bug of every entity system), indexes tags *in the group* so
  duck-typed members never grow attributes, and offers `sorted_by_y()` (feet
  line — painter's order is by baseline) for caller-driven rendering. The
  group never draws. Entities can die in their own `update()` via
  `alive = False`; deliberately absent: spatial hashing, z-layers,
  group-owned rendering — systems, not policy.
- **Audio** (`texastoast.audio`), because the engine had none. `Mixer` with
  `load`/`play`/`play_music`/`stop_music`/`stop_all`/`set_master_volume`,
  over a backend chain that degrades exactly like `I2CBus`: pygame-ce (the
  new `audio` extra — chosen over alternatives because SDL2 wheels are
  first-class on the Pi *and* the same dependency serves the planned pygame
  rendering backend, one dep for two releases) → the platform's basic player
  (`winsound`/`aplay`/`afplay`, honestly SFX-grade) → a null backend where
  every call is a silent no-op. A game with no audio device runs identically.
  **WAV is the guaranteed format** on every tier; a missing asset logs and
  plays as silence, because a Pi image missing one file must not kill the
  game. pygame is imported only inside its backend — never at import time.
- **Player seats** (`texastoast.input.players`). `PlayerManager` assigns
  input sources to seats: join is edge-triggered (a *fresh* A/Start press —
  holding the button through the join screen claims one seat, not one per
  frame), the keyboard is claimable like any controller, and hotplug rides
  the duck-typed `connected` attribute. A disconnected seat polls **idle**,
  never the buttons held at the moment of unplug — the same rationale as
  `MagmaHubInput`'s reset — and a returning controller **reclaims the same
  seat**, re-firing `on_join`: a bounced cable must not reshuffle who is P1.
  (No separate `on_rejoin`; two callbacks instead of four, trade noted.)
  `examples/two_player_demo.py` demonstrates join/leave/rejoin with a
  simulated hub — zero hardware, per the 0.4.0 promise.
- **Theme** (`texastoast.ui.theme`). The widget palette was frozen as
  literals scattered across three files; `Theme` states it once, and
  `DEFAULT_THEME` carries exactly the old values — pinned by a regression
  test, so a default-themed game renders identically. Frozen dataclass;
  variants via `dataclasses.replace`. Layout metrics stay out: layout is not
  theme.
- **magmascript factories**: `scenes`, `entities`, `sprite_sheet`, `theme`,
  `mixer`, `players`; UI factories take a `"theme"` option.

### Changed

- **Widget style kwargs now default from the theme** (identical values).
  Explicit kwargs still win, including `add_stat(color=...)`.
- **`Entity` gained `alive = True`** — one line, consumed by `EntityGroup`.

### Breaking

- **`Camera.follow()` requires `dt`.** Deprecated with a warning through
  0.4.x, an error now: the no-`dt` path applied smoothing per frame, so the
  camera converged twice as fast at 60 fps as at 30. `dt` stays *last* in
  the signature, so correct 0.4.x call sites — keyword and full-positional —
  work unchanged; only the calls that were already warning now raise, with
  the fix spelled out in the error message.

## [0.4.0] — 2026-08-24

The hardware dev-kit release. The premise: **you should not need the hardware
to build for the hardware.** Everything the I2C layer does — the protocol
handshake, hub polling, input adapters — now runs against a simulator, gets
watched by a live test bench, and records/replays as regression files. Plus
the first seam toward a non-tkinter rendering backend.

### Added

- **Hub simulator** (`texastoast.i2c.sim`). `SimBus` implements the smbus2
  surface, injected via the new `I2CBus(backend=...)` parameter — so a
  simulated bus is a *real* bus to every caller, and every test of it
  exercises the actual `MagmaHub` protocol code. Faked at the bus level, not
  the hub level, deliberately: a hub-level fake could never catch a protocol
  regression (the 0.3.0 `connected` bug would have sailed through one). The
  sim is strict about the firmware handshake — a block read with no preceding
  select-write raises, exactly as the Pico refuses it. Includes error
  injection (`fail_next_reads`), latency simulation (`set_read_delay`),
  hotplug (`disconnect_hub`), `simulated_hub()` one-line wiring, and
  `KeyboardHubDriver` (the keyboard as a simulated controller).
- **Controller test bench** — `texastoast-bench`, the package's first console
  script. Live button/joystick display, raw protocol bytes, connection
  status, poll-latency stats and read-error rates per hub; simulator mode
  (automatic when no hub answers, or `--sim`) and `--record`. It lives in
  `texastoast/devtools/`, not `tools/`, because `tools/` ships only in the
  sdist and the Pi that needs the bench installed from a wheel.
- **Input recording & replay** (`texastoast.input.recording`). `.ttrec` is
  delta-encoded JSON Lines of *protocol button bitmasks* — that one choice
  lets a single recording replay through the engine (`ReplayInput`, an
  `InputSource` with a wall clock or a deterministic manual clock) *and*
  through the full hardware stack (`SimBus.play_recording` feeds the raw
  bytes back in). A session recorded against real firmware becomes a
  regression test that runs anywhere.
- **Background polling** (`texastoast.i2c.poller`). `HubPoller` polls on a
  daemon thread and duck-types the hub's read surface, so `MagmaHubInput`
  works unchanged and `poll()` never blocks a frame on a loose wire. The
  handoff is an atomic swap of an immutable snapshot — no locks on the hot
  path. `scan_buses_async` does discovery off-thread. One poller per hub *or*
  direct polling, never both.
- **`MagmaHub.stats`** — `HubStats` with poll/error counts and rolling
  latency min/avg/max/jitter, for the bench and for any game that wants a
  connection-quality indicator.
- **Renderer protocols** (`texastoast.render.abstract`). `Renderer`
  (world-space) and `UISurface` (screen-space, group-scoped) capture what the
  engine asks of a drawing backend; `CanvasRenderer` satisfies both
  structurally. `present()` is a documented no-op on tkinter — it exists now
  because a buffered SDL/framebuffer backend cannot retrofit it later without
  touching every game's render function. UI portraits/images through the
  surface and theming are deliberately deferred.
- **magmascript hardware factories** — `hub`, `hubs`, `sim_hub` (the SimBus
  rides along as `h.sim`), `hub_input`, `composite`, `poller`, `recorder`,
  `replay`; see `examples/sim_input.mgs`.

### Changed

- **UI widgets take the renderer** (any `UISurface`) in place of a bare
  canvas, and inherit its dimensions — ending the width/height being passed
  by hand to every widget separately. The bare-canvas form still works
  unchanged.
- **`MagmaHub.scan_buses()` probes only the candidate addresses** (four
  reads) instead of sweeping 0x03–0x77 — 117 blocking reads had no place on a
  game's startup path. `I2CBus.scan()` remains for diagnostics;
  `I2CBus.probe(addr)` is the new single-address check.
- **`MagmaHub.poll()` returns a fresh snapshot list** each poll instead of
  mutating in place, so a threaded reader can never observe a half-updated
  poll. Treat the returned list as read-only.

### Deprecated

- **`Camera.follow()` without `dt`** now warns; 0.5.0 will require it. The
  no-`dt` path converges twice as fast at 60 fps as at 30 — flipping the
  default silently would change every game's camera feel, so it warns for one
  release instead.

## [0.3.0] — 2026-08-24

A second correctness pass, over the parts 0.2.0 did not reach — the UI widgets
and the camera — plus a scripting surface for
[magmascript](https://github.com/magmacrunchmedia/magmascript).

### Breaking

- **`DialogueBox` and `Menu` are drawn by your render loop**, the way `HUD`
  already was. Call `dialogue.update(dt)` from `update()` and
  `dialogue.render()` / `menu.render()` from `render()`.

  They previously drew themselves once from `show()`, and `DialogueBox` drove
  its typewriter from its own `canvas.after()` timer. Any game whose renderer
  clears the canvas each frame — including both shipped demos — had the box and
  the pause menu wiped off screen while they still reported `active`, so input
  stayed captured and the game looked frozen behind an invisible modal.

  `DialogueBox._tick_type`, `_draw_box`, `_render_text` and `_cancel_pending`
  are gone, along with the second timing source: the typewriter no longer runs
  after the game loop stops, and it advances by `dt` rather than wall clock.
  `Menu._draw()` is now `Menu.render()`.

- **`KeyboardInput.poll()` and `MagmaHubInput.poll()` return a copy**, not the
  live `InputState`. Keeping the previous frame's state to detect a fresh
  button press silently could not work before, because every poll handed back
  the same object. Code that mutated the returned state to inject input needs
  to set the source's state instead.

### Fixed

- **Camera easing was frame-rate dependent.** `Camera.follow()` applied
  `smoothing` once per frame, so the camera converged twice as fast at 60 fps
  as at 30 — the same bug `Entity.move()` was fixed for in 0.2.0. `follow()`
  now takes an optional `dt` and treats `smoothing` as a per-frame factor at
  30 fps, converted to a time constant. Omitting `dt` keeps the old behaviour.
- **Keys that share a button released each other.** `Up`, `w` and `W` all map
  to `up`; releasing any one of them cleared the button. Holding `Left` and
  tapping `a` stopped the player. Each button now tracks which keys are down.
- **Hub input stuck when a controller disappeared.** `MagmaHubInput.poll()`
  kept the last state when the hub stopped reporting that controller, leaving
  whatever was held at that moment pressed forever. It now resets to idle.
- **The game loop swallowed exceptions indefinitely.** A broken `update()`
  printed a traceback every frame while the game appeared to run. The loop now
  tolerates `max_consecutive_errors` (default 10) back-to-back failures, then
  stops and re-raises from `Game.start()` — tkinter discards exceptions raised
  inside an `after()` callback, so carrying the error out of the main loop is
  what lets a caller see it at all. One traceback is logged per error streak
  instead of one per frame.
- **Rendering after a quit.** `update()` calling `game.quit()` — a menu's Quit
  item, a win condition — was still followed by `render()` in the same tick,
  drawing onto a destroyed canvas.
- **`HUD.add_stat()` did not clamp `value`** to `max_value`, while `set_stat()`
  did.

### Added

- **magmascript binding.** texastoast publishes itself as the `texastoast`
  domain — or `tt` for short, the same domain under a second name — through a
  `magmascript.domains` entry point, so `.mgs` scripts can drive the engine.
  Neither package depends on the other; installing both is enough. Not named
  `toast`, which magmascript's CLI already uses for clearing caches. See the
  README and `examples/hello.mgs`. Requires magmascript 3.2+.
- `Game(max_consecutive_errors=...)` and `GameLoop(max_consecutive_errors=...,
  on_error=...)`; `GameLoop.error` holds whatever stopped the loop.
- `DialogueBox.displayed` and `TileMap.solid_tiles` properties.
- `tests/test_ui.py` — the `ui` package had no tests at all, which is why the
  dialogue bug survived 0.2.0.

### Changed

- `TileMap(solid_tiles=...)`, `TileMap.from_file()`, `TileMap.save()` and
  `CanvasRenderer.draw_tilemap(skip_tiles=...)` accept any iterable of tile
  ids, not only a `set`. A list is the natural spelling from JSON and from
  languages without a set literal.

## [0.2.0] — 2026-08-24

A correctness release. Several bugs meant the engine did not behave the way its
own README described; fixing the movement one required a breaking API change.

### Breaking

- **`Entity.move()` now takes `dt`**: `move(dx, dy, dt, tilemap=None)`.
  Previously `speed` was applied per *frame*, so `speed=100` moved an entity
  100 px every frame — 3000 px/s at 30 fps — while the docs described it as a
  walking pace. `speed` is now pixels per second and movement is frame-rate
  independent. See [Migrating to 0.2.0](https://github.com/magmacrunchmedia/texastoast/wiki/Migrating-to-0.2.0).
- **`I2CBus.read_byte_data()` and `read_i2c_block_data()` return `None` on
  failure** instead of fabricating `0x00` bytes, so callers can tell a missing
  device from a device reporting zero.
- **`CanvasRenderer.draw_tilemap()` draws tile id 0.** Tiles are now skipped
  when their id has no entry in `tile_colors`, rather than id 0 being skipped
  unconditionally. If you relied on 0 being invisible, omit it from the color
  map or pass `skip_tiles={0}`.

### Fixed

- Diagonal movement was 1.41× faster than movement along one axis; `Entity.move`
  now normalizes the direction vector.
- Entities could pass straight through walls: collision only tested the tile
  under the destination's leading edge, so any step larger than one tile
  tunneled. Movement is now split into sub-steps of at most one tile.
- Blocked movement reverted to the entity's previous position, leaving a gap of
  up to a full tile between it and the wall. Collisions now snap flush.
- `MagmaHub.connected` was `True` after the first poll even with no hardware
  present, so `CompositeInput` latched onto a dead hub and keyboard input
  stopped reaching the game entirely.
- `MagmaHub.poll()` assigned `connected` inside its per-controller loop, so with
  multiple controllers only the last one's result survived.
- `MagmaHub.scan_buses()` leaked the `SMBus` handle for any bus where no hub
  was found.
- Closing the game window with the X button left the loop running with a
  pending `after()` callback; `Game` now handles `WM_DELETE_WINDOW`.
- `GameLoop` scheduled the next frame with the full interval after update and
  render had already run, so each frame cost `interval + work` and the target
  fps was never reached.
- `KeyboardInput.destroy()` passed a binding id where tkinter expects an event
  sequence, so it silently unbound nothing.
- `examples/sprite_demo.py` raised `AttributeError` whenever Pillow was
  installed; it only appeared to work because it fell back to the no-Pillow path.
- `tools/tile_editor.py` saved every non-zero tile id as solid, so maps came
  back with grass, paths, NPCs and signs as walls. Solidity is now a per-tile
  palette flag, and `solid_tiles` from an opened file is preserved.
- The tile editor crashed on maps with ragged rows; short rows are now padded.

### Added

- `Game(root=...)` accepts an existing tkinter root or frame, so a game can be
  embedded in a larger app or driven from tests.
- `Game.on_close()` registers teardown callbacks that run on `quit()`.
- `CanvasRenderer.draw_tilemap(..., skip_tiles=...)` for explicitly transparent
  tile ids.
- `py.typed` marker — the inline annotations are now visible to type checkers.
- CI across Python 3.10–3.13 on Linux and Windows, plus ruff linting.
- Project URLs on the PyPI listing, and a `sprites` extra for Pillow.

## [0.1.3] — 2026-08-23

- Scaled back Magma Hub hardware details in docs and docstrings.

## [0.1.2] — 2026-08-23

- `CompositeInput` None-safety, HUD bar offset, idempotent quit, dead code
  removal, test improvements.

## [0.1.1] — 2026-08-23

- Dialogue prompt, menu crash recovery, loop exception safety, tilemap
  round-trip, sprite bounds check, dt clamping.

## [0.1.0] — 2026-08-23

- Initial release: game loop, canvas renderer, tile maps, collision, camera,
  keyboard input, tile map editor, dialogue/menu/HUD, I2C abstraction.
