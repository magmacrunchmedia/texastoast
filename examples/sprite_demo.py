#!/usr/bin/env python3
"""Sprite demo — shows procedural sprite generation and sprite sheet usage.

Since we can't bundle image files, this demo generates a simple sprite
sheet at runtime using Pillow (if available) or tkinter PhotoImage,
then animates a character walking across the screen.

On systems without Pillow, it falls back to colored rectangles.
"""

import tkinter as tk
from texastoast import Game, CanvasRenderer, KeyboardInput
from texastoast.ui import HUD

# ── Procedural sprite generation ────────────────────────────────────

FRAME_W = 16
FRAME_H = 16
ANIM_FRAMES = 4
SPRITE_SHEET_W = FRAME_W * ANIM_FRAMES
SPRITE_SHEET_H = FRAME_H * 3  # 3 animation rows: down, right, up

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def create_character_sheet(root) -> list[list[tk.PhotoImage]]:
    """Generate a simple character sprite sheet procedurally."""
    frames = [[], [], []]  # down, right, up

    if HAS_PIL:
        img = Image.new("RGBA", (SPRITE_SHEET_W, sprite_sheet_h := SPRITE_SHEET_H), (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)

        colors = ["#e94560", "#4fc3f7", "#66bb6a"]
        body_colors = ["#ff8a80", "#80d8ff", "#a5d6a7"]

        for row in range(3):
            for col in range(ANIM_FRAMES):
                x = col * FRAME_W
                y = row * FRAME_H
                bc = body_colors[row]
                # simple character: head + body + legs
                draw.ellipse([x+4, y+1, x+12, y+7], fill=colors[row])  # head
                draw.rectangle([x+5, y+7, x+11, y+13], fill=bc)  # body
                # legs with walk animation
                leg_offset = [0, 1, 0, -1][col]
                draw.rectangle([x+5, y+13, x+7, y+15], fill=colors[row])
                draw.rectangle([x+9, y+13, x+11, y+15 + leg_offset], fill=colors[row])

        tk_image = ImageTk.PhotoImage(img)

        for row in range(3):
            for col in range(ANIM_FRAMES):
                x = col * FRAME_W
                y = row * FRAME_H
                frame = tk_image.subsample(1, 1)
                # Use copy with crop region
                f = img.crop((x, y, x + FRAME_W, y + FRAME_H))
                frames[row].append(ImageTk.PhotoImage(f))

        # Keep reference
        frames._tk_image = tk_image  # type: ignore
    else:
        # Fallback: colored rectangles
        colors = ["#e94560", "#4fc3f7", "#66bb6a"]
        for row in range(3):
            for col in range(ANIM_FRAMES):
                img = tk.PhotoImage(width=FRAME_W, height=FRAME_H)
                # Simple body shape
                img.put(colors[row], to=(5, 1, 11, 7))
                img.put(colors[row], to=(5, 7, 11, 13))
                img.put("#ffffff", to=(5, 13, 7, 15))
                leg_off = [0, 1, 0, -1][col]
                img.put("#ffffff", to=(9, 13, 11, 15 + leg_off))
                frames[row].append(img)

    return frames


# ── Game ────────────────────────────────────────────────────────────

game = Game(title="sprite demo", width=400, height=300, fps=12)
renderer = CanvasRenderer(game.canvas, 400, 300)
keyboard = KeyboardInput(game.root)
hud = HUD(game.canvas, 400, 300)

# Generate sprites
sheets = create_character_sheet(game.root)

# Player state
player_x = 200.0
player_y = 150.0
player_speed = 60.0
direction = 0  # 0=down, 1=right, 2=up
frame = 0
anim_timer = 0.0
anim_speed = 0.15

hud.add_text("title", "SPRITE DEMO", 4, 4, fill="#ffffff", font=("Courier", 10, "bold"))
hud.add_text("dir", "direction: down", 4, 20, fill="#aaaaaa", font=("Courier", 9))
hud.add_text("hint", "WASD to move", 4, 36, fill="#666666", font=("Courier", 9))


def update(dt):
    global player_x, player_y, direction, frame, anim_timer

    state = keyboard.poll()
    moved = state.is_any_direction()

    if moved:
        anim_timer += dt
        if anim_timer >= anim_speed:
            anim_timer = 0.0
            frame = (frame + 1) % ANIM_FRAMES

        player_x += state.dx * player_speed * dt
        player_y += state.dy * player_speed * dt

        if state.dy > 0:
            direction = 0
        elif state.dx > 0:
            direction = 1
        elif state.dy < 0:
            direction = 2
        elif state.dx < 0:
            direction = 1  # mirror right for left

        # Clamp
        player_x = max(0, min(400 - FRAME_W * 2, player_x))
        player_y = max(0, min(300 - FRAME_H * 2, player_y))
    else:
        frame = 0
        anim_timer = 0.0

    dir_names = ["down", "right", "up"]
    hud.set_text("dir", f"direction: {dir_names[direction]} frame: {frame}")


def render():
    renderer.clear()

    # Draw sprite
    sprite_frame = sheets[direction][frame]
    renderer.draw_image(player_x, player_y, sprite_frame)

    # Draw a simple ground line
    renderer.draw_rect(0, 260, 400, 40, "#5d4037")

    hud.render()


game.set_update(update)
game.set_render(render)
game.start()
