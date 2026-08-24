"""Controller test bench — live diagnostics for Magma Hub controllers.

Run it as ``texastoast-bench`` (or ``python -m texastoast.devtools.bench``).
It shows, per controller: the eight buttons, the raw protocol bytes, the
joystick position, and per-hub connection status with poll-latency and
read-error statistics. This is the tool to have open while probing wiring or
iterating on hub firmware.

With no hardware found (or ``--sim``) it drops into simulator mode, where the
keyboard drives controller 0 through a :class:`~texastoast.i2c.sim.SimBus` —
the full I2C stack minus the wires — so the bench also serves as a reference
for the engine's hardware code paths on any machine.

The bench always reads through a :class:`~texastoast.i2c.poller.HubPoller`:
the UI thread never blocks on the bus, so a loose wire shows up as an error
rate, not a frozen window.

tkinter is imported inside functions so this module stays importable
headless (argument parsing is testable without a display).
"""

from __future__ import annotations

import argparse
import time

from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.poller import HubPoller, scan_buses_async
from texastoast.i2c.protocol import DEFAULT_HUB_ADDRESSES, ControllerState
from texastoast.i2c.sim import KeyboardHubDriver, SimBus, simulated_hub
from texastoast.input.magma_hub import MagmaHubInput
from texastoast.input.recording import InputRecorder

_BUTTON_ORDER = ["up", "down", "left", "right", "a", "b", "start", "select"]
_REFRESH_MS = 33

_BG = "#1a1a2e"
_PANEL = "#16213e"
_FG = "#ffffff"
_DIM = "#aaaaaa"
_ACCENT = "#e94560"
_OK = "#3ec96e"
_OFF = "#333333"


class _ControllerPanel:
    """One controller's row: button cells, raw bytes, joystick crosshair."""

    def __init__(self, parent, index: int):
        import tkinter as tk

        self.frame = tk.Frame(parent, bg=_PANEL, padx=6, pady=4)
        tk.Label(self.frame, text=f"controller {index}", bg=_PANEL, fg=_DIM,
                 font=("Courier", 9)).grid(row=0, column=0, sticky="w")

        buttons_frame = tk.Frame(self.frame, bg=_PANEL)
        buttons_frame.grid(row=1, column=0, sticky="w")
        self._cells: dict[str, tk.Label] = {}
        for col, name in enumerate(_BUTTON_ORDER):
            cell = tk.Label(
                buttons_frame, text=name.upper()[:4], width=5,
                bg=_OFF, fg=_DIM, font=("Courier", 9), relief="flat",
            )
            cell.grid(row=0, column=col, padx=1, pady=1)
            self._cells[name] = cell

        self._raw = tk.Label(self.frame, text="btn:0x00 joy:0x00",
                             bg=_PANEL, fg=_DIM, font=("Courier", 9))
        self._raw.grid(row=2, column=0, sticky="w")

        self._joy = tk.Canvas(self.frame, width=48, height=48,
                              bg=_OFF, highlightthickness=0)
        self._joy.grid(row=0, column=1, rowspan=3, padx=(12, 0))

    def update(self, state: ControllerState):
        for name, cell in self._cells.items():
            if getattr(state, name):
                cell.configure(bg=_ACCENT, fg=_FG)
            else:
                cell.configure(bg=_OFF, fg=_DIM)

        self._raw.configure(
            text=f"btn:0x{state.buttons:02x} joy:0x{state.joystick:02x}"
        )

        self._joy.delete("all")
        self._joy.create_line(24, 0, 24, 48, fill="#555555")
        self._joy.create_line(0, 24, 48, 24, fill="#555555")
        # One byte, nibble per axis: high nibble x, low nibble y, 8 = center.
        jx = (((state.joystick >> 4) & 0x0F) - 8) / 8.0
        jy = ((state.joystick & 0x0F) - 8) / 8.0
        cx = 24 + jx * 20
        cy = 24 + jy * 20
        self._joy.create_oval(cx - 4, cy - 4, cx + 4, cy + 4,
                              fill=_ACCENT, outline="")


class _HubPanel:
    """One hub's box: status line plus its controller panels."""

    def __init__(self, parent, source):
        import tkinter as tk

        self.source = source  # HubPoller (or anything with its read surface)
        self.frame = tk.Frame(parent, bg=_PANEL, padx=8, pady=6,
                              highlightbackground="#0f3460",
                              highlightthickness=1)

        header = tk.Frame(self.frame, bg=_PANEL)
        header.pack(fill="x")
        self._dot = tk.Label(header, text="●", bg=_PANEL, fg=_OFF,
                             font=("Courier", 12))
        self._dot.pack(side="left")
        tk.Label(header, text=f"hub 0x{source.address:02x}", bg=_PANEL,
                 fg=_FG, font=("Courier", 11, "bold")).pack(side="left", padx=(4, 0))
        self._stats_label = tk.Label(header, text="", bg=_PANEL, fg=_DIM,
                                     font=("Courier", 9))
        self._stats_label.pack(side="right")

        self.controllers = []
        for i in range(source.num_controllers):
            panel = _ControllerPanel(self.frame, i)
            panel.frame.pack(fill="x", pady=(4, 0))
            self.controllers.append(panel)

        self._last_errors = 0
        self._last_errors_t = time.monotonic()
        self._error_rate = 0.0

    def update(self):
        source = self.source
        self._dot.configure(fg=_OK if source.connected else _ACCENT)

        states = source.poll()
        for i, panel in enumerate(self.controllers):
            panel.update(states[i] if i < len(states) else ControllerState())

        stats = source.stats
        now = time.monotonic()
        elapsed = now - self._last_errors_t
        if elapsed >= 1.0:
            self._error_rate = (stats.error_count - self._last_errors) / elapsed
            self._last_errors = stats.error_count
            self._last_errors_t = now

        self._stats_label.configure(
            text=(
                f"poll {stats.avg_duration * 1000:.1f}ms avg "
                f"({stats.min_duration * 1000:.1f}–{stats.max_duration * 1000:.1f}, "
                f"jitter {stats.jitter * 1000:.1f})  "
                f"errs {stats.error_count} ({self._error_rate:.0f}/s)"
            )
        )


