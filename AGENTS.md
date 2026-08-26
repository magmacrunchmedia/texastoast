# AGENTS.md — texastoast

Python (3.10+) 2D game engine on tkinter, with an I2C hardware abstraction for
Raspberry Pi "Magma Hub" controllers. Published on PyPI as `texastoast`
(currently 0.5.0). Everything degrades gracefully: no I2C, no display, no audio
backend — the engine still runs on keyboard input. Apache-2.0, hatchling build.

## AI Attribution

**No AI attribution.** Do not append `Co-Authored-By: Claude …`, "Generated with …",
or any similar trailer to commit messages, PR bodies, or release notes. If your
tooling adds such a line by default, remove it before committing.

## Layout

```
texastoast/             the package (ships py.typed)
  core/ render/ world/ input/ ui/ audio/   engine subsystems
  scene.py              SceneStack — modality as a stack, no base class
  i2c/                  bus, MagmaHub, protocol, SimBus simulator (i2c/sim)
  devtools/             ships in the wheel; bench:main is the texastoast-bench script
  mgs.py                magmascript domain (`texastoast` / `tt` entry points)
tests/                  pytest; display-needing tests skip headless, and the
                        terminal-backend tests skip without the [tui] extra
examples/               hello_world.py … game_template.py (the reference wiring),
                        magma_hub_demo.py, *.mgs magmascript demos
tools/                  tile_editor.py (map editor GUI), controller_bench.py
                        (same tool as the installed texastoast-bench)
.github/workflows/      ci.yml (pytest under xvfb + ruff), release.yml (PyPI publish)
pyproject.toml          hatchling; version read from texastoast/__init__.py
```

Extras: `[sprites]` Pillow (sheet cropping), `[hardware]` smbus2 (Linux only),
`[audio]` pygame-ce, `[tui]` textual (terminal backend), `[dev]` pytest + ruff.
None are required to run — `tests/test_no_hard_deps.py` enforces that, and it is
the reason the terminal host is behind a lazy `__getattr__` in `core/__init__.py`.

## Render backends

The terminal is **not a fourth engine** — it is a second output surface for this
one. adenosine is the web engine, magnolia the Wii engine, texastoast the Python
engine; a TUI is a backend under texastoast, and new games get one by targeting
`render/abstract.py` rather than any particular backend.

| | `render/canvas.py` | `render/tui.py` |
|---|---|---|
| host | `core/game.py` (tkinter) | `core/tui_game.py` (Textual) |
| units | pixels | **character cells** |
| `present()` | no-op, canvas is retained | **required** — flushes the buffer |
| `draw_image` | sprite sheets | **no-op**, a grid has no pixels |
| colors | hex strings | the same hex strings, via Rich |

Three seams keep a backend swappable, and are worth preserving:

- `render/cellbuffer.py` is framework-free — no Textual, no Rich, no curses. It
  is the half a hand-written ANSI backend reuses verbatim.
- `core/scheduler.py` names the two methods (`after`/`after_cancel`) that
  `GameLoop` needs. A tkinter root satisfies it structurally, which is why the
  loop worked before the protocol existed. `ManualScheduler` drives the loop in
  tests with no display and no sleeping.
- `TuiGame` takes its surface and scheduler by **injection**, so a new backend
  is a constructor argument rather than a second host class.

A custom ANSI backend is a stated long-term goal; it lands as `render/ansi.py`
plus `core/ansi_game.py` and should require no change to any game.

## Commands

```bash
pip install -e ".[dev,sprites,hardware]"   # dev setup; skip hardware off-Linux
pytest                                     # full suite
pytest tests/test_collision.py -v          # one area
ruff check .                               # CI fails on any finding; --fix to apply
texastoast-bench --sim                     # controller bench, simulator mode
texastoast-bench --record session.ttrec    # capture a session (firmware corpus)
python tools/tile_editor.py                # tile map editor GUI
python examples/game_template.py           # the reference game wiring
```

A green `pytest` on a headless machine is *not* a full pass — renderer/loop/editor
tests skip without a display; CI runs them under xvfb on Linux.

## Conventions

- `speed` and velocities are **pixels per second**; anything per-frame takes `dt`
  explicitly. Do not reintroduce per-frame movement. (`Camera.follow()` requires
  `dt` as of 0.5.0.)
- "Hardware not there" must be distinguishable from valid zero data: return
  `None`, never fabricate a zero buffer. `hub.connected` is True only while reads
  actually succeed.
- Every bug fix gets a regression test that fails against the old behavior, with a
  comment naming what used to go wrong.
- Hardware code paths must be testable with no I2C and no display — test through
  `SimBus` (`texastoast.i2c.sim`), which runs the real bus/hub/protocol code and
  enforces the firmware's select-write handshake. No tests may require a physical
  hub; the Pi checklist in README.md is the manual release gate for `[hardware]`.
- `texastoast/devtools/` may import tkinter only inside functions, never at module
  import time — the package must stay importable headless.
- No base classes: a scene is anything with `update(dt)`/`render()`; entity-group
  membership is anything with `update(dt)`. Optional hooks detected by presence.
- Audio: WAV is the guaranteed format on every backend tier; a missing sound file
  logs a warning and plays silence — an absent asset must not kill the game.
- One `HubPoller` per hub *or* direct `hub.poll()` — never both.
- Ruff: target py310, line-length 100, rules E/F/I/UP/B (E501 ignored;
  `examples/*` may put imports next to use, E402 ignored there).
- magmascript integration (`mgs.py`): constructors take a dict (no kwargs in
  magmascript); unknown keys are errors. The domain registers as both
  `texastoast` and `tt` via entry points; neither package depends on the other.

## Sprite sheets (shared contract — do not change unilaterally)

Uniform grid PNG: frames are frameWidth x frameHeight cells, counted left-to-right
then top-to-bottom. The origin/anchor is stored with the sheet at load time, not
re-derived at call sites. This format is read by all three engines — adenosine (TS),
magnolia (C/Wii), texastoast (Python) — so a sheet exported from SPRITE//FORGE
(adenosine/tools/sprites.html) feeds all of them. Canonical spec:
adenosine/packages/rpg/API.md. Changing the format is a three-repo change.

Here the readers are the sprite support behind the `[sprites]` extra (Pillow does
the cropping) and the `tt.sprite_sheet(path, fw, fh)` magmascript factory.

The terminal backend does not participate: `TuiRenderer.draw_image` is a
documented no-op, because a character grid cannot honor the format. That is a
gap in what a terminal can express, **not** a change to the contract — nothing
in `render/tui.py` reads or writes a sheet.

## Publishing / deploy

Releases go to PyPI via GitHub Actions with PyPI Trusted Publishing — no API
token, no repository secret. The flow (see CONTRIBUTING.md):

1. Update `CHANGELOG.md` — move the unreleased section under the new version.
2. Bump `__version__` in `texastoast/__init__.py` (the single source of truth;
   `pyproject.toml` reads it via `[tool.hatch.version]`).
3. Commit, then `git tag v0.X.Y && git push origin main --tags`.
4. `release.yml` builds sdist + wheel, verifies the tag matches `__version__`,
   publishes with `skip-existing`, and opens a GitHub Release with generated notes.

The sdist also ships `tests/`, `examples/`, and `tools/`; the wheel ships only the
`texastoast` package (including `devtools/`, so `texastoast-bench` installs on the Pi).

## Git

Commit and push as magmacrunchmedia. No AI attribution trailers, ever.

<!-- Update this file in the same commit as any change to build, test, deploy, or layout. -->
