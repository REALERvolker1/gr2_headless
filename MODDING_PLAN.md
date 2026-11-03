# Modding route

The owned Steam game is app 2144740, build 16083277, UE4.27.2 Windows x64. `scripts/locate.py` discovers the host paths, and `lab.toml` pins the qualified executable hash. UE4SS v3.0.1 and GE-Proton10-25 provide the startup path and loader settings. Bounded reflection/serialization and motherboard capture are implemented in this harness.

The first route probe showed that a map argument on the shipping command line still reached MainMenu. A game-thread GameplayStatics.OpenLevel request then entered `/Game/Maps/TestLevels/Levels_Zoo`, possessed `BP_PlayerCharacter_C`, and exposed live kinematics/stamina. This is the current native initialization base.

No UE editor/cooker is installed. Use UE4SS to spawn measured collision geometry into this initialized world now. Preserve standalone cooked custom maps as the preferred future authoring route; try streamed-sublevel override if that route lacks native initialization. Custom maps and LogicMods are established community techniques, not research questions to reopen here.

The implementation is external and reversible. The game receives a private prefix, staged executable/mod directory, read-only original asset mounts, and copied saves. Runtime procedures and safety bounds are authoritative in `docs/runtime.md`; qualification status is in `docs/validation.md`.
