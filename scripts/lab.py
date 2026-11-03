#!/usr/bin/env python3
"""Disposable GR2 lab lifecycle and synchronous command bridge."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import shutil
import subprocess
import time
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "lab.toml"
SAVE = Path("pfx/drive_c/users/steamuser/AppData/Local/Ghostrunner2/Saved")


@dataclass(frozen=True)
class Config:
    game: Path
    proton: Path
    seed_prefix: Path
    canonical_prefix: Path
    steam: Path
    state: Path
    game_sha256: str

    @classmethod
    def load(cls) -> Config:
        if not CONFIG.exists():
            raise RuntimeError("Missing lab.toml; run `python3 scripts/locate.py` first")
        with CONFIG.open("rb") as stream:
            data = tomllib.load(stream)
        paths = {
            key: Path(str(data[key])).expanduser().resolve()
            for key in (
                "game",
                "proton",
                "seed_prefix",
                "canonical_prefix",
                "steam",
                "state",
            )
        }
        return cls(**paths, game_sha256=str(data["game_sha256"]).lower())

    @property
    def bin(self) -> Path:
        return self.state / "game/Ghostrunner2/Binaries/Win64"

    @property
    def prefix(self) -> Path:
        return self.state / "compatdata"


def run(
    command: list[str],
    *,
    env: Mapping[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, text=True, env=env, capture_output=capture_output)


def hashes(path: Path) -> dict[str, str]:
    return {
        str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.rglob("*"))
        if p.is_file()
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n")


def check_stopped(c: Config) -> None:
    if (
        subprocess.run(
            ["systemctl", "--user", "is-active", "--quiet", "gr2-groundtruth"],
            check=False,
        ).returncode
        == 0
    ):
        raise RuntimeError("Lab display is already running; stop it before resetting")
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                executable = (entry / "cmdline").read_bytes().split(b"\0", 1)[0]
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
            if executable.endswith(b"Ghostrunner2-Win64-Shipping.exe"):
                raise RuntimeError("Close GR2 before preparing or resetting the lab")
    validate_paths(c)


def validate_paths(c: Config) -> None:
    if (
        c.prefix.resolve().is_relative_to(c.canonical_prefix)
        or c.state.is_relative_to(c.seed_prefix)
        or c.seed_prefix.is_relative_to(c.state)
        or c.state.is_relative_to(c.game)
        or c.game.is_relative_to(c.state)
        or c.canonical_prefix.is_relative_to(c.state)
        or ROOT == c.state
        or not c.bin.resolve().is_relative_to(c.state)
    ):
        raise RuntimeError(
            "Runtime state must be separate from the canonical and seed prefixes and repository"
        )


def prepare(c: Config) -> None:
    check_stopped(c)
    binary = c.game / "Ghostrunner2/Binaries/Win64/Ghostrunner2-Win64-Shipping.exe"
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    if digest != c.game_sha256:
        raise RuntimeError(
            "Unqualified GR2 build: executable hash does not match lab.toml. "
            f"Found {digest}; qualify travel and reflection, then set game_sha256. "
            "lab.example.toml records the currently qualified hash"
        )
    c.state.mkdir(parents=True, exist_ok=True)
    if not (c.prefix / "pfx").exists():
        shutil.copytree(c.seed_prefix, c.prefix, symlinks=True)
    game = c.state / "game"
    if not c.bin.exists():
        c.bin.mkdir(parents=True)
        source = c.game / "Ghostrunner2/Binaries/Win64"
        for p in source.iterdir():
            if p.is_file() and (
                p.suffix.lower() in (".dll", ".exe", ".ini") or p.name == "steam_appid.txt"
            ):
                shutil.copy2(p, c.bin / p.name)
            elif p.is_dir() and p.name in (
                "UE4SS_Signatures",
                "CustomGameConfigs",
                "MemberVarLayoutTemplates",
                "VTableLayoutTemplates",
                "RedpointEOS",
            ):
                shutil.copytree(p, c.bin / p.name)
        (game / "Engine").symlink_to(c.game / "Engine", target_is_directory=True)
        for name in ("Plugins",):
            (game / "Ghostrunner2" / name).symlink_to(
                c.game / "Ghostrunner2" / name, target_is_directory=True
            )
    content = game / "Ghostrunner2/Content"
    if content.is_symlink():
        content.unlink()
    content.mkdir(exist_ok=True)
    for source in (c.game / "Ghostrunner2/Content").iterdir():
        destination = content / source.name
        if source.name == "Paks":
            destination.mkdir(exist_ok=True)
            for pak in source.iterdir():
                if not (destination / pak.name).exists():
                    (destination / pak.name).symlink_to(pak, target_is_directory=pak.is_dir())
        elif not destination.exists():
            destination.symlink_to(source, target_is_directory=source.is_dir())
    mods = c.bin / "Mods"
    mods.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "harness", mods / "GroundTruth", dirs_exist_ok=True)
    (mods / "mods.txt").write_text("GroundTruth : 1\n")
    reset_saves(c)
    print(c.state)


def reset_saves(c: Config) -> None:
    check_stopped(c)
    if (c.state / "canonical-before.json").exists():
        verify(c)
    canonical = c.canonical_prefix / SAVE
    destination = c.prefix / SAVE
    # A copied prefix may retain host junctions. Resolve before touching any save.
    if not destination.resolve().is_relative_to(c.prefix):
        raise RuntimeError(f"Lab save resolves outside its prefix: {destination.resolve()}")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(canonical, destination, symlinks=False)
    write_json(c.state / "canonical-before.json", hashes(canonical / "SaveGames"))


def verify(c: Config) -> None:
    before: object = json.loads((c.state / "canonical-before.json").read_text())
    after = hashes(c.canonical_prefix / SAVE / "SaveGames")
    if before != after:
        raise RuntimeError("Canonical save hashes changed; preserve evidence and investigate")
    print(json.dumps({"canonical_unchanged": True, "files": len(after)}))


def start(c: Config) -> None:
    check_stopped(c)
    reset_saves(c)
    shutil.copytree(ROOT / "harness", c.bin / "Mods/GroundTruth", dirs_exist_ok=True)
    for pattern in ("gt.request", "gt.reply", "gt.telemetry.jsonl"):
        (c.bin / pattern).unlink(missing_ok=True)
    unit = "gr2-groundtruth"
    display_file = c.state / "display"
    display_file.unlink(missing_ok=True)
    # A fixed private Gamescope display is owned by this transient user service.
    run(
        [
            "systemd-run",
            "--user",
            "--unit=" + unit,
            "--collect",
            "--property=WorkingDirectory=" + str(c.state),
            "--setenv=GT_DISPLAY_FILE=" + str(display_file),
            "/usr/bin/gamescope",
            "--backend",
            "headless",
            "-w",
            "1280",
            "-h",
            "720",
            "-W",
            "1280",
            "-H",
            "720",
            "-r",
            "60",
            "--",
            "/bin/sh",
            "-c",
            'echo "$DISPLAY" > "$GT_DISPLAY_FILE"; exec sleep infinity',
        ]
    )
    deadline = time.monotonic() + 30
    while not display_file.exists():
        if time.monotonic() > deadline:
            raise RuntimeError(
                "Gamescope did not publish a display; inspect journalctl --user -u gr2-groundtruth"
            )
        time.sleep(0.1)
    env = os.environ.copy()
    for key in (
        "WINEPREFIX",
        "WAYLAND_DISPLAY",
        "PROTON_ENABLE_WAYLAND",
        "PROTON_USE_WAYLAND",
        "SDL_VIDEODRIVER",
    ):
        env.pop(key, None)
    env.update(
        DISPLAY=display_file.read_text().strip(),
        STEAM_COMPAT_DATA_PATH=str(c.prefix),
        STEAM_COMPAT_CLIENT_INSTALL_PATH=str(c.steam),
        SteamAppId="2144740",
        SteamGameId="2144740",
        WINEDLLOVERRIDES="dwmapi=n,b;dxgi,d3d11=n",
        PROTON_LOG="1",
        PROTON_LOG_DIR=str(c.state),
    )
    command = [
        "bwrap",
        "--dev-bind",
        "/",
        "/",
        "--ro-bind",
        str(c.canonical_prefix),
        str(c.canonical_prefix),
        "--ro-bind",
        str(c.game),
        str(c.game),
    ]
    userdata = c.steam / "userdata"
    if userdata.exists():
        command += ["--ro-bind", str(userdata), str(userdata)]
    command += [
        "--",
        str(c.proton),
        "runinprefix",
        str(c.bin / "Ghostrunner2-Win64-Shipping.exe"),
    ]
    command += ["-dx11", "-windowed", "-ResX=1280", "-ResY=720", "-nosplash"]
    service = [
        "systemd-run",
        "--user",
        "--unit=gr2-groundtruth-game",
        "--collect",
        "--property=WorkingDirectory=" + str(c.bin),
        "--property=TimeoutStopSec=10",
        "--property=StandardOutput=append:" + str(c.state / "launch.log"),
        "--property=StandardError=append:" + str(c.state / "launch.log"),
    ]
    for key in (
        "DISPLAY",
        "STEAM_COMPAT_DATA_PATH",
        "STEAM_COMPAT_CLIENT_INSTALL_PATH",
        "SteamAppId",
        "SteamGameId",
        "WINEDLLOVERRIDES",
        "PROTON_LOG",
        "PROTON_LOG_DIR",
    ):
        service.append("--setenv=" + key + "=" + env[key])
    service += [
        "--property=UnsetEnvironment=WAYLAND_DISPLAY WINEPREFIX "
        "PROTON_ENABLE_WAYLAND PROTON_USE_WAYLAND SDL_VIDEODRIVER"
    ]
    run(service + command)
    write_json(c.state / "launch.json", {"command": command, "display": env["DISPLAY"]})
    print(json.dumps({"display": env["DISPLAY"]}))


def display(c: Config) -> dict[str, str]:
    return {**os.environ, "DISPLAY": (c.state / "display").read_text().strip()}


def window(c: Config) -> str:
    result = run(
        ["xdotool", "search", "--name", "^Ghostrunner2  *$"],
        env=display(c),
        capture_output=True,
    )
    return result.stdout.strip().splitlines()[-1]


def focus(c: Config) -> None:
    wid = window(c)
    console = subprocess.run(
        ["xdotool", "search", "--name", "^Z:.*Ghostrunner2-Win64-Shipping.exe$"],
        env=display(c),
        text=True,
        capture_output=True,
        check=False,
    )
    for identifier in console.stdout.splitlines():
        run(["xdotool", "windowunmap", identifier], env=display(c))
    run(["xdotool", "windowmap", wid], env=display(c))
    run(["xdotool", "windowfocus", "--sync", wid], env=display(c))


def input_key(c: Config, key: str, seconds: float) -> None:
    if not math.isfinite(seconds) or not 0 <= seconds <= 60:
        raise ValueError("Key duration must be finite and between 0 and 60 seconds")
    focus(c)
    run(["xdotool", "keydown", key], env=display(c))
    try:
        time.sleep(seconds)
    finally:
        run(["xdotool", "keyup", key], env=display(c))


def mouse(c: Config, dx: int, dy: int) -> None:
    focus(c)
    run(["xdotool", "mousemove_relative", "--", str(dx), str(dy)], env=display(c))


def request(c: Config, parts: list[str], timeout: float = 30) -> object:
    token = str(time.time_ns())
    (c.bin / "gt.reply").unlink(missing_ok=True)
    temporary = c.bin / "gt.pending"
    temporary.write_text(token + " " + " ".join(parts) + "\n")
    temporary.replace(c.bin / "gt.request")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        reply = c.bin / "gt.reply"
        if reply.exists():
            data: object = json.loads(reply.read_text())
            if isinstance(data, dict) and data.get("id") == token:
                if not data.get("ok"):
                    raise RuntimeError(str(data))
                return data
        time.sleep(0.1)
    raise TimeoutError(f"No game-thread acknowledgement for {parts}")


def result(reply: object) -> dict[str, object]:
    if not isinstance(reply, dict) or not isinstance(reply.get("result"), dict):
        raise ValueError("Malformed game reply")
    copied: dict[str, object] = {}
    for key, value in reply["result"].items():
        copied[str(key)] = value
    return copied


def enter(
    c: Config, map_path: str = "/Game/Maps/TestLevels/Levels_Zoo", timeout: float = 90
) -> None:
    deadline = time.monotonic() + timeout
    # A launch clock is only a deadline. The possessed pawn is the readiness gate.
    while time.monotonic() < deadline:
        try:
            state = result(request(c, ["status"], timeout=5))
            if state.get("worlds") and "MainMenu" in str(state["worlds"]):
                request(c, ["travel", map_path])
                break
            if state.get("pawn"):
                break
        except TimeoutError:
            if (
                subprocess.run(
                    ["systemctl", "--user", "is-active", "--quiet", "gr2-groundtruth-game"],
                    check=False,
                ).returncode
                != 0
            ):
                raise RuntimeError(
                    "Game exited before readiness; inspect launch/proton/UE4SS logs"
                ) from None
        time.sleep(1)
    while time.monotonic() < deadline:
        if result(request(c, ["status"])).get("pawn"):
            print(json.dumps(request(c, ["build"])))
            return
        time.sleep(0.5)
    raise TimeoutError("Real Jack was not possessed before the deadline")


def capture(c: Config, destination: Path) -> None:
    import signal

    pid = int(
        run(
            ["systemctl", "--user", "show", "gr2-groundtruth", "-p", "MainPID", "--value"],
            capture_output=True,
        ).stdout
    )
    previous = set(Path("/tmp").glob("gamescope_*.avif"))
    os.kill(pid, signal.SIGUSR2)
    for _ in range(50):
        time.sleep(0.1)
        fresh = set(Path("/tmp").glob("gamescope_*.avif")) - previous
        if fresh:
            source = max(fresh, key=lambda p: p.stat().st_mtime)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination.with_suffix(".avif"))
            run(["magick", str(source), str(destination)])
            return
    raise TimeoutError("Gamescope did not produce a screenshot")


def experiment(c: Config, name: str) -> None:
    stamp = str(time.time_ns())
    output = ROOT / ".work/runs" / (stamp + "-" + name)
    output.mkdir(parents=True)
    request(c, ["teleport", "walls" if name == "wallrun" else "runway"])
    request(c, ["reset"])
    if name == "wallrun":
        request(c, ["pose", "-3000", "19600", "10100"])
    time.sleep(0.5)
    before = result(request(c, ["observe"]))
    telemetry = c.bin / "gt.telemetry.jsonl"
    offset = telemetry.stat().st_size if telemetry.exists() else 0
    request(c, ["record_start"])
    try:
        if name == "wallrun":
            input_key(c, "w+space", 0.1)
            input_key(c, "w", 1)
        elif name == "walk":
            input_key(c, "w", 1)
        elif name == "dash":
            input_key(c, "w+Shift_L", 0.15)
            time.sleep(0.5)
        elif name == "jump":
            input_key(c, "space", 0.15)
            time.sleep(1)
        else:
            raise ValueError("Unknown experiment")
        after = result(request(c, ["observe"]))
    finally:
        request(c, ["record_stop"])
    with (c.bin / "gt.telemetry.jsonl").open("rb") as stream:
        stream.seek(offset)
        (output / "telemetry.jsonl").write_bytes(stream.read())
    shutil.copy2(c.bin / "UE4SS.log", output / "UE4SS.log")
    verify(c)
    write_json(
        output / "result.json",
        {
            "experiment": name,
            "before": before,
            "after": after,
            "upgrades": result(request(c, ["upgrades"])),
            "game_sha256": hashlib.sha256(
                (c.bin / "Ghostrunner2-Win64-Shipping.exe").read_bytes()
            ).hexdigest(),
            "harness_sha256": hashes(c.bin / "Mods/GroundTruth"),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "proton_version": (c.proton.parent / "version").read_text().strip(),
            "canonical_unchanged": True,
        },
    )
    capture(c, output / "screen.png")
    sample_rows: list[dict[str, object]] = []
    for line in (output / "telemetry.jsonl").read_text().splitlines():
        row: object = json.loads(line)
        if isinstance(row, dict):
            sample_rows.append({str(key): value for key, value in row.items()})
    assert len(sample_rows) >= 5, "Experiment produced too few samples"
    if name == "wallrun":
        wall_seen = False
        for row in sample_rows:
            state = row.get("player_state")
            if isinstance(state, dict) and state.get("bOnWall") is True:
                wall_seen = True
        assert wall_seen, "Native wall state was not observed"
    verify(c)
    print(output)


def steam_start(c: Config) -> None:
    if subprocess.run(["pgrep", "-x", "steam"], check=False, capture_output=True).returncode == 0:
        print("Steam client already running")
        return
    unit = "gr2-groundtruth-steam-display"
    state = run(
        ["systemctl", "--user", "show", unit, "-p", "LoadState", "--value"], capture_output=True
    )
    if state.stdout.strip() == "loaded":
        subprocess.run(["systemctl", "--user", "stop", unit], check=False, timeout=20)
    log = c.steam / "logs/connection_log.txt"
    offset = log.stat().st_size if log.exists() else 0
    run(
        [
            "systemd-run",
            "--user",
            "--unit=gr2-groundtruth-steam-display",
            "--collect",
            "--property=TimeoutStopSec=10",
            "/usr/bin/gamescope",
            "--backend",
            "headless",
            "-w",
            "1280",
            "-h",
            "720",
            "--",
            "/usr/bin/steam",
            "-silent",
        ]
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if log.exists():
            with log.open("rb") as stream:
                stream.seek(offset if log.stat().st_size >= offset else 0)
                fresh = stream.read()
            if b"RecvMsgClientLogOnResponse() : processing complete" in fresh:
                print("Steam client login acknowledged")
                return
        time.sleep(0.5)
    raise TimeoutError(
        "Steam login not acknowledged; sign in to the existing client before experiments"
    )


def mount(c: Config, pak: Path) -> None:
    if pak.suffix != ".pak":
        raise ValueError("Expected a cooked .pak")
    destination = c.state / "game/Ghostrunner2/Content/Paks" / pak.name
    if not destination.parent.resolve().is_relative_to(c.state):
        raise RuntimeError("Pak destination resolves outside private staging; prepare first")
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copy2(pak, destination)
    if pak.with_suffix(".sig").exists():
        shutil.copy2(pak.with_suffix(".sig"), destination.with_suffix(".sig"))
    print(destination)


def stop(c: Config) -> None:
    validate_paths(c)
    # Stop only this lab prefix. Steam and other Wine applications keep running.
    wine_env = {**os.environ, "WINEPREFIX": str(c.prefix / "pfx")}
    subprocess.run([str(c.proton.parent / "files/bin/wineserver"), "-k"], env=wine_env, check=False)
    subprocess.run(
        [str(c.proton.parent / "files/bin/wineserver"), "-w"], env=wine_env, check=False, timeout=10
    )
    # systemctl rejects a multi-unit stop if a failed, collected game unit is
    # absent. Stop each owned unit independently so the display is still cleaned.
    for unit in ("gr2-groundtruth-game", "gr2-groundtruth"):
        state = run(
            ["systemctl", "--user", "show", unit, "-p", "LoadState", "--value"], capture_output=True
        )
        if state.stdout.strip() == "loaded":
            run(["systemctl", "--user", "stop", unit])

    verify(c)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("prepare", "stop", "verify", "reset-saves", "enter"):
        sub.add_parser(name)
    sub.add_parser("launch")
    custom = sub.add_parser("mount")
    custom.add_argument("pak", type=Path)
    sub.add_parser("steam-start")
    cmd = sub.add_parser("cmd")
    cmd.add_argument("parts", nargs="+")
    key = sub.add_parser("key")
    key.add_argument("key")
    key.add_argument("seconds", type=float, nargs="?", default=0.1)
    motion = sub.add_parser("mouse")
    motion.add_argument("dx", type=int)
    motion.add_argument("dy", type=int)
    shot = sub.add_parser("capture")
    shot.add_argument("destination", type=Path)
    exp = sub.add_parser("experiment")
    exp.add_argument("name", choices=("walk", "dash", "jump", "wallrun"))
    args = parser.parse_args()
    c = Config.load()
    c.state.mkdir(parents=True, exist_ok=True)
    lock = (c.state / "control.lock").open("w")
    try:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise RuntimeError("Another lab operation owns the command bridge") from error
    if args.action == "prepare":
        prepare(c)
    elif args.action == "launch":
        start(c)
    elif args.action == "steam-start":
        steam_start(c)
    elif args.action == "mount":
        check_stopped(c)
        mount(c, args.pak)
    elif args.action == "stop":
        stop(c)
    elif args.action == "verify":
        verify(c)
    elif args.action == "reset-saves":
        reset_saves(c)
    elif args.action == "cmd":
        print(json.dumps(request(c, args.parts)))
    elif args.action == "enter":
        enter(c)
    elif args.action == "capture":
        capture(c, args.destination)
    elif args.action == "experiment":
        experiment(c, args.name)
    elif args.action == "mouse":
        mouse(c, args.dx, args.dy)
    elif args.action == "key":
        input_key(c, args.key, args.seconds)


if __name__ == "__main__":
    main()
