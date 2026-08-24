#!/usr/bin/env python3
"""Game template — a starting point for new texastoast games.

This demonstrates the full feature set:
  - Scene stack: world, pause menu, and dialogue as scenes
  - Tile map with collision, camera following the player
  - Entity group driving updates
  - Keyboard input, HUD with stats

The 0.4.0 version of this file kept `paused` and `showing_dialogue` globals,
early-returned from update() while either was set, and dispatched keys down an
if-chain. All of that is gone: modality is the stack. Pushing PauseScene
freezes WorldScene by construction; popping it resumes. No flags exist.

Copy this file and modify it to build your own game.
"""

from texastoast import (
    CanvasRenderer,
    Entity,
    EntityGroup,
    Game,
    KeyboardInput,
    SceneStack,
    TileMap,
)
from texastoast.ui import HUD, DialogueBox, Menu

# ── Config ──────────────────────────────────────────────────────────

SCREEN_W = 400
SCREEN_H = 300
TILE_SIZE = 20
FPS = 30
PLAYER_SPEED = 100

TILE_COLORS = {
    0: "#7cb342",  # grass
    1: "#5d4037",  # wall
    2: "#1e88e5",  # water
    3: "#fdd835",  # path
}

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
game.on_close(keyboard.destroy)
stack = SceneStack()


# ── Scenes ──────────────────────────────────────────────────────────

class WorldScene:
    """The game itself: player, map, camera, HUD."""

    def __init__(self):
        self.tilemap = TileMap(LEVEL_1, tile_size=TILE_SIZE, solid_tiles={1, 2})
        self.entities = EntityGroup()
        self.player = self.entities.add(
            Entity(x=60, y=60, width=14, height=14, speed=PLAYER_SPEED), "player"
        )
        self.hp = 100
        self.xp = 0

        self.hud = HUD(renderer)
        self.hud.add_stat("hp", "HP", value=self.hp, max_value=100)
        self.hud.add_stat("xp", "XP", value=self.xp, max_value=100, color="#4fc3f7")
        self.hud.add_text("score", "Score: 0", SCREEN_W - 120, 4, fill="#fdd835")
        self.hud.add_text("pos", "", 4, SCREEN_H - 16, fill="#666666",
                          font=("Courier", 8))

    def update(self, dt):
        state = keyboard.poll()
        self.player.move(state.dx, state.dy, dt, self.tilemap)
        self.entities.update(dt)
        renderer.camera.follow(
            self.player.center_x, self.player.center_y,
            map_width=self.tilemap.width, map_height=self.tilemap.height, dt=dt,
        )
        self.hud.set_text("pos", f"({int(self.player.x)}, {int(self.player.y)})")

    def render(self):
        renderer.clear()
        renderer.draw_tilemap(self.tilemap, TILE_COLORS)
        for entity in self.entities.sorted_by_y():
            renderer.draw_rect(entity.x, entity.y, entity.width, entity.height,
                               "#e94560")
        self.hud.render()
        renderer.present()

    def handle_key(self, event):
        key = event.keysym
        if key in ("Escape", "p", "P"):
            stack.push(PauseScene(self))
            return True
        if key in ("z", "Z", "Return"):
            return self._try_fish()
        return False

    def _try_fish(self):
        # Press Z next to water to "fish".
        col, row = self.tilemap.to_grid_coords(self.player.center_x,
                                               self.player.center_y)
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                if self.tilemap.get(col + dc, row + dr) == 2:
                    self.xp = min(100, self.xp + 10)
                    self.hud.set_stat("xp", self.xp)
                    stack.push(DialogueScene("You caught a fish! +10 XP"))
                    return True
        return False

    def restart(self):
        self.hp, self.xp = 100, 0
        self.player.x, self.player.y = 60, 60
        self.hud.set_stat("hp", self.hp)
        self.hud.set_stat("xp", self.xp)


class PauseScene:
    """The pause menu, drawn over the visible, frozen world.

    No `paused` flag anywhere: the world freezes because it is not the top
    scene, and render_below keeps it visible underneath.
    """

    render_below = True

    def __init__(self, world: WorldScene):
        self._world = world
        self._menu = Menu(renderer)

    def on_enter(self):
        self._menu.show(
            ["Resume", "Restart", "Quit"],
            on_select=self._on_select,
            on_cancel=stack.pop,
            title="PAUSED",
        )

    def on_exit(self):
        self._menu.hide()

    def update(self, dt):
        pass

    def render(self):
        self._menu.render()

    def handle_key(self, event):
        key = event.keysym
        if key in ("Up", "w", "W"):
            self._menu.move_up()
        elif key in ("Down", "s", "S"):
            self._menu.move_down()
        elif key in ("z", "Z", "Return"):
            self._menu.confirm()
        elif key in ("x", "X", "Escape"):
            self._menu.cancel()
        return True

    def _on_select(self, index, label):
        if label == "Restart":
            self._world.restart()
        elif label == "Quit":
            game.quit()
            return
        stack.pop()


class DialogueScene:
    """A dialogue box over the visible world. The typewriter runs because this
    scene's update drives it; the world underneath is frozen."""

    render_below = True

    def __init__(self, text, speaker=""):
        self._dialogue = DialogueBox(renderer, speed=0.03)
        self._dialogue.show(text, speaker=speaker, on_complete=stack.pop)

    def update(self, dt):
        self._dialogue.update(dt)

    def render(self):
        self._dialogue.render()

    def handle_key(self, event):
        if event.keysym in ("z", "Z", "Return", "space"):
            self._dialogue.dismiss()
        return True


# ── Wiring ──────────────────────────────────────────────────────────

stack.push(WorldScene())
game.set_update(stack.update)
game.set_render(stack.render)
game.bind_key("<Key>", stack.dispatch_key)
game.start()