class BenchApp:
    """The bench window. Everything except the mainloop, for testability."""

    def __init__(self, root, record_path: str | None = None):
        import tkinter as tk

        self._root = root
        self._record_path = record_path
        self._pollers: list[HubPoller] = []
        self._panels: list[_HubPanel] = []
        self._sim: SimBus | None = None
        self._keyboard_driver: KeyboardHubDriver | None = None
        self._recorder: InputRecorder | None = None
        self._closed = False

        self._banner = tk.Label(
            root, text="scanning I2C buses…", bg=_BG, fg=_DIM,
            font=("Courier", 10), anchor="w", padx=8, pady=6,
        )
        self._banner.pack(fill="x")
        self._body = tk.Frame(root, bg=_BG, padx=8, pady=8)
        self._body.pack(fill="both", expand=True)

        if hasattr(root, "configure"):
            root.configure(bg=_BG)
        if hasattr(root, "protocol"):
            root.protocol("WM_DELETE_WINDOW", self.close)

    # ── wiring ──────────────────────────────────────────────────────

    def start_scan(self, bus_numbers: list[int], addresses: list[int] | None,
                   num_controllers: int):
        """Discover hubs off-thread; fall back to simulator mode if none."""
        def on_result(hubs: list[MagmaHub]):
            # Called from the scan thread — marshal to tkinter.
            self._root.after(0, lambda: self._on_scan_done(hubs, num_controllers))

        scan_buses_async(on_result, bus_numbers=bus_numbers,
                         addresses=addresses, num_controllers=num_controllers)

    def _on_scan_done(self, hubs: list[MagmaHub], num_controllers: int):
        if self._closed:
            return
        if hubs:
            self.attach_hubs(hubs)
        else:
            self.enter_sim_mode(num_controllers)

    def attach_hubs(self, hubs: list[MagmaHub]):
        """Show real hubs. Each gets its own background poller."""
        self._banner.configure(
            text=f"{len(hubs)} hub(s) connected", fg=_OK
        )
        for hub in hubs:
            poller = HubPoller(hub).start()
            self._pollers.append(poller)
            self._add_panel(poller)
        self._start_recorder()

    def enter_sim_mode(self, num_controllers: int = 1):
        """No hardware: simulate one hub, driven by the keyboard."""
        self._banner.configure(
            text="SIMULATOR — keyboard drives controller 0 "
                 "(arrows/WASD move, Z=A, X=B, Esc=Start, Shift=Select)",
            fg=_ACCENT,
        )
        hub, sim = simulated_hub(num_controllers=num_controllers)
        self._sim = sim
        self._keyboard_driver = KeyboardHubDriver(self._root, sim)
        poller = HubPoller(hub).start()
        self._pollers.append(poller)
        self._add_panel(poller)
        self._start_recorder()

    def _add_panel(self, poller: HubPoller):
        panel = _HubPanel(self._body, poller)
        panel.frame.pack(fill="x", pady=(0, 8))
        self._panels.append(panel)

    def _start_recorder(self):
        if self._record_path and self._pollers and self._recorder is None:
            self._recorder = InputRecorder(
                MagmaHubInput(self._pollers[0]), self._record_path
            )
            self._recorder.start()

    # ── frame loop ──────────────────────────────────────────────────

    def refresh(self):
        """One UI update. Called every frame; also directly from tests."""
        if self._keyboard_driver is not None:
            self._keyboard_driver.apply()
        for panel in self._panels:
            panel.update()
        if self._recorder is not None:
            self._recorder.poll()

    def _tick(self):
        if self._closed:
            return
        self.refresh()
        self._root.after(_REFRESH_MS, self._tick)

    def run(self):
        self._tick()

    # ── teardown ────────────────────────────────────────────────────

    def close(self):
        if self._closed:
            return
        self._closed = True
        for poller in self._pollers:
            poller.stop()
        if self._recorder is not None:
            self._recorder.stop()
        if self._keyboard_driver is not None:
            self._keyboard_driver.destroy()
        try:
            self._root.destroy()
        except Exception:
            pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="texastoast-bench",
        description="Live diagnostics for Magma Hub controllers.",
    )
    parser.add_argument("--sim", action="store_true",
                        help="force simulator mode (no I2C)")
    parser.add_argument("--bus", type=int, default=1,
                        help="I2C bus number (default 1)")
    parser.add_argument("--addr", type=lambda s: int(s, 0), default=None,
                        help="probe one address (e.g. 0x08) instead of all candidates")
    parser.add_argument("--controllers", type=int, default=1,
                        help="controllers per hub (default 1)")
    parser.add_argument("--record", metavar="PATH", default=None,
                        help="record controller 0 to a .ttrec file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    import tkinter as tk

    args = parse_args(argv)

    root = tk.Tk()
    root.title("texastoast controller bench")
    app = BenchApp(root, record_path=args.record)

    if args.sim:
        app.enter_sim_mode(args.controllers)
    else:
        addresses = [args.addr] if args.addr is not None else DEFAULT_HUB_ADDRESSES
        app.start_scan([args.bus], addresses, args.controllers)

    app.run()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
