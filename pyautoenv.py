#!/usr/bin/env python3
# pyautoenv Automatically activate and deactivate Python environments.
# Copyright (C) 2023  Harry Saunders.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
Print a command to activate or deactivate a Python venv based on a directory.

Supports environments managed by venv and poetry.
"""

import argparse
import enum
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, TextIO, Union

__version__ = "0.1.0"


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


def main(sys_args: List[str], stdout: TextIO) -> int:
    """Activate environment if it exists in the given directory."""
    args = parse_args(sys_args)
    if not args.directory.is_dir():
        return 1
    new_env = discover_env(args.directory)
    if active_env_path := os.environ.get("VIRTUAL_ENV", None):
        if not new_env:
            stdout.write("deactivate")
        elif not new_env.directory.samefile(active_env_path):
            stdout.write("deactivate")
            if activate := env_activate_path(new_env):
                stdout.write(f" && . {activate}")
    elif new_env and (activate := env_activate_path(new_env)):
        stdout.write(f". {activate}")
    return 0


def parse_args(sys_args: List[str]) -> CliArgs:
    """Parse the sequence of command line arguments."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="the path to look in for a python environment",
        default=Path.cwd(),
        nargs="?",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"pyautoenv {__version__}",
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
        return Env(directory=directory / ".venv", env_type=EnvType.VENV)
    if check_poetry(directory) and (env_path := poetry_env_path(directory)):
        return Env(directory=env_path, env_type=EnvType.POETRY)
    return None


def check_venv(directory: Path) -> bool:
    """Return true if a venv exists in the given directory."""
    candidate_path = venv_path(directory)
    return candidate_path.is_file()


def env_activate_path(env: Env) -> Union[Path, None]:
    """Get the path to the activation script for the environment."""
    if is_windows():
        if (path := env.directory / "Scripts" / "Activate.ps1").is_file():
            return path
    elif (path := env.directory / "bin" / "activate").is_file():
        return path
    return None


def venv_path(directory: Path) -> Path:
    """Get the path to the activate script for a venv."""
    if is_windows():
        return directory / ".venv" / "Scripts" / "Activate.ps1"
    return directory / ".venv" / "bin" / "activate"


def check_poetry(directory: Path) -> bool:
    """Return true if a poetry env exists in the given directory."""
    candidate_path = directory.joinpath("poetry.lock")
    return candidate_path.is_file()


def poetry_env_path(directory: Path) -> Union[Path, None]:
    """
    Return the path of the venv associated with a poetry project directory.

    Note that there may be more than one poetry environment associated with
    a poetry project directory. We first take whichever env is 'Activated',
    as given by 'poetry env list --full-path'. If that doesn't work, take
    the first path that exists, or return None if none do.
    """
    if env_list := poetry_env_list_path(directory):
        for env_path in env_list:
            if (
                env_path.endswith(" (Activated)")
                and (path := Path(env_path[:-12])).is_dir()
            ):
                return path
        for env_path in env_list:
            if (path := Path(env_path)).is_dir():
                return path
    return None


def poetry_env_list_path(directory: Path) -> Union[list[str], None]:
    """Try to get a list of poetry environments for a given directory."""
    try:
        return poetry_env_list_path_subprocess(directory).strip().split("\n")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def poetry_env_list_path_subprocess(cwd: Path) -> str:
    """Run 'poetry env list --full-path' and return the output."""
    return subprocess.run(
        ["poetry", "env", "list", "--full-path"],
        cwd=cwd,
        capture_output=True,
        check=True,
    ).stdout.decode()


def is_windows() -> bool:
    """Return True if the OS running the script is Windows."""
    return os.name == "nt"


if __name__ == "__main__":
    import sys

    try:
        exit_code = main(sys.argv[1:], sys.stdout)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"pyautoenv: {exc}\n")
        sys.exit(1)
    sys.exit(exit_code)
