# Ground truth lab

First setup: run `python3 scripts/locate.py` to write the ignored `lab.toml`, then review it against `lab.example.toml`. It records the machine's Steam, game, Proton, prefix, and state paths plus the qualified executable hash.

For GR2 runtime experiments, save handling, or launch failures, read [docs/quickstart.md](docs/quickstart.md) before running the game. Use `scripts/lab.py` with the disposable prefix and private Gamescope display.

For geometry, instrumentation, or cooked-map extensions, read [docs/extending.md](docs/extending.md). Treat `harness/Scripts/areas.lua` as the geometry source of truth.

After changing Python or Lua, run the focused checks in `docs/extending.md`. After changing runtime behavior, run `scripts/validate.py`; completion requires game-thread acknowledgements, useful telemetry, and unchanged canonical save hashes. Preserve failed runs as evidence in ignored `.work/`; publish only curated output under `evidence/`.
