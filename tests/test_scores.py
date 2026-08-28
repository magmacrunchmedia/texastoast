"""High scores on disk.

Every test points the scorebook at a tmp_path, so nothing here can read or
write a real player's records — a suite that could lose somebody's high scores
is not one you want to run twice.

The behaviours pinned here are the ones the browser client already has, because
matching it is what makes a future sync additive rather than a translation.
"""

from __future__ import annotations

import json

import pytest

from texastoast import scores


@pytest.fixture
def book(tmp_path):
    return scores.ScoreBook("test-game", directory=tmp_path)


# ── Initials ────────────────────────────────────────────────────────


@pytest.mark.parametrize("given,expected", [
    ("jam", "JAM"),
    ("JAM", "JAM"),
    ("jamie", "JAM"),
    ("j", "JAA"),
    ("", "AAA"),
    ("j@m!", "JMA"),
    ("  ", "AAA"),
])
def test_initials_are_three_upper_case_characters(given, expected):
    """The same rule the browser client applies, so a name set in one place
    reads the same in the other."""
    assert scores.normalise_initials(given) == expected


# ── An empty board ──────────────────────────────────────────────────


def test_a_board_with_no_file_is_empty_rather_than_an_error(book):
    assert book.load() == []
    assert book.best() == 0
    assert not book.path.exists()


def test_anything_qualifies_for_an_empty_board(book):
    assert book.qualifies(1)
    assert book.qualifies(0)


# ── Saving and loading ──────────────────────────────────────────────


def test_a_score_survives_being_written_and_read_back(book):
    book.save("jam", 500)
    assert [(e.initials, e.score) for e in book.load()] == [("JAM", 500)]


def test_a_second_book_on_the_same_file_sees_the_same_scores(tmp_path):
    """The whole point: the record outlives the process."""
    scores.ScoreBook("test-game", directory=tmp_path).save("jam", 500)
    reopened = scores.ScoreBook("test-game", directory=tmp_path)
    assert reopened.best() == 500


def test_scores_come_back_best_first(book):
    for initials, score in (("aaa", 10), ("bbb", 900), ("ccc", 400)):
        book.save(initials, score)
    assert [e.score for e in book.load()] == [900, 400, 10]


def test_extra_is_stored_alongside_the_score(book):
    """A game remembers the mode or the character, not just the number."""
    book.save("jam", 120, mode="gauntlet", pilot="fire-toad")
    entry = book.load()[0]
    assert entry.extra == {"mode": "gauntlet", "pilot": "fire-toad"}


def test_extra_is_flattened_into_the_record_the_way_the_web_stores_it(book):
    book.save("jam", 120, mode="byte")
    written = json.loads(book.path.read_text(encoding="utf-8"))
    assert written == [{"initials": "JAM", "score": 120, "mode": "byte"}]


def test_two_games_keep_separate_boards(tmp_path):
    scores.ScoreBook("one", directory=tmp_path).save("aaa", 10)
    scores.ScoreBook("two", directory=tmp_path).save("bbb", 20)
    assert scores.ScoreBook("one", directory=tmp_path).best() == 10
    assert scores.ScoreBook("two", directory=tmp_path).best() == 20


# ── Rank ────────────────────────────────────────────────────────────


def test_rank_is_one_based(book):
    assert book.save("jam", 100).rank == 1


def test_rank_places_a_score_among_the_others(book):
    book.save("aaa", 300)
    book.save("bbb", 100)
    assert book.save("ccc", 200).rank == 2


def test_rank_is_counted_against_every_score_not_just_the_kept_ones(tmp_path):
    """Indexing into the truncated list would report 0 for anything that
    missed the table, which is not an answer."""
    book = scores.ScoreBook("test-game", directory=tmp_path, limit=3)
    for i in range(3):
        book.save("aaa", 1000 + i)
    result = book.save("zzz", 1)
    assert result.rank == 4
    assert not result.made_the_table


def test_a_tie_does_not_displace_the_score_already_there(book):
    book.save("aaa", 100)
    assert book.save("bbb", 100).rank == 2


# ── The limit ───────────────────────────────────────────────────────


