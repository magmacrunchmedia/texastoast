# Contributing to texastoast

## Setup

```bash
git clone https://github.com/magmacrunchmedia/texastoast.git
cd texastoast
pip install -e ".[dev,sprites,hardware]"
```

`hardware` pulls in `smbus2` and only installs cleanly on Linux; skip it unless
you are working on the I2C layer. Without it, `I2CBus` runs in mock mode and
everything else still works.

## Tests

```bash
pytest
```

Some tests drive a real tkinter canvas — the renderer, the game loop, the tile
editor. They skip automatically when no display is available, so a green run on
a headless machine does not mean those tests passed. CI runs them under `xvfb`
on Linux so they actually execute.

Run a single area:

```bash
pytest tests/test_collision.py -v
```

## Lint

```bash
ruff check .
ruff check . --fix
```

CI runs `ruff check .` and fails on any finding.

## Conventions

- `speed` and velocities are in **pixels per second**; anything taking a
  per-frame step takes `dt` explicitly. Do not reintroduce per-frame movement.
- Errors that mean "the hardware is not there" must be distinguishable from
  valid zero data. Return `None`, do not fabricate a zero buffer.
- Every bug fix gets a regression test that fails against the old behavior, with
  a comment naming what used to go wrong.

## Releasing

Releases are published to PyPI by GitHub Actions, using the same
`PYPI_API_TOKEN` secret as the other magmacrunch packages.

1. Update `CHANGELOG.md` — move the unreleased section under the new version.
2. Bump `__version__` in `texastoast/__init__.py`. That is the single source of
   truth; `pyproject.toml` reads it via `[tool.hatch.version]`.
3. Commit, then tag:

   ```bash
   git tag v0.2.0 && git push origin main --tags
   ```

4. The release workflow builds the sdist and wheel, verifies the tag matches
   `__version__`, and publishes.

The workflow also verifies the tag matches `__version__`, publishes with
`skip-existing`, and opens a GitHub Release with generated notes.

### PyPI credentials

Publishing uses the `PYPI_API_TOKEN` secret. If it is an organization-level
secret it is already available here; if it is scoped to a single repository, add
it to texastoast's secrets too. The PyPI token itself must be account-scoped, or
scoped to include the texastoast project — a token scoped only to another
project will fail with a 403.
