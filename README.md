# texastoast

Python RPG engine with I2C hardware abstraction for magmacrunch game systems.

A tkinter-based 2D game engine inspired by [adenosine](https://github.com/magmacrunchmedia/adenosine), with optional I2C support for Raspberry Pi hardware.

## Install

```bash
# Basic install (keyboard-only, no hardware)
pip install -e .

# With I2C hardware support (Raspberry Pi)
pip install -e ".[hardware]"

# Development (includes pytest)
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

player = Entity(x=40, y=40, width=14, height=14, speed=100)

def update(dt):
    state = keyboard.poll()
    player.move(state.dx, state.dy, tilemap)
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

## Examples

| Example | Description |
|---------|-------------|
| `examples/hello_world.py` | Minimal movement demo |
| `examples/tilemap_demo.py` | Walk around a larger map |
| `examples/sprite_demo.py` | Animated character sprites |
| `examples/rpg_demo.py` | NPCs, dialogue, menus, HUD |
| `examples/game_template.py` | Full game starting point |
| `examples/magma_hub_demo.py` | I2C controller input |
| `tools/tile_editor.py` | Tile map editor GUI |

## API Reference

### Core

```python
from texastoast import Game, Config, GameLoop

game = Game(title="My Game", width=640, height=480, fps=30)
game.set_update(update_fn)  # def update(dt: float): ...
game.set_render(render_fn)  # def render(): ...
game.start()
```

### Rendering

```python
from texastoast import CanvasRenderer, Camera

renderer = CanvasRenderer(game.canvas, 640, 480)
renderer.draw_tilemap(tilemap, {0: "#7cb342", 1: "#5d4037"})
renderer.draw_rect(x, y, w, h, color)
renderer.draw_image(x, y, photo_image)
renderer.draw_hud_text(x, y, text, fill="#fff", font=("Courier", 10))

# Camera
renderer.camera.follow(target_x, target_y, map_width=800, map_height=600)
renderer.camera.set_position(x, y)
```

### World

```python
from texastoast import TileMap, Entity, AABB

# Tile map
tilemap = TileMap(grid_data, tile_size=16, solid_tiles={1, 2})
tilemap = TileMap.from_file("map.json", tile_size=16)
tilemap.save("map.json")
tilemap.get(col, row)  # -> tile_id
tilemap.is_solid(col, row)  # -> bool
tilemap.is_solid_at(world_x, world_y)  # -> bool

# Entity
player = Entity(x=0, y=0, width=16, height=16, speed=100)
player.move(dx, dy, tilemap)  # with collision
player.aabb  # -> AABB for overlap checks
player.collides_with(other_entity)  # -> bool
```

### Input

```python
from texastoast import KeyboardInput, InputState

keyboard = KeyboardInput(game.root)
state = keyboard.poll()

state.up, state.down, state.left, state.right  # bool
state.a, state.b, state.start, state.select     # bool
state.dx, state.dy                               # float (-1, 0, 1)
state.is_any_direction()                         # bool
```

### I2C

Optional I2C support for connecting hardware controllers via Raspberry Pi.

```python
from texastoast import I2CBus, MagmaHub, MagmaHubInput, CompositeInput

# Direct I2C
bus = I2CBus(1)
hubs = MagmaHub.scan_buses(bus_numbers=[1])
hub = hubs[0]
hub.poll()  # -> [ControllerState, ...]

# Input adapter (same interface as KeyboardInput)
hub_input = MagmaHubInput(hub, controller_index=0)
state = hub_input.poll()

# Auto-fallback composite
controls = CompositeInput(keyboard, hub_input)
state = controls.poll()  # uses hub if connected, else keyboard
```

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

## License

Apache-2.0. Copyright 2026 magmacrunch media.
