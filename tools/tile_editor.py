#!/usr/bin/env python3
"""texastoast tile map editor — draw maps for the RPG engine."""

from __future__ import annotations

import json
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox

# ── Defaults ────────────────────────────────────────────────────────

DEFAULT_COLS = 20
DEFAULT_ROWS = 15
DEFAULT_TILE_SIZE = 24


@dataclass
class Tile:
    """One palette entry: how a tile id looks and whether it blocks movement."""
    name: str
    color: str
    solid: bool = False


# Whether a tile blocks movement is a property of the tile, not of "is it
# non-zero" — grass, paths, NPCs and signs are all walkable.
DEFAULT_PALETTES: dict[int, Tile] = {
    0: Tile("empty", "#7cb342", solid=False),
    1: Tile("wall", "#5d4037", solid=True),
    2: Tile("water", "#1e88e5", solid=True),
    3: Tile("path", "#fdd835", solid=False),
    4: Tile("door", "#e94560", solid=False),
    5: Tile("chest", "#ff9800", solid=False),
    6: Tile("npc", "#ab47bc", solid=False),
    7: Tile("sign", "#78909c", solid=False),
}


@dataclass
class HistoryEntry:
    grid: list[list[int]]


# ── Editor ──────────────────────────────────────────────────────────

class TileEditor:
    def __init__(self, root: tk.Tk):
        self._root = root
        self._root.title("texastoast tile editor")
        self._root.configure(bg="#2b2b2b")

        self._cols = DEFAULT_COLS
        self._rows = DEFAULT_ROWS
        self._tile_size = DEFAULT_TILE_SIZE
        self._palette: dict[int, Tile] = {
            tid: Tile(t.name, t.color, t.solid)
            for tid, t in DEFAULT_PALETTES.items()
        }
        self._selected_id = 1
        self._show_grid = True
        self._painting = False
        self._file_path: str | None = None

        self._grid: list[list[int]] = [
            [0] * self._cols for _ in range(self._rows)
        ]

        self._history: list[HistoryEntry] = []
        self._redo_stack: list[HistoryEntry] = []
        self._max_history = 100

        self._build_ui()
        self._draw_grid()

    # ── UI construction ─────────────────────────────────────────────

    def _build_ui(self):
        menubar = tk.Menu(self._root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self._new_map, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self._save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Resize Grid", command=self._resize_dialog)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        self._grid_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Grid", variable=self._grid_var,
                                  command=self._toggle_grid, accelerator="Ctrl+G")
        menubar.add_cascade(label="View", menu=view_menu)

        self._root.config(menu=menubar)
        self._root.bind("<Control-n>", lambda e: self._new_map())
        self._root.bind("<Control-o>", lambda e: self._open_file())
        self._root.bind("<Control-s>", lambda e: self._save_file())
        self._root.bind("<Control-z>", lambda e: self._undo())
        self._root.bind("<Control-y>", lambda e: self._redo())
        self._root.bind("<Control-g>", lambda e: self._toggle_grid())

        main = tk.Frame(self._root, bg="#2b2b2b")
        main.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(main, bg="#2b2b2b", width=160)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=4, pady=4)

        tk.Label(left, text="TILES", bg="#2b2b2b", fg="#ffffff",
                 font=("Courier", 10, "bold")).pack(pady=(0, 4))

        self._palette_frame = tk.Frame(left, bg="#2b2b2b")
        self._palette_frame.pack(fill=tk.X)
        self._build_palette()

        tk.Label(left, text="", bg="#2b2b2b").pack()  # spacer

        ctrl = tk.Frame(left, bg="#2b2b2b")
        ctrl.pack(fill=tk.X, padx=2)

        tk.Button(ctrl, text="Save", command=self._save_file, width=8).pack(pady=1)
        tk.Button(ctrl, text="Open", command=self._open_file, width=8).pack(pady=1)
        tk.Button(ctrl, text="Undo", command=self._undo, width=8).pack(pady=1)
        tk.Button(ctrl, text="Redo", command=self._redo, width=8).pack(pady=1)
        tk.Button(ctrl, text="Resize", command=self._resize_dialog, width=8).pack(pady=1)

        center = tk.Frame(main, bg="#3c3c3c")
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)

        canvas_w = self._cols * self._tile_size
        canvas_h = self._rows * self._tile_size

        self._canvas = tk.Canvas(center, width=canvas_w, height=canvas_h,
                                 bg="#1a1a1a", highlightthickness=0)
        self._canvas.pack(padx=8, pady=8)

        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<B1-Motion>", self._on_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)
        self._canvas.bind("<Button-3>", self._on_right_click)
        self._canvas.bind("<B3-Motion>", self._on_right_drag)
        self._canvas.bind("<Motion>", self._on_hover)

        self._status = tk.Label(self._root, text="Ready", bg="#1e1e1e", fg="#aaaaaa",
                                anchor=tk.W, font=("Courier", 9), padx=8)
        self._status.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_palette(self):
        for widget in self._palette_frame.winfo_children():
            widget.destroy()

        self._solid_vars: dict[int, tk.BooleanVar] = {}
        for tile_id, tile in sorted(self._palette.items()):
            frame = tk.Frame(self._palette_frame, bg="#2b2b2b")
            frame.pack(fill=tk.X, pady=1)

            btn = tk.Button(frame, bg=tile.color, width=3, height=1,
                            relief=tk.SUNKEN if tile_id == self._selected_id else tk.RAISED,
                            command=lambda tid=tile_id: self._select_tile(tid))
            btn.pack(side=tk.LEFT, padx=(0, 4))

            label_text = f"{tile_id}: {tile.name}"
            tk.Label(frame, text=label_text, bg="#2b2b2b", fg="#cccccc",
                     font=("Courier", 9), anchor=tk.W).pack(side=tk.LEFT)

            var = tk.BooleanVar(value=tile.solid)
            self._solid_vars[tile_id] = var
            tk.Checkbutton(
                frame, text="solid", variable=var, bg="#2b2b2b", fg="#888888",
                selectcolor="#1a1a1a", activebackground="#2b2b2b",
                activeforeground="#cccccc", font=("Courier", 8),
                command=lambda tid=tile_id: self._toggle_solid(tid),
            ).pack(side=tk.RIGHT)

    def _select_tile(self, tile_id: int):
        self._selected_id = tile_id
        self._build_palette()
        tile = self._palette.get(tile_id)
        name = tile.name if tile else "?"
        self._status.config(text=f"Selected: {tile_id} ({name})")

    def _toggle_solid(self, tile_id: int):
        tile = self._palette.get(tile_id)
        if tile is None:
            return
        tile.solid = self._solid_vars[tile_id].get()
        state = "solid" if tile.solid else "walkable"
        self._status.config(text=f"{tile_id} ({tile.name}) is now {state}")

    # ── Drawing ─────────────────────────────────────────────────────

    def _draw_grid(self):
        self._canvas.delete("all")
        ts = self._tile_size

        for row in range(self._rows):
            for col in range(self._cols):
                tile_id = self._grid[row][col]
                x1 = col * ts
                y1 = row * ts
                x2 = x1 + ts
                y2 = y1 + ts

                color = self._get_tile_color(tile_id)
                self._canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

                if self._show_grid:
                    self._canvas.create_rectangle(x1, y1, x2, y2,
                                                  outline="#444444", width=1)

    def _get_tile_color(self, tile_id: int) -> str:
        if tile_id in self._palette:
            return self._palette[tile_id].color
        return f"#{(tile_id * 37) % 256:02x}{(tile_id * 73) % 256:02x}{(tile_id * 113) % 256:02x}"

    def _tile_at(self, event) -> tuple[int, int] | None:
        col = int(event.x // self._tile_size)
        row = int(event.y // self._tile_size)
        if 0 <= col < self._cols and 0 <= row < self._rows:
            return col, row
        return None

    # ── Paint events ────────────────────────────────────────────────

    def _on_click(self, event):
        self._push_history()
        self._painting = True
        self._paint(event, self._selected_id)

    def _on_drag(self, event):
        if self._painting:
            self._paint(event, self._selected_id)

    def _on_release(self, event):
        self._painting = False

    def _on_right_click(self, event):
        self._push_history()
        self._paint(event, 0)

    def _on_right_drag(self, event):
        self._paint(event, 0)

    def _paint(self, event, tile_id: int):
        tile = self._tile_at(event)
        if tile is None:
            return
        col, row = tile
        if self._grid[row][col] == tile_id:
            return
        self._grid[row][col] = tile_id
        ts = self._tile_size
        x1, y1 = col * ts, row * ts
        x2, y2 = x1 + ts, y1 + ts
        color = self._get_tile_color(tile_id)
        self._canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
        if self._show_grid:
            self._canvas.create_rectangle(x1, y1, x2, y2, outline="#444444", width=1)

    def _on_hover(self, event):
        tile = self._tile_at(event)
        if tile:
            col, row = tile
            tile_id = self._grid[row][col]
            tile = self._palette.get(tile_id)
            name = tile.name if tile else "?"
            solid = " solid" if tile and tile.solid else ""
            self._status.config(text=f"({col}, {row}) tile={tile_id} ({name}){solid}")
        else:
            self._status.config(text="Ready")

    # ── History ─────────────────────────────────────────────────────

    def _push_history(self):
        snapshot = [row[:] for row in self._grid]
        self._history.append(HistoryEntry(grid=snapshot))
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self._redo_stack.clear()

    def _undo(self):
        if not self._history:
            return
        current = HistoryEntry(grid=[row[:] for row in self._grid])
        self._redo_stack.append(current)
        entry = self._history.pop()
        self._grid = entry.grid
        self._draw_grid()
        self._status.config(text="Undo")

    def _redo(self):
        if not self._redo_stack:
            return
        current = HistoryEntry(grid=[row[:] for row in self._grid])
        self._history.append(current)
        entry = self._redo_stack.pop()
        self._grid = entry.grid
        self._draw_grid()
        self._status.config(text="Redo")

    # ── File I/O ────────────────────────────────────────────────────

    def _new_map(self):
        if not messagebox.askyesno("New", "Discard current map?"):
            return
        self._grid = [[0] * self._cols for _ in range(self._rows)]
        self._history.clear()
        self._redo_stack.clear()
        self._file_path = None
        self._root.title("texastoast tile editor")
        self._draw_grid()
        self._status.config(text="New map")

    def _open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            grid = data["grid"]
            if not isinstance(grid, list) or not all(isinstance(r, list) for r in grid):
                raise ValueError("'grid' must be a list of rows")

            self._rows = len(grid)
            self._cols = max((len(r) for r in grid), default=0)
            # Pad ragged rows: every row is indexed up to _cols when painting.
            self._grid = [list(r) + [0] * (self._cols - len(r)) for r in grid]
            self._tile_size = data.get("tile_size", 16)

            saved_solid = set(data.get("solid_tiles", []))
            for tid in {t for row in self._grid for t in row} | saved_solid:
                if tid not in self._palette:
                    self._palette[tid] = Tile(f"tile_{tid}", self._get_tile_color(tid))
            for tid, tile in self._palette.items():
                tile.solid = tid in saved_solid
            self._build_palette()
            self._file_path = path
            self._history.clear()
            self._redo_stack.clear()
            self._root.title(f"texastoast tile editor — {path}")
            self._rebuild_canvas()
            self._status.config(text=f"Opened: {path} ({self._cols}x{self._rows})")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _save_file(self):
        if self._file_path:
            self._do_save(self._file_path)
        else:
            self._save_file_as()

    def _save_file_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not path:
            return
        self._file_path = path
        self._root.title(f"texastoast tile editor — {path}")
        self._do_save(path)

    def _do_save(self, path: str):
        # Solidity comes from the palette. Treating every non-zero id as solid
        # turned grass, paths and NPCs into walls the player could not cross.
        used = {tid for row in self._grid for tid in row}
        solid_tiles = sorted(
            tid for tid in used
            if tid in self._palette and self._palette[tid].solid
        )
        data = {
            "grid": self._grid,
            "tile_size": self._tile_size,
            "solid_tiles": solid_tiles,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._status.config(text=f"Saved: {path}")

    # ── Grid management ─────────────────────────────────────────────

    def _rebuild_canvas(self):
        canvas_w = self._cols * self._tile_size
        canvas_h = self._rows * self._tile_size
        self._canvas.config(width=canvas_w, height=canvas_h)
        self._draw_grid()

    def _resize_dialog(self):
        dialog = tk.Toplevel(self._root)
        dialog.title("Resize Grid")
        dialog.configure(bg="#2b2b2b")
        dialog.transient(self._root)
        dialog.grab_set()

        tk.Label(dialog, text="Columns:", bg="#2b2b2b", fg="#ffffff").grid(
            row=0, column=0, padx=8, pady=4, sticky=tk.E)
        cols_var = tk.IntVar(value=self._cols)
        tk.Entry(dialog, textvariable=cols_var, width=8).grid(
            row=0, column=1, padx=8, pady=4)

        tk.Label(dialog, text="Rows:", bg="#2b2b2b", fg="#ffffff").grid(
            row=1, column=0, padx=8, pady=4, sticky=tk.E)
        rows_var = tk.IntVar(value=self._rows)
        tk.Entry(dialog, textvariable=rows_var, width=8).grid(
            row=1, column=1, padx=8, pady=4)

        def apply_resize():
            new_cols = cols_var.get()
            new_rows = rows_var.get()
            if new_cols < 1 or new_rows < 1:
                return
            self._push_history()
            old_grid = self._grid
            self._cols = new_cols
            self._rows = new_rows
            self._grid = [[0] * new_cols for _ in range(new_rows)]
            for r in range(min(len(old_grid), new_rows)):
                for c in range(min(len(old_grid[r]), new_cols)):
                    self._grid[r][c] = old_grid[r][c]
            self._rebuild_canvas()
            dialog.destroy()
            self._status.config(text=f"Resized to {new_cols}x{new_rows}")

        tk.Button(dialog, text="Apply", command=apply_resize, width=10).grid(
            row=2, column=0, columnspan=2, pady=8)

    def _toggle_grid(self):
        self._show_grid = self._grid_var.get()
        self._draw_grid()


# ── Main ────────────────────────────────────────────────────────────

def main():
    root = tk.Tk()
    TileEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
