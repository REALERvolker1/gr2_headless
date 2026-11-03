#!/usr/bin/env python3
"""Qualify two independent GR2 launches, geometry, input, telemetry and saves."""

from __future__ import annotations

import argparse
import fcntl
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import lab  # noqa: E402


def number(value: object) -> float:
    if not isinstance(value, (float, int)) or isinstance(value, bool):
        raise TypeError(f"Expected numeric measurement, received {value}")
    return float(value)


def mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Expected measurement object")
    return {str(key): item for key, item in value.items()}


def rows(path: Path) -> list[dict[str, object]]:
    return [mapping(json.loads(line)) for line in path.read_text().splitlines()]


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    config = lab.Config.load()
    config.state.mkdir(parents=True, exist_ok=True)
    with (config.state / "control.lock").open("w") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lab.steam_start(config)
        lab.prepare(config)
        output = lab.ROOT / ".work/validation" / str(time.time_ns())
        output.mkdir(parents=True)
        results: list[dict[str, object]] = []
        for iteration in range(2):
            run = output / str(iteration + 1)
            run.mkdir()
            try:
                lab.start(config)
                lab.enter(config)
                status = lab.result(lab.request(config, ["status"]))
                assert "BP_PlayerCharacter_C" in str(status["pawn"]), status
                build = lab.result(lab.request(config, ["build"]))
                areas = mapping(build["areas"])
                observations: dict[str, object] = {}
                for area in sorted(areas):
                    lab.request(config, ["teleport", area])
                    time.sleep(0.25)
                    snapshot = lab.result(lab.request(config, ["observe"]))
                    position = mapping(snapshot["position"])
                    assert abs(number(position["z"]) - 10098.15) < 1, snapshot
                    assert number(snapshot["movement_mode"]) == 1, snapshot
                    observations[area] = snapshot
                lab.write_json(run / "areas.json", observations)
                lab.request(config, ["teleport", "runway"])
                lab.request(config, ["reset"])
                time.sleep(0.3)
                before = lab.result(lab.request(config, ["observe"]))
                lab.request(config, ["record_start"])
                lab.input_key(config, "w", 1)
                after = lab.result(lab.request(config, ["observe"]))
                lab.request(config, ["record_stop"])
                distance = number(mapping(after["position"])["x"]) - number(
                    mapping(before["position"])["x"]
                )
                assert distance > 100, (before, after)
                samples = rows(config.bin / "gt.telemetry.jsonl")
                assert len(samples) >= 5, samples
                assert max(number(mapping(row["velocity"])["x"]) for row in samples) > 100
                loadout = lab.result(lab.request(config, ["upgrades"]))
                assert "motherboard" in loadout, loadout
                look_before = mapping(after["control_rotation"])
                lab.mouse(config, 100, 0)
                time.sleep(0.2)
                look_after = mapping(
                    lab.result(lab.request(config, ["observe"]))["control_rotation"]
                )
                assert abs(number(look_after["yaw"]) - number(look_before["yaw"])) > 0.1, (
                    look_before,
                    look_after,
                )
                lab.capture(config, run / "runway.png")
                (run / "telemetry.jsonl").write_text(
                    (config.bin / "gt.telemetry.jsonl").read_text()
                )
                (run / "UE4SS.log").write_bytes((config.bin / "UE4SS.log").read_bytes())
                physics_before = lab.result(lab.request(config, ["physics"]))
                time.sleep(0.25)
                physics_after = lab.result(lab.request(config, ["physics"]))
                assert (
                    abs(
                        number(mapping(physics_after["platform"])["x"])
                        - number(mapping(physics_before["platform"])["x"])
                    )
                    > 1
                )
                assert abs(number(mapping(physics_after["cube"])["z"]) - 10050) < 5, physics_after
                lab.experiment(config, "wallrun")
                lab.verify(config)
                results.append(
                    {
                        "launch": iteration + 1,
                        "areas": list(areas),
                        "pawn": status["pawn"],
                        "walk_cm": distance,
                        "samples": len(samples),
                        "canonical_unchanged": True,
                        "physics": physics_after,
                        "wallrun_observed": True,
                        "mouse_yaw_before": look_before["yaw"],
                        "mouse_yaw_after": look_after["yaw"],
                        "upgrades": loadout,
                    }
                )
                lab.write_json(output / "results.json", results)
            except Exception as failure:
                for source in (
                    config.bin / "UE4SS.log",
                    config.state / "launch.log",
                    config.state / "steam-2144740.log",
                ):
                    if source.exists():
                        shutil.copy2(source, run / source.name)
                lab.write_json(run / "failure.json", {"error": str(failure)})
                raise
            finally:
                lab.stop(config)
        print(output)


if __name__ == "__main__":
    main()
