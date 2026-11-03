# Validation record

Qualified on 2026-10-13 using the configured Steam build 16083277, UE4SS v3.0.1, GE-Proton10-25, headless Gamescope 1280x720 at 60 Hz, Xdotool, and read-only canonical mounts. The shipping binary hash is pinned as `game_sha256` in `lab.toml`; a different build is unqualified until that value is updated and the validator passes again.

The final two-launch run is published in [`evidence/validation/`](../evidence/validation/) (see the [evidence README](../evidence/README.md)): `results.json`, per-launch area observations, JSONL traces, and screenshots. A named wallrun experiment is in [`evidence/wallrun/`](../evidence/wallrun/). Loader logs and earlier failed/probing runs stay under ignored `.work/` or the private state directory.

| Requirement | Observed result |
| --- | --- |
| Automatic launch | Two fresh service-owned Proton launches reached the menu and acknowledged commands |
| Entry without New Game | Game-thread OpenLevel reached Levels_Zoo; no Play/New Game menu input |
| Real player | Possessed native-derived `BP_PlayerCharacter_C`; advancing clocks, native stamina, movement and state observations |
| Custom test areas | Eight authored areas rebuilt on both launches; 38 fixture actors; Jack settled at Z=10098.15 cm at every start with walking movement mode |
| Scripted movement | One-second W experiment moved 940.520 cm and 934.272 cm; runs captured 23 and 25 samples with positive native velocity |
| Wall geometry | Named wallrun experiment observed native `bOnWall=true` on both launches |
| Relative mouse input | Xdotool +100 X motion changed native control yaw from zero to 31.781 and 31.544 degrees |
| Physics area | Native simulated cube settled at Z=10050 cm; platform changed X between observations on both launches |
| Save isolation | All five canonical SaveGames files retained their SHA-256 hashes after both experiments and both shutdowns |

A cold Steam restart exposed an early-launch failure before client login. `steam-start` now waits for the client login acknowledgement, and failure cleanup stops display/game units independently when a failed game unit has already been collected. The failed probe stays in ignored `.work/failures/steam-not-ready/`.

Additional probes qualified `set_stamina` through its native float/bool signature, captured all five motherboard branches and 20 raw socket records, and spawned native pistol, Shinobi, and grapple actors. A dash probe moved about 1635 cm and sampled stamina down to about 56. A jump probe reached about 205 cm above its resting height. These are examples from timed inputs with the copied loadout, not deterministic reference constants.

The focused Python tests pass for disposable writes/reset, escaping save junction rejection, preservation of the prior hash baseline after an outside canonical change, display cleanup when the failed game service is already absent, and Steam discovery across secondary and Flatpak libraries. Ruff, strict mypy, StyLua, and Lua language-server checks pass.

## Remaining qualification

Standalone custom cooked maps and streamed-sublevel replacements are future routes, not completed deliverables. No UE editor/cooker exists on this host. The working route is measured runtime geometry inside a qualified cooked stock test world.

Complete grapple traversal, full enemy AI/combat in the elevated arena, rail-specific native mechanics, memory-card pickup behavior, arbitrary upgrade application, moving-platform passenger behavior, and complete latent-state reset remain unqualified. Spawn identity, floor collision, or a polled state flag does not establish those behaviors. Read `runtime.md` before using results as a parity oracle.
