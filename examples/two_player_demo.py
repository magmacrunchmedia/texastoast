#!/usr/bin/env python3
"""Two-player demo — seats, join-by-press, and hotplug, with zero hardware.

Player 1 is the keyboard. Player 2 is a *simulated* Magma Hub controller
driven by a little autopilot, so the demo runs anywhere: you watch P2 join by
"pressing" A, wander around, get unplugged (the sim disconnects the hub),
drop to inactive without stuck buttons, then come back — reclaiming the same
seat, because a bounced cable must never reshuffle who is P1 and who is P2.

Press Z or Enter to join as Player 1. Arrow keys / WASD to move.

On a Raspberry Pi with real hubs, replace the simulator block with:

    hubs = MagmaHub.scan_buses(bus_numbers=[1])
    for hub in hubs:
        poller = HubPoller(hub).start()
        game.on_close(poller.stop)
        manager.add_hub(poller)
"""

from texastoast import (
    CanvasRenderer,
    Game,
    KeyboardInput,
    PlayerManager,
    simulated_hub,
)
from texastoast.i2c.protocol import BTN_A, BTN_DOWN, BTN_LEFT, BTN_RIGHT, BTN_UP
from texastoast.ui import HUD

W, H = 400, 300
PLAYER_COLORS = ["#e94560", "#4fc3f7", "#7cb342", "#fdd835"]

game = Game(title="two player demo", width=W, height=H, fps=30)
renderer = CanvasRenderer(game.canvas, W, H)
keyboard = KeyboardInput(game.root)
game.on_close(keyboard.destroy)
hud = HUD(renderer)

# ── Seats ───────────────────────────────────────────────────────────

manager = PlayerManager(
    max_players=2,
    on_join=lambda p: hud.set_text("status", f"Player {p.index + 1} joined!"),
    on_leave=lambda p: hud.set_text("status", f"Player {p.index + 1} disconnected"),
)
manager.add_source(keyboard)

hub, sim = simulated_hub()
manager.add_hub(hub)

hud.add_text("status", "Press Z / A to join", 8, 8)

# ── The autopilot driving the simulated controller ──────────────────

SCRIPT = [
    # (at_seconds, action)
    (2.0, lambda: sim.press(BTN_A)),          # P2 joins
    (2.3, lambda: sim.release(BTN_A)),
    (3.0, lambda: sim.press(BTN_RIGHT)),
    (5.0, lambda: sim.release(BTN_RIGHT)),
    (5.0, lambda: sim.press(BTN_DOWN)),
    (6.5, lambda: sim.release(BTN_DOWN)),
    (8.0, lambda: sim.disconnect_hub(0x08)),  # "cable falls out" mid-walk
    (11.0, lambda: sim.reconnect_hub(0x08)),  # plugged back in — same seat
    (12.0, lambda: sim.press(BTN_LEFT)),
    (14.0, lambda: sim.release(BTN_LEFT)),
    (14.0, lambda: sim.press(BTN_UP)),
    (15.5, lambda: sim.release(BTN_UP)),
]

clock = 0.0
cursor = 0

# ── Game state ──────────────────────────────────────────────────────

positions = [[100.0, 150.0], [280.0, 150.0]]
SPEED = 100.0


def update(dt):
    global clock, cursor
    clock += dt
    while cursor < len(SCRIPT) and SCRIPT[cursor][0] <= clock:
        SCRIPT[cursor][1]()
        cursor += 1

    manager.update()
    for player in manager.joined_players:
        state = player.poll()
        pos = positions[player.index]
        pos[0] = max(0, min(W - 16, pos[0] + state.dx * SPEED * dt))
        pos[1] = max(20, min(H - 16, pos[1] + state.dy * SPEED * dt))


def render():
    renderer.clear()
    for player in manager.players:
        if not player.joined:
            continue
        x, y = positions[player.index]
        color = PLAYER_COLORS[player.index] if player.active else "#555555"
        renderer.draw_rect(x, y, 16, 16, color)
        renderer.draw_hud_text(x, y - 14, f"P{player.index + 1}",
                               fill=color, font=("Courier", 8))
    hud.render()
    renderer.present()


game.set_update(update)
game.set_render(render)
game.start()
