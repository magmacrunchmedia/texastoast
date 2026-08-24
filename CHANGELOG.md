# Changelog

All notable changes to texastoast are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
