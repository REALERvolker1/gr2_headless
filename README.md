# Ghostrunner 2 Headless Modding Environment

# WARNING: This project is entirely AI generated

Run the owned GR2 implementation through headless Gamescope and Xdotool, with UE4SS commands for travel, measured geometry, player reset, spawning, and JSONL telemetry. Each launch starts with a disposable copy of the campaign save. Game files and the canonical save are mounted read-only inside the game process.

## Setup

No machine-specific path is committed. Generate the ignored `lab.toml` from this host:

```sh
python3 scripts/locate.py
```

`locate.py` does the discovery:

- Scans native Steam (`~/.steam`, `~/.local/share/Steam`) and Flatpak Steam (`~/.var/app/com.valvesoftware.Steam/data/Steam` and the older `.../.local/share/Steam` variant).
- Reads every library listed in `steamapps/libraryfolders.vdf`, including secondary drives.
- Finds Ghostrunner 2 and its `steamapps/compatdata/2144740` prefix.
- Prefers GE-Proton, then other custom tools, then stock Proton.
- Chooses the lab state directory from `$XDG_STATE_HOME/gr2_headless`, falling back to `~/.local/state/gr2_headless`.
- Hashes `Ghostrunner2-Win64-Shipping.exe` and writes `game_sha256` only when it matches the qualified build in [`lab.example.toml`](lab.example.toml); otherwise it leaves the value empty so `prepare` refuses an unqualified build.

Review the generated file against [`lab.example.toml`](lab.example.toml) before running. Rerun with `--force` after moving a Steam library.

[Agent quickstart](docs/quickstart.md) gives the run sequence. [Architecture and save isolation](docs/runtime.md) explains the boundaries. [Extensions](docs/extending.md) covers geometry, measurements, and cooked maps. [Validation](docs/validation.md) distinguishes tested behavior from remaining work.

The current environment is a runtime graybox built inside the game's cooked `Levels_Zoo` world. It uses the real `BP_PlayerCharacter_C`, native movement, stamina, and copied motherboard loadout. It contains runway, gaps, walls, terrain, grapple, combat, resources, and physics areas. This repository does not yet contain a cooked custom `.umap`.

An agent implementing GR2 elsewhere can link `docs/quickstart.md` from its project's AGENTS.md, run an experiment here, and compare its own implementation against the recorded positions, velocities, states, and resources. Use the same copied loadout and input sequence. A mismatch is evidence to investigate, not permission to replace native behavior with a guessed formula.

Published qualification output is in [evidence](evidence/README.md). Raw runs, logs, and saves stay in the ignored `.work/` directory.

## License

MIT. See [LICENSE.txt](LICENSE.txt).
