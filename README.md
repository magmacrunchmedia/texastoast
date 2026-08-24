# texastoast

[![PyPI](https://img.shields.io/pypi/v/texastoast.svg)](https://pypi.org/project/texastoast/)
[![Python versions](https://img.shields.io/pypi/pyversions/texastoast.svg)](https://pypi.org/project/texastoast/)
[![CI](https://github.com/magmacrunchmedia/texastoast/actions/workflows/ci.yml/badge.svg)](https://github.com/magmacrunchmedia/texastoast/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Python RPG engine with I2C hardware abstraction for magmacrunch game systems.

A tkinter-based 2D game engine inspired by [adenosine](https://github.com/magmacrunchmedia/adenosine), with optional I2C support for Raspberry Pi hardware.

It ships a [hardware dev kit](#hardware-dev-kit) too: a simulator, a controller
test bench, and session record/replay, so you can build and test against I2C
controllers you do not have plugged in — or have not finished building.

```bash
pip install texastoast && texastoast-bench --sim
```

## Install

```bash
pip install texastoast
```

Optional extras:

```bash
pip install "texastoast[sprites]"   # Pillow, for sprite sheet cropping
pip install "texastoast[hardware]"  # smbus2, for I2C controllers on Raspberry Pi
```

Neither is required — the engine runs on keyboard input with no extras installed.

### From source

```bash
git clone https://github.com/magmacrunchmedia/texastoast.git
cd texastoast
pip install -e ".[dev]"
```

## Quick Start

```python
from texastoast import Game, CanvasRenderer, TileMap, Entity, KeyboardInput

game = Game(title="My Game", width=400, height=300, fps=30)
renderer = CanvasRenderer(game.canvas, 400, 300)
keyboard = KeyboardInput(game.root)

tilemap = TileMap([
    [1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 1],
], tile_size=20, solid_tiles={1})

player = Entity(x=40, y=24, width=14, height=14, speed=100)  # 100 px/second

def update(dt):
    state = keyboard.poll()
    player.move(state.dx, state.dy, dt, tilemap)
    renderer.camera.follow(player.center_x, player.center_y,
                           map_width=tilemap.width, map_height=tilemap.height,
                           dt=dt)

def render():
    renderer.clear()
    renderer.draw_tilemap(tilemap, {0: "#7cb342", 1: "#5d4037"})
    renderer.draw_rect(player.x, player.y, player.width, player.height, "#e94560")

game.set_update(update)
game.set_render(render)
game.start()
```

### Movement contract

- `speed` is in **pixels per second**, not per frame.
- `move()` takes the frame's `dt`, so movement is frame-rate independent.
- Diagonals are normalized: holding two directions is the same speed as one.

## Upgrading from 0.3.x

Nothing breaks. Two things are better:

- UI widgets accept the renderer in place of `game.canvas` and inherit its
  dimensions — `DialogueBox(renderer)` instead of
  `DialogueBox(game.canvas, 640, 480)`. The old form still works.
- `Camera.follow()` without `dt` now emits a `DeprecationWarning`; 0.5.0 will
  require it. Pass the frame's `dt` (the examples always have).

## Upgrading from 0.2.x

`DialogueBox` and `Menu` are now drawn by your render loop, like `HUD` always
was. If you call `renderer.clear()` each frame — the demos do — the old
widgets were being wiped off the canvas while still reporting `active`, so the
game looked frozen behind an invisible dialogue.

```python
def update(dt):
    dialogue.update(dt)      # 0.3.0 — advances the typewriter
    ...

def render():
    renderer.clear()
    ...
    hud.render()
    dialogue.render()        # 0.3.0 — both are frame-driven now
    menu.render()
```

See [CHANGELOG.md](CHANGELOG.md) for the rest.

## Upgrading from 0.1.x

`Entity.move()` gained a required `dt` argument, and a few defaults changed.
See [CHANGELOG.md](CHANGELOG.md) or the
[migration guide](https://github.com/magmacrunchmedia/texastoast/wiki/Migrating-to-0.2.0).

```python
player.move(state.dx, state.dy, tilemap)      # 0.1.x — px per frame
player.move(state.dx, state.dy, dt, tilemap)  # 0.2.0 — px per second
```

## Examples

Examples and the tile editor live in the repository, not in the installed
package — clone the repo to run them.

| Example | Description |
|---------|-------------|
| `examples/hello_world.py` | Minimal movement demo |
| `examples/tilemap_demo.py` | Walk around a larger map |
| `examples/sprite_demo.py` | Animated character sprites |
| `examples/rpg_demo.py` | NPCs, dialogue, menus, HUD |
| `examples/game_template.py` | Full game starting point |
| `examples/magma_hub_demo.py` | I2C controller input |
| `examples/hello.mgs` | The same demo written in magmascript |
| `examples/sim_input.mgs` | A simulated Magma Hub driving a game |
| `tools/tile_editor.py` | Tile map editor GUI |
| `tools/controller_bench.py` | Controller test bench (also `texastoast-bench`) |

## Hardware dev kit

You should not need the hardware to build for the hardware. Everything below
runs the *real* I2C stack — protocol handshake, hub polling, input adapters —
against a simulator when no bus is present.

### Controller test bench

```bash
texastoast-bench            # scan for hubs; simulator mode if none found
texastoast-bench --sim      # force the simulator (keyboard drives controller 0)
texastoast-bench --record session.ttrec   # capture controller 0 while open
```

Live per-controller button/joystick display, raw protocol bytes, connection
status, poll-latency stats (min/avg/max/jitter) and read-error rates. Open it
while probing wiring or iterating on hub firmware.

### Hub simulator

`SimBus` implements the smbus2 surface, so a simulated bus is a real bus to
every caller — and it enforces the firmware's select-write handshake, so it
catches protocol regressions, not just byte mismatches.

```python
from texastoast import simulated_hub
from texastoast.i2c.protocol import BTN_A

hub, sim = simulated_hub()          # a real MagmaHub over a simulated bus
sim.press(BTN_A)
assert hub.poll()[0].a              # full stack, no wires

sim.fail_next_reads(3)              # error injection: a loose wire, on demand
sim.set_read_delay(0.05)            # latency simulation
sim.disconnect_hub(0x08)            # hotplug simulation
```

### Background polling

I2C reads block; a loose wire can turn one `poll()` into a frame hitch.
`HubPoller` moves bus traffic onto a daemon thread and duck-types the hub's
read surface, so `MagmaHubInput` can't tell the difference:

```python
from texastoast import HubPoller, MagmaHubInput

poller = HubPoller(hub).start()
game.on_close(poller.stop)                   # you wire the teardown
pad = MagmaHubInput(poller)                  # poll() now never blocks
poller.stats                                 # HubStats: latency, errors
```

One poller per hub *or* direct `hub.poll()` calls — never both.

### Input recording & replay

`.ttrec` files are delta-encoded JSON Lines of protocol button bitmasks, so
one recording replays two ways: through the engine, or through the full
hardware stack.

```python
from texastoast import InputRecorder, ReplayInput

recorder = InputRecorder(controls, "session.ttrec")   # wraps any InputSource
recorder.start()
game.on_close(recorder.stop)

replay = ReplayInput("session.ttrec")                 # is an InputSource
replay.advance(dt)                                    # deterministic mode
# or replay.start() for wall-clock playback

driver = sim.play_recording("session.ttrec")          # firmware-shaped replay:
driver.advance(dt)                                    # raw bytes → SimBus → MagmaHub
```

A session recorded against real firmware (`texastoast-bench --record`) becomes
a regression test that runs anywhere.

### Testing on the Pi

CI covers all of the hardware *logic* through the simulator; the release gate
for the `hardware` extra is a manual pass on a Raspberry Pi:

1. `sudo raspi-config` → enable I2C; wire the hub; `i2cdetect -y 1` should
   show it at `0x08`–`0x0b`.
2. `pip install texastoast[hardware]` and run `texastoast-bench` — every
   button lights, the joystick crosshair tracks, poll latency is steady
   (sub-millisecond jitter on a healthy bus) and the error rate is 0/s.
3. Record a session with `--record`, replay it through `ReplayInput`, and
   keep the file — it is the firmware regression corpus.
4. Run `examples/magma_hub_demo.py` and confirm hub input drives the square
   and unplugging mid-game falls back to the keyboard.

## Documentation

Full guides live in the [wiki](https://github.com/magmacrunchmedia/texastoast/wiki);
the reference below covers the whole public API.

| Guide | Covers |
|-------|--------|
| [Getting Started](https://github.com/magmacrunchmedia/texastoast/wiki/Getting-Started) | Build a small game from nothing |
| [Core Concepts](https://github.com/magmacrunchmedia/texastoast/wiki/Core-Concepts) | The loop, `dt`, how the pieces fit |
| [Rendering and Camera](https://github.com/magmacrunchmedia/texastoast/wiki/Rendering-and-Camera) | Drawing, camera easing, the backend protocols |
| [Input](https://github.com/magmacrunchmedia/texastoast/wiki/Input) | Sources, `InputState`, record and replay |
| [UI Components](https://github.com/magmacrunchmedia/texastoast/wiki/UI-Components) | Dialogue, menus, HUD, drawing groups |
| [Magma Hub and I2C](https://github.com/magmacrunchmedia/texastoast/wiki/Magma-Hub-and-I2C) | The wire protocol and hardware interface |
| [Hardware Dev Kit](https://github.com/magmacrunchmedia/texastoast/wiki/Hardware-Dev-Kit) | Simulator, test bench, polling, recording |
| [Tile Editor](https://github.com/magmacrunchmedia/texastoast/wiki/Tile-Editor) | The map editor and its JSON format |

## API Reference

### Core

```python
from texastoast import Game, Config, GameLoop

game = Game(title="My Game", width=640, height=480, fps=30)
game.set_update(update_fn)  # def update(dt: float): ...
game.set_render(render_fn)  # def render(): ...
game.on_close(cleanup_fn)   # runs on quit(), including the window's X button
game.start()

# Embed in an existing tkinter app (the caller keeps ownership of the root
# and runs its own mainloop):
game = Game(width=640, height=480, root=my_frame)
```

### Rendering

```python
from texastoast import CanvasRenderer, Camera

renderer = CanvasRenderer(game.canvas, 640, 480)
renderer.width, renderer.height   # the viewport; UI widgets read this back

# A tile is drawn when its id has a color; ids you leave out stay transparent.
renderer.draw_tilemap(tilemap, {0: "#7cb342", 1: "#5d4037"})
renderer.draw_tilemap(tilemap, colors, skip_tiles={0})  # or skip explicitly

renderer.draw_rect(x, y, w, h, color)
renderer.draw_image(x, y, photo_image)
renderer.draw_text(x, y, text)                  # world space, follows the camera
renderer.draw_hud_text(x, y, text, fill="#fff") # screen space, ignores the camera

# Camera — pass dt; omitting it is deprecated and becomes an error in 0.5.0
renderer.camera.follow(target_x, target_y, map_width=800, map_height=600, dt=dt)
renderer.camera.set_position(x, y)
renderer.camera.world_to_screen(wx, wy)
renderer.camera.is_visible(x, y, w, h)

renderer.present()   # no-op on tkinter; end every render() with it anyway
```

`CanvasRenderer` satisfies two protocols — `Renderer` (world space) and
`UISurface` (screen space, what the UI widgets draw through). They are the
contract a future SDL/framebuffer backend implements; `present()` is included
now because a buffered backend cannot add it later without editing every game.

```python
from texastoast import Renderer, UISurface

isinstance(renderer, Renderer), isinstance(renderer, UISurface)   # (True, True)
```

### World

```python
from texastoast import TileMap, Entity, AABB

# Tile map
tilemap = TileMap(grid_data, tile_size=16, solid_tiles={1, 2})  # any iterable
tilemap = TileMap.from_file("map.json", tile_size=16)
tilemap.save("map.json")
tilemap.get(col, row)          # -> tile_id, or -1 out of bounds
tilemap.is_solid(col, row)     # -> bool (out of bounds counts as solid)
tilemap.is_solid_at(world_x, world_y)

# Entity — speed is px/second, move() takes dt
player = Entity(x=0, y=0, width=16, height=16, speed=100)
player.move(dx, dy, dt, tilemap)  # with collision; omit tilemap to skip it
player.vel_x, player.vel_y        # px/second
player.aabb                       # -> AABB for overlap checks
player.collides_with(other_entity)
```

Collision resolves each axis separately, so entities slide along walls rather
than sticking. A blocked entity stops flush against the wall, and fast movement
is sub-stepped so nothing tunnels through a tile.

### Input

```python
from texastoast import KeyboardInput, InputState

keyboard = KeyboardInput(game.root)
game.on_close(keyboard.destroy)  # release the key bindings on exit
state = keyboard.poll()

state.up, state.down, state.left, state.right  # bool
state.a, state.b, state.start, state.select     # bool
state.dx, state.dy                               # float (-1, 0, 1), raw axes
state.is_any_direction()                         # bool
```

`dx`/`dy` are raw axis reads and are *not* normalized — `Entity.move` does that
for you. If you integrate position yourself, normalize before scaling by speed.

`poll()` returns a fresh snapshot each call, so you can keep the previous
frame's state to detect a button that was just pressed:

```python
def update(dt):
    global prev
    state = keyboard.poll()
    if state.a and not prev.a:
        interact()
    prev = state
```

### I2C

Optional I2C support for connecting hardware controllers via Raspberry Pi.

```python
from texastoast import I2CBus, MagmaHub, MagmaHubInput, CompositeInput

# Direct I2C — scan_buses probes only the candidate hub addresses (4 reads);
# bus.scan() sweeps the whole range and is for diagnostics.
bus = I2CBus(1)
bus.probe(0x08)  # -> bool, one read
hubs = MagmaHub.scan_buses(bus_numbers=[1])
hub = hubs[0]
hub.poll()       # -> [ControllerState, ...] (a fresh snapshot; don't mutate)
hub.connected    # -> True only while reads are actually succeeding
hub.stats        # -> HubStats: poll_count, error_count, latency min/avg/max

# Input adapter (same interface as KeyboardInput)
hub_input = MagmaHubInput(hub, controller_index=0)
state = hub_input.poll()

# Auto-fallback composite
controls = CompositeInput(keyboard, hub_input)
state = controls.poll()  # uses hub if connected, else keyboard
```

See [Hardware dev kit](#hardware-dev-kit) for the simulator (`SimBus`,
`simulated_hub`), background polling (`HubPoller`, `scan_buses_async`) and
input recording (`InputRecorder`, `ReplayInput`).

Without `smbus2`, or with no bus present, `I2CBus` runs in mock mode: reads
return `None` rather than fabricated zeros, `hub.connected` stays `False`, and
`CompositeInput` falls through to the keyboard.

### UI

```python
from texastoast.ui import DialogueBox, Menu, HUD

# Widgets take the renderer (preferred — they inherit its dimensions) or a
# bare canvas plus explicit width/height (the pre-0.4 form, still supported).

# Dialogue
dialogue = DialogueBox(renderer)
dialogue.show("Hello, world!", speaker="NPC", on_complete=callback)
dialogue.update(dt)   # from your update(); advances the typewriter
dialogue.render()     # from your render(); safe to call when inactive
dialogue.dismiss()    # skip to the end, or close if already there
dialogue.active, dialogue.waiting, dialogue.displayed

# Menu
menu = Menu(renderer)
menu.show(["Play", "Settings", "Quit"],
          on_select=lambda i, label: print(label),
          on_cancel=lambda: menu.hide())
menu.move_up()
menu.move_down()
menu.confirm()
menu.render()         # from your render(); safe to call when inactive

# HUD
hud = HUD(renderer)
hud.add_stat("hp", "HP", value=100, max_value=100, color="#e94560")
hud.set_stat("hp", 75)
hud.add_text("score", "Score: 0", 10, 10, fill="#fdd835")
hud.set_text("score", "Score: 100")
hud.render()
```

All three widgets draw from your render function, so a renderer that clears the
canvas each frame puts them back. Call `render()` unconditionally — it is a
no-op when the widget is not showing.

## Scripting with magmascript

texastoast publishes itself to [magmascript](https://github.com/magmacrunchmedia/magmascript)
as the `texastoast` domain, or `tt` for short. Install both into the same
environment and `.mgs` scripts can drive the engine directly — neither package
depends on the other.

```bash
pip install texastoast magmascript
magmascript examples/hello.mgs
```

```magmascript
g = tt.game({"title": "hello", "width": 400, "height": 300, "fps": 30})
r = tt.renderer(g, 400, 300)
kb = tt.keyboard(g)
world = tt.tilemap([[1,1,1],[1,0,1],[1,1,1]], 20, [1])
player = tt.entity({"x": 25, "y": 25, "width": 14, "height": 14, "speed": 100})

update = fn(dt) {
    s = kb.poll()
    player.move(s.dx, s.dy, dt, world)
    r.camera.follow(player.center_x, player.center_y, world.width, world.height, dt)
}
render = fn() {
    r.clear()
    r.draw_tilemap(world, {0: "#7cb342", 1: "#5d4037"})
    r.draw_rect(player.x, player.y, player.width, player.height, "#e94560")
}
g.set_update(update)
g.set_render(render)
g.start()
```

`tt` and `texastoast` are the same domain under two names — the domain object
holds no state, so a script can use either, or both.

The domain is called `texastoast` rather than `toast` because magmascript's CLI
already spells `magmascript toast <target>` for clearing caches, and
`magmascript texas <target>` for heavy operations. Those are shell verbs that
never appear inside a script, so nothing actually collides — but reusing the
name would make the two sets of docs read as a contradiction.

Constructors take a dict rather than keyword arguments, since MagmaScript has no
keyword-argument syntax; an unknown key is an error rather than a silent
default. Everything else is the Python API unchanged — the objects a script
holds are the same objects, so `player.x` reads and `player.speed = 200` writes
go straight through.

The hardware layer is scriptable too: `tt.hub()`, `tt.hubs()` (scan),
`tt.sim_hub()` (simulator — the `SimBus` is reachable as `h.sim`),
`tt.hub_input()`, `tt.composite()`, `tt.poller()` (background polling; wire
`g.on_close(p.stop)` yourself), `tt.recorder()` and `tt.replay()`. See
[examples/sim_input.mgs](examples/sim_input.mgs) for a simulated hub driving a
game. UI factories accept the renderer in place of the game —
`tt.dialogue(r)` — and then inherit its dimensions.

Needs magmascript 3.2 or newer. See [examples/hello.mgs](examples/hello.mgs).

## Design Philosophy

- **No opinions** — engines provide systems, you wire them together
- **Configurable** — pass callbacks and data, don't inherit from base classes
- **Tiny** — small, focused modules with minimal dependencies
- **Graceful fallback** — I2C hardware is optional, keyboard always works
- **Testable** — game logic doesn't depend on tkinter, and the hardware layer
  is simulatable end to end, so the whole suite runs with no display and no I2C
- **Portable by seam** — backends sit behind protocols, so the engine can leave
  tkinter without rewriting the games

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests, and the release process.

## License

Apache-2.0. Copyright 2026 magmacrunch media.
