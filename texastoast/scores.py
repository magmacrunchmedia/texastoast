"""High scores that survive the process, with no server and no dependencies.

A score you lose when you close the terminal is not a high score, it is a
number on a screen. This is the part that makes it a record: a JSON file per
game in a per-user data directory, written atomically, read back on the next
run.

**It is deliberately shaped like the web arcade's scoreboard.** The browser
games post to a WebSocket backend through
``@magmacrunch/adenosine-score-client``, and that client keeps exactly this
structure in ``localStorage`` as its offline fallback: entries of
``{initials, score, ...extra}``, sorted descending, the top hundred kept, and
a rank counted against the *whole* list rather than the truncated one. Matching
it is not decoration — it is what makes a future sync additive rather than a
translation layer, because the records on both sides already agree.

What is deliberately **not** here is the sync itself. Talking to the backend
needs a WebSocket client, which is a dependency this engine does not have and
should not acquire on behalf of every game that wants to remember a number.
:attr:`SaveResult.synced` is the seam: it is always ``False`` today, and the
day something does send scores upstream it becomes the answer to "did that
reach the server", with nothing else changing shape.

Nothing here imports anything outside the standard library, and nothing here
knows what a terminal is. A score file is data.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

#: How many entries a game's file keeps. The same hundred the browser client
#: keeps in localStorage.
LIMIT = 100

#: Initials are three characters, as they are on the web and as they have been
#: on every arcade cabinet since before anyone reading this was born.
INITIALS_LENGTH = 3

#: Overrides where score files live. Set it to a temporary directory in tests,
#: or to somewhere shared on a machine where several people play.
DATA_DIR_ENV = "MAGMACRUNCH_DATA_DIR"


@dataclass(frozen=True)
class ScoreEntry:
    """One line on a scoreboard.

    ``extra`` carries whatever a game wants to remember alongside the number —
    the mode it was set in, the character it was flown with — and is stored
    flattened into the record, which is the shape the web client uses.
    """

    initials: str
    score: int
    extra: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        return {"initials": self.initials, "score": self.score, **self.extra}

    @classmethod
    def from_record(cls, record: dict) -> ScoreEntry:
        extra = {k: v for k, v in record.items()
                 if k not in ("initials", "score")}
        return cls(initials=str(record.get("initials", "")),
                   score=int(record.get("score", 0)),
                   extra=extra)


@dataclass(frozen=True)
class SaveResult:
    """What came of saving a score."""

    #: 1-based position among every score the game knows, not just the ones
    #: kept. A run that misses the table still gets told where it landed.
    rank: int
    entry: ScoreEntry
    #: Whether the score reached a server. Always False while there is no
    #: server to reach — see the module docstring.
    synced: bool = False
    #: How many entries the board that produced this keeps. Carried rather than
    #: read off the module constant, because a book may keep fewer — and a
    #: result that answered against somebody else's limit would be wrong in
    #: exactly the case the caller cares about.
    limit: int = LIMIT

    @property
    def made_the_table(self) -> bool:
        return self.rank <= self.limit


def normalise_initials(initials: str) -> str:
    """Upper case, three characters, padded if short.

    The same rule the browser client applies, so a name set in one place reads
    the same in the other.
    """
    cleaned = "".join(c for c in initials.upper() if c.isalnum())
    return (cleaned[:INITIALS_LENGTH] or "AAA").ljust(INITIALS_LENGTH, "A")


def data_dir() -> Path:
    """Where score files live, by platform.

    Worked out rather than taken from a library: this module has no
    dependencies, and the three rules below are the whole of what a
    dependency would do.
    """
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        return Path(override)

    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME")
        root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "magmacrunch"


class ScoreBook:
    """The scores for one game, on disk.

    ``game`` is the key the scoreboard is filed under, and should be the same
    key the browser build uses — ``george-boole``, ``moonlight-drift``,
    ``solitaire-thld`` — so that a shared board later means a shared board and
    not two boards with the same name.
    """

    def __init__(self, game: str, directory: Path | None = None,
                 limit: int = LIMIT):
        self.game = game
        self.limit = limit
        self._dir = Path(directory) if directory is not None else data_dir()

    @property
    def path(self) -> Path:
        return self._dir / "scores" / f"{self.game}.json"

    # -- Reading -----------------------------------------------------

    def load(self) -> list[ScoreEntry]:
        """Every kept score, best first.

        A file that cannot be read or parsed is treated as an empty board
        rather than an error. A corrupt scoreboard must not be able to stop
        somebody playing — losing a record is bad, refusing to start is worse.
        """
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(raw, list):
            return []

        entries = []
        for record in raw:
            if isinstance(record, dict):
                try:
                    entries.append(ScoreEntry.from_record(record))
                except (TypeError, ValueError):
                    continue
        return sorted(entries, key=lambda e: e.score, reverse=True)

    def top(self, count: int) -> list[ScoreEntry]:
        return self.load()[:count]

    def best(self) -> int:
        """The highest score on record, or 0 for an empty board."""
        entries = self.load()
        return entries[0].score if entries else 0

    def qualifies(self, score: int) -> bool:
        """Whether ``score`` would make the table as it stands.

        What a game asks before deciding to prompt for initials — nobody wants
        to be asked for their name to be told they came 213th.
        """
        entries = self.load()
        if len(entries) < self.limit:
            return True
        return score > entries[-1].score

    # -- Writing -----------------------------------------------------

    def save(self, initials: str, score: int, **extra) -> SaveResult:
        """Record a score and return where it landed."""
        entry = ScoreEntry(normalise_initials(initials), int(score), dict(extra))
        entries = self.load()
        entries.append(entry)
        entries.sort(key=lambda e: e.score, reverse=True)

        # Rank against the full list, not the truncated one, so a score outside
        # the table still gets a truthful answer rather than zero.
        rank = next(i for i, e in enumerate(entries, start=1) if e is entry)

        self._write(entries[:self.limit])
        return SaveResult(rank=rank, entry=entry, limit=self.limit)

    def clear(self) -> None:
        """Wipe the board. Used by tests and by a game that offers a reset."""
        self._write([])

    def _write(self, entries: list[ScoreEntry]) -> None:
        """Replace the file atomically.

        Written to a neighbouring temporary file and moved into place, so a
        crash or a full disk mid-write leaves the previous scoreboard intact
        rather than half a JSON document. ``os.replace`` is atomic on every
        platform this runs on.

        A failure to write is swallowed for the same reason a failure to read
        is: a read-only home directory should cost you the record, not the
        game.
        """
        path = self.path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps([e.to_record() for e in entries], indent=1)
            fd, tmp = tempfile.mkstemp(dir=str(path.parent),
                                       prefix=f".{self.game}-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                os.replace(tmp, path)
            except OSError:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
        except OSError:
            return


__all__ = ["DATA_DIR_ENV", "INITIALS_LENGTH", "LIMIT", "SaveResult",
           "ScoreBook", "ScoreEntry", "data_dir", "normalise_initials"]
