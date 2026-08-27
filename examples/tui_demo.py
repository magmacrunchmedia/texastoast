#!/usr/bin/env python3
"""Terminal backend demo — the smallest thing that exercises loop, input and draw.

Run it with the ``tui`` extra installed::

    pip install "texastoast[tui]"
    python examples/tui_demo.py

Move with the arrow keys or WASD, hold space to sprint, press Q to quit. The
box bounces off the edges on its own, so the frame rate is visible even when
nothing is pressed.

Everything below is written against the ``Renderer``/``UISurface`` protocols,
not against Textual. The same render function would work on the tkinter backend
given a CanvasRenderer — which is the point of the seam.
"""

from texastoast.core.tui_game import TuiGame, TuiInput

FPS = 30
BOX_W = 6
BOX_H = 3

# Terminal cells are about twice as tall as they are wide, so horizontal speed
# is doubled to make diagonal motion look diagonal. Any pixel-space game ported
# to this backend needs the same correction — the renderer deliberately does
# not apply it, because the right factor depends on the game.
SPEED_X = 24.0
SPEED_Y = 12.0

PALETTE = {
    "bg": "#1a1a2e",
    "box": "#e94560",
    "sprint": "#f9c74f",
    "hud": "#a0a0c0",
    "text": "#ffffff",
}


class Demo:
    def __init__(self):
        # hold_ms > 0 gives decay semantics: a terminal never reports key
        # release, so a held key is inferred from its auto-repeat. 120 ms is
        # comfortably above a typical 30-50 ms repeat interval.
        self.game = TuiGame(title="texastoast TUI demo", fps=FPS,
                            input_source=TuiInput(hold_ms=120))
        self.r = self.game.renderer

        self.x = 4.0
        self.y = 2.0
        self.vx = SPEED_X
        self.vy = SPEED_Y
        self.frames = 0

        self.game.set_update(self.update)
        self.game.set_render(self.render)
        self.game.bind_key("q", lambda key: self.game.quit())
        self.game.bind_key("escape", lambda key: self.game.quit())

    def update(self, dt: float) -> None:
        self.frames += 1
        state = self.game.input.poll()
        sprint = 2.0 if state.a else 1.0

        if state.is_any_direction():
            self.x += state.dx * SPEED_X * sprint * dt
            self.y += state.dy * SPEED_Y * sprint * dt
        else:
            self.x += self.vx * dt
            self.y += self.vy * dt

        # Bounce, and clamp so a resize that shrinks the terminal cannot strand
        # the box outside the buffer.
        max_x = max(0, self.r.width - BOX_W)
        max_y = max(0, self.r.height - BOX_H - 2)
        if self.x <= 0 or self.x >= max_x:
            self.vx = -self.vx
        if self.y <= 0 or self.y >= max_y:
            self.vy = -self.vy
        self.x = min(max(self.x, 0), max_x)
        self.y = min(max(self.y, 0), max_y)

    def render(self) -> None:
        r = self.r
        r.clear()

        r.draw_rect(0, 0, r.width, r.height, PALETTE["bg"])

        sprinting = self.game.input.is_pressed("a")
        r.draw_rect(self.x, self.y, BOX_W, BOX_H,
                    PALETTE["sprint"] if sprinting else PALETTE["box"])

        r.begin_group("hud")
        r.ui_text(1, 0, f"texastoast {r.width}x{r.height} cells",
                  fill=PALETTE["text"], group="hud")
        fps = self.game.loop.fps if self.game.loop else 0.0
        r.ui_text(1, r.height - 2,
                  f"fps {fps:5.1f}   frame {self.frames:<6d}"
                  f"   pos {self.x:5.1f},{self.y:4.1f}",
                  fill=PALETTE["hud"], group="hud")
        r.ui_text(1, r.height - 1,
                  "arrows/WASD move   space sprint   Q quit",
                  fill=PALETTE["hud"], group="hud")

        # Nothing appears until this call — unlike the tkinter backend, where
        # present() is a no-op and the canvas is retained.
        r.present()


if __name__ == "__main__":
    Demo().game.start()
