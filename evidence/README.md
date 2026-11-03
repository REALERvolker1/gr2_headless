# Published evidence

Curated output from the qualification run on 2026-10-13. Raw runs, logs, and
save-derived data stay under the ignored `.work/` directory; this directory is
the subset intended for readers.

Environment: Ghostrunner 2 app `2144740`, build `16083277`, UE4SS v3.0.1,
GE-Proton10-25, headless Gamescope 1280x720 at 60 Hz, Xdotool, and read-only
canonical mounts. The executable hash is pinned by `game_sha256` in `lab.toml`.

## `validation/`

Two complete launches from `python3 scripts/validate.py`.

- `results.json` — per-launch summary: areas, walk distance, sample counts,
  physics, wallrun, mouse yaw, and copied loadout.
- `1/`, `2/` — `areas.json` observations for all eight areas, the JSONL
  telemetry slice, and the runway screenshot.

Canonical SaveGames hashes were unchanged after both experiments and both
shutdowns.

## `wallrun/`

One named `wallrun` experiment from the same build: `result.json`, its
telemetry slice, and the screenshot taken at the wall.

Screenshots are lossy JPEG conversions of the captured PNGs; the originals are
in `.work/`. They contain Ghostrunner 2 imagery and are published only as test
evidence.

## Reproducing

```sh
python3 scripts/locate.py
python3 scripts/validate.py
```

The validator writes a fresh timestamped directory under `.work/validation/`.
Loader and launch logs are intentionally not published because they contain
host-specific absolute paths.
