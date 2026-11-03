# Agent quickstart

Use this repository when you need observations from the real GR2 implementation, including movement, resource costs, geometry interactions, or native actor spawning.

## Prerequisites

- Owned GR2 Steam installation, qualified build `16083277`. `game_sha256` in `lab.toml` pins the exact executable.
- Linux user systemd manager, Vulkan-capable GPU, Gamescope headless backend, Xdotool, Bubblewrap, ImageMagick, Python 3.11 or newer.
- GE-Proton10-25, or another Proton launcher. `scripts/locate.py` prefers GE-Proton and searches native Steam, Flatpak Steam, and every library in `libraryfolders.vdf`.
- UE4SS v3.0.1 loader in the source Win64 tree. `prepare` copies it into private staging.
- A signed-in Steam client for the game's Steam API. `steam-start` can start the existing client on its own headless display and waits for its login acknowledgement; it does not submit a Steam game-launch request.

Run `python3 scripts/locate.py` once to write the ignored `lab.toml`, then review it against [`lab.example.toml`](../lab.example.toml). Rerun with `--force` after moving a Steam library. `locate.py` sets `seed_prefix` to the canonical prefix; it is used only as a copy source for the disposable lab prefix. It writes `game_sha256` only for the qualified executable; otherwise it leaves the value empty and `prepare` refuses to run until the build is qualified. Runtime files live on local disk at its `state` path because a Wine prefix on a network filesystem was unreliable in prior work.

## Run

From this directory:

```sh
python3 scripts/locate.py
python3 scripts/lab.py prepare
python3 scripts/lab.py steam-start
python3 scripts/lab.py launch
python3 scripts/lab.py enter
python3 scripts/lab.py experiment walk
python3 scripts/lab.py experiment wallrun
python3 scripts/lab.py stop
```

`enter` waits for the menu controller, requests Unreal travel, waits for a possessed real Jack, builds the graybox, and teleports Jack to the runway. Success reports area actor counts. No menu selection is part of this sequence. `experiment` prints a run directory under `.work/runs/` containing `result.json`, `telemetry.jsonl`, loader log, and a screenshot. `stop` terminates only the lab prefix and its game/display services, then reports `canonical_unchanged: true`.

For repeated qualification, run `python3 scripts/validate.py`. Success requires two complete launches with useful traces and unchanged save hashes.

## One controlled experiment

```sh
python3 scripts/lab.py cmd teleport walls
python3 scripts/lab.py cmd reset
python3 scripts/lab.py cmd observe
python3 scripts/lab.py cmd record_start
python3 scripts/lab.py key w 1
python3 scripts/lab.py cmd record_stop
python3 scripts/lab.py capture .work/walls.png
```

Use `cmd status` to check readiness. A command succeeds only after the game thread acknowledges it. Read `scripts/lab.py --help` for lifecycle operations and [runtime.md](runtime.md) for game-side command semantics and safety boundaries.

## Failure

Preserve `.work/runs/` and the configured state directory. Publish curated output under `evidence/`, not raw logs. Inspect `launch.log`, `steam-2144740.log`, and staged `UE4SS.log`. Inspect the services with `journalctl --user -u gr2-groundtruth -u gr2-groundtruth-game`. Run `stop` before changing a prefix, save fixture, or loader. A timeout or living process does not establish that an environment is usable.

Canonical save hash failures block further resets. Investigate the outside writer before accepting a new baseline. Use only the copied saves for experiments; never point `state` or the staged prefix at Steam's canonical prefix.
