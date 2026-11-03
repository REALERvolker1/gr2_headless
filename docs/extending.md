# Extending the lab

## Geometry

Edit `harness/Scripts/areas.lua`. Each area has a start position and boxes with absolute X/Z, lane-relative Y, and explicit centimeter sizes. The runtime cube is 100 cm per side; the builder divides requested dimensions by 100 for scale. Collision blocks every channel. Add a new lane with enough separation for its geometry, and a start 100 cm above its floor top.

Stop and launch again to deploy edits. `enter` copies no files; `launch` installs the current source into private staging. Use `build` to reconstruct geometry during a run. Record an observation after settling and a screenshot before calling a new area qualified. For wallrun, grapple, or combat qualification, also demonstrate the relevant native movement or AI state. Collision alone is insufficient.

## Measurements

Add scalar state fields to the selection in `main.lua`. The reader checks reflected declarations, including ancestors, before accessing a field. Missing declarations remain absent. Keep exact native getters explicit; add signature evidence and a focused live check before introducing one.

Use `copy.lua` only for declared, bounded structs/arrays. Avoid recursive arbitrary UObject traversal. That caused freezes in prior recorder work. Keep broad function hooks disabled until individually qualified. Report sampled state changes as polling observations, not exact engine events.

A new experiment must reset to a stated start, define its physical input sequence, record the copied loadout and build identity, and assert a useful measured result. Extend `experiment` and the focused validator together.

## Cooked maps and LogicMods

The authoring route is known. This host lacks a UE4.27 cooker/editor, so the current implementation uses external runtime geometry. The next preferred extension is a cooked standalone world that preserves native player/game-mode references, with streamed-sublevel replacement as the fallback if native initialization fails.

Cook for WindowsNoEditor with the installed game's engine version, UE4.27.2. Keep the Unreal authoring project, imported proprietary assets, cooked packages, and keys in ignored private storage. Use a unique `/Game/GroundTruth/...` package path. Blueprint references to original classes must retain their original package names; validate against the owned game's package inventory rather than copying inferred classes into a parallel gameplay implementation.

When you have a cooked pak:

1. Stop the lab, run `prepare` to create its private Content/Paks view, then `lab.py mount /path/to/map.pak`. A matching `.sig` is copied if supplied. Mounting refuses to overwrite an existing pak.
2. Launch normally. Request `cmd travel /Game/GroundTruth/YourMap` and poll `status` until the expected world and real Jack are present.
3. Prove movement, collision, stamina, and reset behavior. If initialization fails, override a stock streamed test sublevel while keeping its persistent world. Put the replacement pak only in private staging.
4. For a LogicMod, add a compatible loader to the staged Mods load order and prove its explicit ready event. Keep installed source files untouched.

`docs/validation.md` is the status record. Update it with observed evidence after qualification, including failures that constrain the next route. The project does not claim that a hand-written uncooked map or a pak filename alone is runnable.

Relevant primary references: [UE4SS v3.0.1 API/source](https://github.com/UE4SS-RE/RE-UE4SS/tree/v3.0.1), [GR2 DML author page](https://www.nexusmods.com/ghostrunner2/mods/5), and [the mod author's Blueprint/LogicMod guide](https://github.com/Dmgvol/GR_Guides/blob/main/ModLoaderExample.md). The latter is a Ghostrunner guide; qualify GR2-specific assumptions in this lab.

## Checks

```sh
ruff check scripts tests
ruff format --check scripts tests
mypy --strict scripts tests
stylua --check harness/Scripts
lua-language-server --check=harness/Scripts --checklevel=Warning
python3 -m unittest discover -s tests
python3 scripts/validate.py
```

Run static checks and focused isolation tests for script changes. Runtime geometry, reflected API, input, and lifecycle changes also require the validator. Its two launches are deliberately bounded; it stops the owned lab even if qualification fails.
