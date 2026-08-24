#!/usr/bin/env python3
"""RPG demo — walk around, talk to NPCs, open menus, manage stats."""

from texastoast import CanvasRenderer, Entity, Game, KeyboardInput, TileMap
from texastoast.ui import HUD, DialogueBox, Menu

# ── Setup ───────────────────────────────────────────────────────────

game = Game(title="texastoast rpg demo", width=400, height=300, fps=30)
renderer = CanvasRenderer(game.canvas, 400, 300)
keyboard = KeyboardInput(game.root)
dialogue = DialogueBox(game.canvas, 400, 300, speed=0.04)
menu = Menu(game.canvas, 400, 300)
hud = HUD(game.canvas, 400, 300)

# ── Map ─────────────────────────────────────────────────────────────

grid = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 6, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]

TILE_COLORS = {
    0: "#7cb342",  # grass
    1: "#5d4037",  # wall
    2: "#1e88e5",  # water
    3: "#fdd835",  # path
    6: "#ab47bc",  # npc
    7: "#78909c",  # sign
}

tilemap = TileMap(grid, tile_size=20, solid_tiles={1, 2})
player = Entity(x=60, y=60, width=14, height=14, speed=100)

# ── NPCs ────────────────────────────────────────────────────────────

NPCS = {
    (3, 3): {"name": "Old Wizard", "dialogue": "Welcome, young traveler! The dungeon lies to the east. Be careful..."},
    (15, 3): {"name": "Merchant", "dialogue": "I sell the finest swords in all the land! ...Oh, you have no gold? Come back later."},
    (3, 10): {"name": "Guard", "dialogue": "Halt! You may pass. I'm just kidding, there's no door here."},
    (15, 10): {"name": "Mysterious Cat", "dialogue": "Meow."},
}

# ── State ───────────────────────────────────────────────────────────

paused = False
showing_dialogue = False


def check_npc_proximity():
    for (nc, nr), npc_data in NPCS.items():
        nx = nc * tilemap.tile_size + tilemap.tile_size / 2
        ny = nr * tilemap.tile_size + tilemap.tile_size / 2
        dist = ((player.center_x - nx) ** 2 + (player.center_y - ny) ** 2) ** 0.5
        if dist < 30:
            return npc_data
    return None


# ── Input ───────────────────────────────────────────────────────────

def handle_keypress(event):
    global paused, showing_dialogue

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

    if key in ("Escape", "p", "P") and not showing_dialogue:
        toggle_pause()
    elif key in ("z", "Z", "Return"):
        npc = check_npc_proximity()
        if npc:
            showing_dialogue = True
            dialogue.show(
                npc["dialogue"],
                speaker=npc["name"],
                on_complete=_on_dialogue_done,
            )


def _on_dialogue_done():
    global showing_dialogue
    showing_dialogue = False


def toggle_pause():
    global paused
    paused = not paused
    if paused:
        menu.show(
            ["Resume", "Settings", "Quit"],
            on_select=_on_menu_select,
            on_cancel=lambda: toggle_pause(),
            title="PAUSED",
        )
    else:
        menu.hide()


def _on_menu_select(index, label):
    global paused
    if label == "Resume":
        paused = False
    elif label == "Quit":
        game.quit()


game.bind_key("<Key>", handle_keypress)

# ── HUD setup ───────────────────────────────────────────────────────

hud.add_stat("health", "HP", value=80, max_value=100, color="#e94560")
hud.add_stat("xp", "XP", value=35, max_value=100, color="#4fc3f7")
hud.add_text("score", "Score: 0", 290, 8, fill="#fdd835")

score = 0


# ── Update ──────────────────────────────────────────────────────────

def update(dt):
    global score

    dialogue.update(dt)

    if dialogue.active or menu.active or paused:
        return

    state = keyboard.poll()
    player.move(state.dx, state.dy, dt, tilemap)
    renderer.camera.follow(
        player.center_x, player.center_y,
        map_width=tilemap.width, map_height=tilemap.height, dt=dt,
    )

    # proximity hint
    npc = check_npc_proximity()
    if npc:
        hud.add_text("hint", f"Press Z to talk to {npc['name']}", 8, 280,
                      fill="#aaaaaa", font=("Courier", 9))
    else:
        hud.remove_text("hint")


# ── Render ──────────────────────────────────────────────────────────

def render():
    renderer.clear()
    renderer.draw_tilemap(tilemap, TILE_COLORS)
    renderer.draw_rect(player.x, player.y, player.width, player.height, "#e94560")
    hud.render()
    dialogue.render()
    menu.render()


game.set_update(update)
game.set_render(render)
game.start()
