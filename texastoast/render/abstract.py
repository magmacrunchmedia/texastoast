"""Renderer protocols — the seam between the engine and any drawing backend.

texastoast draws with tkinter today, but the eventual target is console-class
hardware where tkinter does not go (an SDL or framebuffer backend). These
protocols capture what the engine actually asks of a backend, so game code
written against them ports for free when that backend arrives.

Both are structural (:class:`typing.Protocol`): a backend implements them by
having the methods, not by inheriting anything.
:class:`~texastoast.render.canvas.CanvasRenderer` satisfies both. This module
must never import tkinter.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Renderer(Protocol):
    """World-space drawing, offset by a camera.

    ``present()`` exists for backends that draw to an off-screen buffer and
    flip it once per frame. On tkinter it is a no-op — the Canvas is
    retained-mode — but calling it at the end of every render function costs
    nothing today and is the one habit a buffered backend cannot retrofit
    later without touching every game.
    """

    @property
    def camera(self) -> Any: ...

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    def clear(self) -> None: ...

    def present(self) -> None: ...

    def draw_tilemap(self, tilemap: Any, tile_colors: dict[int, str],
                     skip_tiles: Any = None) -> None: ...

    def draw_rect(self, x: float, y: float, w: float, h: float,
                  color: str, tag: str = "") -> None: ...

    def draw_image(self, x: float, y: float, image: Any,
                   anchor: str = "nw", tag: str = "") -> None: ...

    def draw_text(self, x: float, y: float, text: str, **kwargs: Any) -> None: ...

    def draw_hud_text(self, x: float, y: float, text: str, **kwargs: Any) -> None: ...


@runtime_checkable
class UISurface(Protocol):
    """Screen-space drawing for UI widgets, organized into named groups.

    A *group* is a widget's frame of drawing: ``begin_group(name)`` discards
    whatever the group drew last frame, and ``clear_group(name)`` removes it
    entirely (the widget was dismissed). On tkinter's retained-mode canvas
    both map to deleting a tag; an immediate-mode backend may make
    ``begin_group`` a no-op because ``clear()`` already wiped the frame.

    Within one frame, draw order is z-order — later calls draw on top. That
    is the contract; there is no other layering.
    """

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    def begin_group(self, group: str) -> None: ...

    def clear_group(self, group: str) -> None: ...

    def ui_rect(self, x: float, y: float, w: float, h: float, *,
                fill: str, outline: str = "", outline_width: int = 0,
                group: str = "") -> None: ...

    def ui_text(self, x: float, y: float, text: str, *,
                fill: str, font: Any = None, anchor: str = "nw",
                width: float | None = None, group: str = "") -> None: ...


class _CanvasUISurface:
    """Adapts a bare ``tk.Canvas`` to :class:`UISurface`.

    The backward-compatibility shim: UI widgets constructed with a raw canvas
    (the pre-0.4 signature) are wrapped in one of these. No tkinter import —
    the canvas is duck-typed.
    """

    def __init__(self, canvas: Any, width: int, height: int):
        self._canvas = canvas
        self._width = width
        self._height = height

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def begin_group(self, group: str) -> None:
        self._canvas.delete(group)

    def clear_group(self, group: str) -> None:
        self._canvas.delete(group)

    def ui_rect(self, x, y, w, h, *, fill, outline="", outline_width=0, group=""):
        self._canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=fill, outline=outline, width=outline_width, tags=group,
        )

    def ui_text(self, x, y, text, *, fill, font=None, anchor="nw",
                width=None, group=""):
        kwargs: dict[str, Any] = {
            "text": text, "fill": fill, "anchor": anchor, "tags": group,
        }
        if font is not None:
            kwargs["font"] = font
        if width is not None:
            kwargs["width"] = width
        self._canvas.create_text(x, y, **kwargs)


def as_ui_surface(surface: Any, width: int | None, height: int | None,
                  fallback_width: int = 640, fallback_height: int = 480) -> Any:
    """Resolve a widget's first constructor argument to a :class:`UISurface`.

    Accepts either a real ``UISurface`` (a ``CanvasRenderer``, or any future
    backend) or a bare ``tk.Canvas`` (the pre-0.4 signature), which gets
    wrapped. Explicit ``width``/``height`` win; otherwise they come from the
    surface, and a bare canvas falls back to the engine's defaults.
    """
    if hasattr(surface, "ui_rect"):
        return surface
    return _CanvasUISurface(
        surface,
        width if width is not None else fallback_width,
        height if height is not None else fallback_height,
    )
