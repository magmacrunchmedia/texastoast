#!/usr/bin/env python3
"""Magma Hub demo — shows controller input from I2C or keyboard fallback.

On a Raspberry Pi with a Magma Hub connected, this reads button/joystick
data via I2C. On other systems, it falls back to keyboard input.

Controls:
  Arrow keys / WASD — move the square
  Z / Enter — press A button
  X / Backspace — press B button
  P / Escape — start (pause)

The status bar shows which input source is active and the raw
button/joystick bytes from the Magma Hub.
"""

from texastoast import CanvasRenderer, Game, KeyboardInput
from texastoast.i2c import I2CBus, MagmaHub
from texastoast.i2c.poller import HubPoller
from texastoast.input.magma_hub import CompositeInput, MagmaHubInput

# ── Setup ───────────────────────────────────────────────────────────

game = Game(title="magma hub demo", width=320, height=240, fps=30)
renderer = CanvasRenderer(game.canvas, 320, 240)
keyboard = KeyboardInput(game.root)

# Try to find a Magma Hub on I2C bus 1. scan_buses probes only the four
# candidate hub addresses, so this is quick even on a real bus.
hub = None
bus = I2CBus(1)
if not bus.is_mock:
    hubs = MagmaHub.scan_buses(bus_numbers=[1])
    if hubs:
        hub = hubs[0]
        print(f"Magma Hub found at 0x{hub.address:02x}")
    else:
        print("No Magma Hub found — using keyboard only")
else:
    print("I2C not available — using keyboard only")

# Poll the hub on a background thread so a slow or flaky wire never stalls a
# frame; the poller has the hub's read surface, so MagmaHubInput can't tell
# the difference. One poller per hub OR direct hub.poll() calls — never both.
if hub:
    poller = HubPoller(hub).start()
    game.on_close(poller.stop)
    hub_input = MagmaHubInput(poller, controller_index=0)
else:
    hub_input = None
controls = CompositeInput(keyboard, hub_input)

# ── Player ──────────────────────────────────────────────────────────

player_x = 160.0
player_y = 120.0
player_size = 16
player_speed = 100.0

# ── Update ──────────────────────────────────────────────────────────

def update(dt):
    global player_x, player_y

    state = controls.poll()
    player_x += state.dx * player_speed * dt
    player_y += state.dy * player_speed * dt

    # clamp to screen
    player_x = max(0, min(320 - player_size, player_x))
    player_y = max(0, min(240 - player_size, player_y))


# ── Render ──────────────────────────────────────────────────────────

def render():
    renderer.clear()

    renderer.draw_rect(player_x, player_y, player_size, player_size, "#e94560")

    # Status bar
    source = controls.active_source
    state = controls.poll()
    status = f"input: {source}"
    if hub and hub.connected:
        ctrl = hub.get_controller(0)
        status += f"  btn:0x{ctrl.buttons:02x} joy:0x{ctrl.joystick:02x}"
    renderer.draw_hud_text(4, 4, status, fill="#aaaaaa", font=("Courier", 9))

    # Button indicators
    indicators = []
    if state.a:
        indicators.append("A")
    if state.b:
        indicators.append("B")
    if state.start:
        indicators.append("START")
    if state.select:
        indicators.append("SELECT")
    if indicators:
        renderer.draw_hud_text(4, 220, " ".join(indicators),
                               fill="#fdd835", font=("Courier", 10, "bold"))


game.set_update(update)
game.set_render(render)
game.start()