def test_only_the_top_scores_are_kept(tmp_path):
    book = scores.ScoreBook("test-game", directory=tmp_path, limit=3)
    for i in range(10):
        book.save("aaa", i)
    kept = book.load()
    assert len(kept) == 3
    assert [e.score for e in kept] == [9, 8, 7]


def test_qualifies_says_no_once_the_table_is_full_of_better_scores(tmp_path):
    book = scores.ScoreBook("test-game", directory=tmp_path, limit=3)
    for score in (300, 200, 100):
        book.save("aaa", score)
    assert not book.qualifies(50)
    assert not book.qualifies(100), "a tie with last place does not make it"
    assert book.qualifies(150)


def test_the_default_limit_is_the_web_clients_hundred():
    assert scores.LIMIT == 100


# ── Not losing the game over a scoreboard ───────────────────────────


def test_a_corrupt_file_reads_as_an_empty_board(book):
    book.path.parent.mkdir(parents=True, exist_ok=True)
    book.path.write_text("{ this is not json", encoding="utf-8")
    assert book.load() == []


def test_a_file_holding_the_wrong_shape_reads_as_empty(book):
    book.path.parent.mkdir(parents=True, exist_ok=True)
    book.path.write_text('{"scores": []}', encoding="utf-8")
    assert book.load() == []


def test_one_bad_row_does_not_lose_the_rest(book):
    book.path.parent.mkdir(parents=True, exist_ok=True)
    book.path.write_text(json.dumps([
        {"initials": "AAA", "score": 10},
        "not a record",
        {"initials": "BBB", "score": 20},
    ]), encoding="utf-8")
    assert [e.score for e in book.load()] == [20, 10]


def test_saving_over_a_corrupt_file_recovers_the_board(book):
    book.path.parent.mkdir(parents=True, exist_ok=True)
    book.path.write_text("garbage", encoding="utf-8")
    book.save("jam", 42)
    assert book.best() == 42


def test_a_directory_that_cannot_be_written_costs_the_record_not_the_game(
        tmp_path, monkeypatch):
    """A read-only home should not be able to stop somebody playing."""
    book = scores.ScoreBook("test-game", directory=tmp_path)

    def refuse(*args, **kwargs):
        raise OSError("read-only")

    monkeypatch.setattr("pathlib.Path.mkdir", refuse)
    book.save("jam", 10)          # must not raise
    assert book.load() == []


# ── Where files live ────────────────────────────────────────────────


def test_the_environment_can_move_the_data_directory(tmp_path, monkeypatch):
    monkeypatch.setenv(scores.DATA_DIR_ENV, str(tmp_path))
    assert scores.data_dir() == tmp_path


def test_the_data_directory_is_under_the_family_name(monkeypatch):
    monkeypatch.delenv(scores.DATA_DIR_ENV, raising=False)
    assert scores.data_dir().name == "magmacrunch"


def test_a_board_files_itself_under_its_game_key(tmp_path):
    book = scores.ScoreBook("moonlight-drift", directory=tmp_path)
    assert book.path.name == "moonlight-drift.json"
    assert book.path.parent.name == "scores"


# ── The seam a sync would use ───────────────────────────────────────


def test_a_saved_score_is_not_claimed_to_be_synced(book):
    """There is no server to reach yet, and saying otherwise would make the
    flag useless the day there is one."""
    assert book.save("jam", 10).synced is False


def test_an_entry_round_trips_through_its_record(book):
    entry = scores.ScoreEntry("JAM", 10, {"mode": "byte"})
    assert scores.ScoreEntry.from_record(entry.to_record()) == entry


def test_clearing_empties_the_board(book):
    book.save("jam", 10)
    book.clear()
    assert book.load() == []


def test_the_module_needs_nothing_outside_the_standard_library():
    """It is imported by games that have no dependencies, and by the engine
    without its terminal extra."""
    import subprocess
    import sys

    code = ("import sys, texastoast.scores; "
            "print([m for m in sys.modules if m in ('textual', 'rich')])")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, check=True)
    assert out.stdout.strip() == "[]", out.stdout
