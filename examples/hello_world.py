"""Minimal texastoast example — a colored square you can move with arrow keys."""

from texastoast import Game, CanvasRenderer, TileMap, Entity, KeyboardInput

# --- Setup ---
game = Game(title="texastoast hello", width=320, height=240, fps=30)
renderer = CanvasRenderer(game.canvas, 320, 240)
keyboard = KeyboardInput(game.root)

# A tiny map: 0 = grass, 1 = wall
tilemap = TileMap(
    [
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    ],
    tile_size=16,
    solid_tiles={1},
)

TILE_COLORS = {0: "#7cb342", 1: "#5d4037"}

player = Entity(x=48, y=48, width=12, height=12, speed=100)


# --- Update ---
def update(dt: float):
    state = keyboard.poll()
    player.move(state.dx, state.dy, tilemap)
    renderer.camera.follow(
        player.center_x, player.center_y,
        map_width=tilemap.width, map_height=tilemap.height,
    )


# --- Render ---
def render():
    renderer.clear()
    renderer.draw_tilemap(tilemap, TILE_COLORS)
    renderer.draw_rect(player.x, player.y, player.width, player.height, "#e94560")


game.set_update(update)
game.set_render(render)
game.start()
