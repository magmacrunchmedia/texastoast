#!/usr/bin/env python3
"""Game template — a starting point for new texastoast games.

This demonstrates the full feature set:
  - Game loop with fixed timestep
  - Tile map with collision
  - Camera following player
  - Keyboard input
  - HUD with stats
  - Dialogue system
  - Pause menu

Copy this file and modify it to build your own game.
"""

from texastoast import CanvasRenderer, Entity, Game, KeyboardInput, TileMap
from texastoast.ui import HUD, DialogueBox, Menu

# ── Config ──────────────────────────────────────────────────────────

SCREEN_W = 400
SCREEN_H = 300
TILE_SIZE = 20
FPS = 30
PLAYER_SPEED = 100

# ── Colors ──────────────────────────────────────────────────────────

TILE_COLORS = {
    0: "#7cb342",  # grass
    1: "#5d4037",  # wall
    2: "#1e88e5",  # water
    3: "#fdd835",  # path
}

# ── Map ─────────────────────────────────────────────────────────────

LEVEL_1 = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]

# ── Init ────────────────────────────────────────────────────────────

game = Game(title="texastoast game template", width=SCREEN_W, height=SCREEN_H, fps=FPS)
renderer = CanvasRenderer(game.canvas, SCREEN_W, SCREEN_H)
keyboard = KeyboardInput(game.root)
dialogue = DialogueBox(game.canvas, SCREEN_W, SCREEN_H)
menu = Menu(game.canvas, SCREEN_W, SCREEN_H)
hud = HUD(game.canvas, SCREEN_W, SCREEN_H)

tilemap = TileMap(LEVEL_1, tile_size=TILE_SIZE, solid_tiles={1, 2})
player = Entity(x=60, y=60, width=14, height=14, speed=PLAYER_SPEED)

# ── Game state ──────────────────────────────────────────────────────

paused = False
showing_dialogue = False
hp = 100
xp = 0
score = 0

hud.add_stat("hp", "HP", value=hp, max_value=100, color="#e94560")
hud.add_stat("xp", "XP", value=xp, max_value=100, color="#4fc3f7")
hud.add_text("score", "Score: 0", SCREEN_W - 120, 4, fill="#fdd835")
hud.add_text("pos", "", 4, SCREEN_H - 16, fill="#666666", font=("Courier", 8))


# ── Input handling ──────────────────────────────────────────────────

def handle_keypress(event):
    global paused, showing_dialogue, hp, xp, score

    key = event.keysym

    if dialogue.active:
        if key in ("z", "Z", "Return", "space"):
            dialogue.dismiss()
        return

    if menu.active:
        if key in ("Up", "w", "W"):
            menu.move_up()
        elif key in ("Down", "s", "S"):
            menu.move_down()
        elif key in ("z", "Z", "Return"):
            menu.confirm()
        elif key in ("x", "X", "Escape"):
            menu.cancel()
        return

    if key in ("Escape", "p", "P"):
        toggle_pause()
    elif key in ("z", "Z", "Return"):
        # Example: press Z near water to "fish"
        col, row = tilemap.to_grid_coords(player.center_x, player.center_y)
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if tilemap.get(col + dc, row + dr) == 2:
                    showing_dialogue = True
                    dialogue.show("You caught a fish! +10 XP",
                                  on_complete=_on_dialogue_done)
                    xp = min(100, xp + 10)
                    hud.set_stat("xp", xp)
                    return


def _on_dialogue_done():
    global showing_dialogue
    showing_dialogue = False


def toggle_pause():
    global paused
    paused = not paused
    if paused:
        menu.show(["Resume", "Restart", "Quit"],
                   on_select=_on_menu_select,
                   on_cancel=lambda: toggle_pause(),
                   title="PAUSED")
    else:
        menu.hide()


def _on_menu_select(index, label):
    global paused, hp, xp, score
    if label == "Resume":
        paused = False
    elif label == "Restart":
        hp, xp, score = 100, 0, 0
        player.x, player.y = 60, 60
        hud.set_stat("hp", hp)
        hud.set_stat("xp", xp)
        paused = False
    elif label == "Quit":
        game.quit()


game.bind_key("<Key>", handle_keypress)


# ── Update ──────────────────────────────────────────────────────────

def update(dt):
    if dialogue.active or menu.active or paused:
        return

    state = keyboard.poll()
    player.move(state.dx, state.dy, dt, tilemap)
    renderer.camera.follow(
        player.center_x, player.center_y,
        map_width=tilemap.width, map_height=tilemap.height,
    )
    hud.set_text("pos", f"({int(player.x)}, {int(player.y)})")


# ── Render ──────────────────────────────────────────────────────────

def render():
    renderer.clear()
    renderer.draw_tilemap(tilemap, TILE_COLORS)
    renderer.draw_rect(player.x, player.y, player.width, player.height, "#e94560")
    hud.render()


game.set_update(update)
game.set_render(render)
game.start()
