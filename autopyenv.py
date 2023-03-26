#!/usr/bin/env python3
"""Activate a python environment if it exists in the given directory."""

import argparse
import enum
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, Union


@dataclass
class CliArgs:
    """Command line arguments for the script."""

    directory: Path
    """Directory to look for a python environment in."""


class EnvType(enum.Enum):
    """Types of virtual environments."""

    POETRY = enum.auto()
    VENV = enum.auto()


@dataclass
class Env:
    """Container for virtual environment information."""

    directory: Path
    env_type: EnvType


def main(sys_args: list[str], stdout: TextIO) -> int:
    """Activate environment if it exists in the given directory."""
    args = parse_args(sys_args)
    if not args.directory.is_dir():
        return 1
    new_env = discover_env(args.directory)
    if active_env_path := os.environ.get("VIRTUAL_ENV", None):
        if not new_env:
            stdout.write("deactivate")
            return 0
        if not new_env.directory.samefile(active_env_path):
            stdout.write("deactivate")
            if activate := env_activate_path(new_env):
                stdout.write(f" && source {activate}")
    elif new_env and (activate := env_activate_path(new_env)):
        stdout.write(f"source {activate}")
    return 0


def parse_args(sys_args: list[str]) -> CliArgs:
    """Parse the sequence of command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        type=Path,
        help="the path to look in for a python environment",
        default=Path.cwd(),
        nargs="?",
    )
    args = parser.parse_args(sys_args)
    return CliArgs(**vars(args))


def discover_env(directory: Path) -> Union[Env, None]:
    """Find an environment in the given directory, or any of its parents."""
    while directory != directory.parent:
        if env := check_env(directory):
            return env
        directory = directory.parent
    return None


def check_env(directory: Path) -> Union[Env, None]:
    """Return true if an environment exists in the given directory."""
    if check_venv(directory):
        return Env(directory=directory, env_type=EnvType.VENV)
    if check_poetry(directory) and (env_path := poetry_env_path(directory)):
        return Env(directory=env_path, env_type=EnvType.POETRY)
    return None


def check_venv(directory: Path) -> bool:
    """Return true if a venv exists in the given directory."""
    candidate_path = venv_path(directory)
    return candidate_path.is_file()


def env_activate_path(env: Env) -> Union[Path, None]:
    """Get the path to the activation script for the environment."""
    if env.env_type == EnvType.POETRY:
        return env.directory / "bin" / "activate"
    if env.env_type == EnvType.VENV:
        return venv_path(env.directory)
    return None


def venv_path(directory: Path) -> Path:
    """Get the path to the activate script for a venv."""
    return directory / ".venv" / "bin" / "activate"


def check_poetry(directory: Path) -> bool:
    """Return true if a poetry env exists in the given directory."""
    candidate_path = directory.joinpath("poetry.lock")
    return candidate_path.is_file()


def poetry_env_path(directory: Path) -> Union[Path, None]:
    """Return the path of the venv associated with a poetry project directory."""
    try:
        env_list = (
            subprocess.run(
                ["poetry", "env", "list", "--full-path"],
                cwd=directory,
                capture_output=True,
            )
            .stdout.decode()
            .strip()
        )
        if env_list.endswith(" (Activated)"):
            return Path(env_list[:-12])
    except subprocess.CalledProcessError:
        return None
    else:
        return Path(env_list)


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:], sys.stdout))
