#!/usr/bin/env python3
"""Activate a python environment if it exists in the given directory."""

import argparse
import enum
import os
import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, Union


@dataclass
class CliArgs:
    """Command line arguments for the script."""

    directory: Path
    """Directory to look for a python environment in."""


class EnvType(enum.Enum):
    """The types of virtual environments."""

    VENV = enum.auto()
    POETRY = enum.auto()


@dataclass
class Env:
    """Container for virtual environment information."""

    directory: Path
    env_type: EnvType


def main(sys_args: Sequence[str], stdout: TextIO) -> int:
    """Activate environment if it exists in the given directory."""
    args = parse_args(sys_args)
    if not args.directory.is_dir():
        return 1
    if env := discover_env(args.directory):
        if env.env_type == EnvType.VENV:
            if active_venv := os.environ.get("VIRTUAL_ENV", ""):
                if not Path(active_venv).samefile(env.directory):
                    print(f"deactivate && {activate_venv(env.directory)}", file=stdout)
            else:
                print(activate_venv(env.directory), file=stdout)
        if env.env_type == EnvType.POETRY:
            if not shutil.which("poetry"):
                return 0
            if active_venv := os.environ.get("VIRTUAL_ENV", ""):
                if not Path(active_venv).samefile(poetry_env_path(args.directory)):
                    print(
                        f"deactivate && {activate_poetry(env.directory)}", file=stdout
                    )
            else:
                print(activate_poetry(env.directory), file=stdout)
    elif os.environ.get("VIRTUAL_ENV", None):
        print("deactivate", file=stdout)
    return 0


def parse_args(sys_args: Sequence[str]) -> CliArgs:
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


def discover_env(directory: Path) -> Env | None:
    """Find an environment in the given directory, or any of its parents."""
    while directory != directory.parent:
        if env_type := check_env(directory):
            return Env(directory=directory, env_type=env_type)
        directory = directory.parent
    return None


def check_env(directory: Path) -> EnvType | None:
    """Return true if an environment exists in the given directory."""
    if check_venv(directory):
        return EnvType.VENV
    if check_poetry(directory):
        return EnvType.POETRY
    return None


def check_venv(directory: Path) -> bool:
    """Return true if a venv exists in the given directory."""
    candidate_path = venv_path(directory)
    return candidate_path.is_file()


def activate_venv(directory: Path) -> int:
    """Activate the venv in the given directory."""
    path = venv_path(directory)
    return str(path)


def venv_path(directory: Path) -> Path:
    """Get the path to the activate script for a venv."""
    return directory / ".venv" / "bin" / "activate"


def check_poetry(directory: Path) -> bool:
    """Return true if the a poetry env exists in the given directory."""
    candidate_path = directory.joinpath("poetry.lock")
    return candidate_path.is_file()


def activate_poetry(directory: Path) -> str:
    """Activate the poetry environment in the given directory."""
    env_path = poetry_env_path(directory)
    return str(env_path / "bin" / "activate")


def poetry_env_path(directory: Path) -> Union[Path, None]:
    """Return the path of the venv associated with a poetry project directory."""
    try:
        return Path(
            subprocess.run(
                ["poetry", "-C", str(directory), "env", "info", "--path"],
                capture_output=True,
            )
            .stdout.decode()
            .strip()
        )
    except subprocess.CalledProcessError:
        return None


if __name__ == "__main__":
    import sys

    main(sys.argv[1:], sys.stdout)
