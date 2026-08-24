# texastoast

[![PyPI](https://img.shields.io/pypi/v/texastoast.svg)](https://pypi.org/project/texastoast/)
[![Python versions](https://img.shields.io/pypi/pyversions/texastoast.svg)](https://pypi.org/project/texastoast/)
[![CI](https://github.com/magmacrunchmedia/texastoast/actions/workflows/ci.yml/badge.svg)](https://github.com/magmacrunchmedia/texastoast/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Python RPG engine with I2C hardware abstraction for magmacrunch game systems.

A tkinter-based 2D game engine inspired by [adenosine](https://github.com/magmacrunchmedia/adenosine), with optional I2C support for Raspberry Pi hardware.

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
                           map_width=tilemap.width, map_height=tilemap.height)

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
| `tools/tile_editor.py` | Tile map editor GUI |

## Documentation

Full guides live in the [wiki](https://github.com/magmacrunchmedia/texastoast/wiki).
The reference below covers the whole public API.

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

# A tile is drawn when its id has a color; ids you leave out stay transparent.
renderer.draw_tilemap(tilemap, {0: "#7cb342", 1: "#5d4037"})
renderer.draw_tilemap(tilemap, colors, skip_tiles={0})  # or skip explicitly

renderer.draw_rect(x, y, w, h, color)
renderer.draw_image(x, y, photo_image)
renderer.draw_text(x, y, text)                  # world space, follows the camera
renderer.draw_hud_text(x, y, text, fill="#fff") # screen space, ignores the camera

# Camera
renderer.camera.follow(target_x, target_y, map_width=800, map_height=600)
renderer.camera.set_position(x, y)
renderer.camera.world_to_screen(wx, wy)
renderer.camera.is_visible(x, y, w, h)
```

### World

```python
from texastoast import TileMap, Entity, AABB

# Tile map
tilemap = TileMap(grid_data, tile_size=16, solid_tiles={1, 2})
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

### I2C

Optional I2C support for connecting hardware controllers via Raspberry Pi.

```python
from texastoast import I2CBus, MagmaHub, MagmaHubInput, CompositeInput

# Direct I2C
bus = I2CBus(1)
hubs = MagmaHub.scan_buses(bus_numbers=[1])
hub = hubs[0]
hub.poll()       # -> [ControllerState, ...]
hub.connected    # -> True only while reads are actually succeeding

# Input adapter (same interface as KeyboardInput)
hub_input = MagmaHubInput(hub, controller_index=0)
state = hub_input.poll()

# Auto-fallback composite
controls = CompositeInput(keyboard, hub_input)
state = controls.poll()  # uses hub if connected, else keyboard
```

Without `smbus2`, or with no bus present, `I2CBus` runs in mock mode: reads
return `None` rather than fabricated zeros, `hub.connected` stays `False`, and
`CompositeInput` falls through to the keyboard.

### UI

```python
from texastoast.ui import DialogueBox, Menu, HUD

# Dialogue
dialogue = DialogueBox(game.canvas, 640, 480)
dialogue.show("Hello, world!", speaker="NPC", on_complete=callback)
dialogue.dismiss()

# Menu
menu = Menu(game.canvas, 640, 480)
menu.show(["Play", "Settings", "Quit"],
          on_select=lambda i, label: print(label),
          on_cancel=lambda: menu.hide())
menu.move_up()
menu.move_down()
menu.confirm()

# HUD
hud = HUD(game.canvas, 640, 480)
hud.add_stat("hp", "HP", value=100, max_value=100, color="#e94560")
hud.set_stat("hp", 75)
hud.add_text("score", "Score: 0", 10, 10, fill="#fdd835")
hud.set_text("score", "Score: 100")
hud.render()
```

## Design Philosophy

- **No opinions** — engines provide systems, you wire them together
- **Configurable** — pass callbacks and data, don't inherit from base classes
- **Tiny** — small, focused modules with minimal dependencies
- **Graceful fallback** — I2C hardware is optional, keyboard always works
- **Testable** — game logic doesn't depend on tkinter

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests, and the release process.

## License

Apache-2.0. Copyright 2026 magmacrunch media.
