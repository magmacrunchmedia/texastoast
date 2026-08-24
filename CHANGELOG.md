# Changelog

All notable changes to texastoast are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — unreleased

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
