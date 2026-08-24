# texastoast

Python RPG engine and Magma Hub I2C layer for magmacrunch game systems.

A tkinter-based 2D game engine inspired by [adenosine](https://github.com/magmacrunchmedia/adenosine), with I2C hardware abstraction for Raspberry Pi + Pico "Magma Hub" controllers.

## Install

```bash
pip install -e .

# With I2C hardware support (Raspberry Pi only)
pip install -e ".[hardware]"
```

## Quick Start

```python
from texastoast import Game, CanvasRenderer, TileMap, KeyboardInput

game = Game(title="My Game", width=640, height=480)
renderer = CanvasRenderer(game.canvas, width=640, height=480)
tilemap = TileMap([
    [2, 2, 2, 2, 2],
    [2, 0, 0, 0, 2],
    [2, 0, 0, 0, 2],
    [2, 2, 2, 2, 2],
], tile_size=16, solid_tiles={2})

game.start()
```

## Features

- **Game loop** — tick-based update/render via `tkinter.after()`
- **Tile maps** — 2D grid world with collision
- **Camera** — viewport scrolling with target following
- **Sprites** — PNG sprite sheet loading
- **Input** — keyboard and Magma Hub I2C controller support
- **UI** — dialogue boxes, menus, HUD overlay
- **I2C** — Raspberry Pi Pico "Magma Hub" controller abstraction

## Magma Hub

The Magma Hub is a Raspberry Pico acting as an I2C slave, providing controller input (buttons + joystick) to the Pi master. texastoast abstracts this hardware so games don't need to know about I2C details.

## License

Apache-2.0. See [LICENSE](LICENSE).
