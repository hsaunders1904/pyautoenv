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
import base64
import enum
import hashlib
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, TextIO, Union

__version__ = "0.2.0"


@dataclass
class CliArgs:
    """Command line arguments for the script."""

    directory: Path
    """Directory to look for a python environment in."""


class Os(enum.Enum):
    """Supported OS names."""

    LINUX = enum.auto()
    MACOS = enum.auto()
    WINDOWS = enum.auto()


def main(sys_args: List[str], stdout: TextIO) -> int:
    """Write commands to activate/deactivate environments."""
    args = parse_args(sys_args)
    if not args.directory.is_dir():
        return 1
    new_env_path = discover_env(args.directory)
    if active_env_path := os.environ.get("VIRTUAL_ENV", None):
        if not new_env_path:
            stdout.write("deactivate")
        elif not new_env_path.samefile(active_env_path):
            stdout.write("deactivate")
            if activate := env_activation_path(new_env_path):
                stdout.write(f" && . {activate}")
    elif new_env_path and (activate := env_activation_path(new_env_path)):
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
        type=lambda p: Path(p).resolve(),
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


def discover_env(directory: Path) -> Union[Path, None]:
    """Find an environment in the given directory or any of its parents."""
    while directory != directory.parent:
        if env_dir := get_virtual_env(directory):
            return env_dir
        directory = directory.parent
    return None


def get_virtual_env(directory: Path) -> Union[Path, None]:
    """Return the environment if defined in the given directory."""
    if has_venv(directory):
        return directory / ".venv"
    if has_poetry_env(directory) and (env_path := poetry_env_path(directory)):
        return env_path
    return None


def has_venv(directory: Path) -> bool:
    """Return true if a venv exists in the given directory."""
    candidate_path = venv_path(directory)
    return candidate_path.is_file()


def env_activation_path(env_dir: Path) -> Union[Path, None]:
    """Get the path to the activation script for the environment."""
    if operating_system() is Os.WINDOWS:
        if (path := env_dir / "Scripts" / "Activate.ps1").is_file():
            return path
    elif (path := env_dir / "bin" / "activate").is_file():
        return path
    return None


def venv_path(directory: Path) -> Path:
    """Get the path to the activate script for a venv."""
    if operating_system() is Os.WINDOWS:
        return directory / ".venv" / "Scripts" / "Activate.ps1"
    return directory / ".venv" / "bin" / "activate"


def has_poetry_env(directory: Path) -> bool:
    """Return true if a poetry env exists in the given directory."""
    return (directory / "poetry.lock").is_file() and (
        directory / "pyproject.toml"
    ).is_file()


def poetry_env_path(directory: Path) -> Union[Path, None]:
    """Return the path of the venv associated with a poetry project directory."""
    if env_list := poetry_env_list(directory):
        return max(env_list, key=lambda p: p.stat().st_mtime)
    return None


def operating_system() -> Union[Os, None]:
    """
    Return the operating system the script's being run on.

    Return 'None' if we're on an operating system we can't handle.
    """
    platform_sys = platform.system()
    if platform_sys == "Darwin":
        return Os.MACOS
    if platform_sys == "Windows":
        return Os.WINDOWS
    if platform_sys == "Linux":
        return Os.LINUX
    return None


def poetry_cache_dir() -> Union[Path, None]:
    """Return the poetry cache directory, or None if it's not found."""
    cache_dir_str = os.environ.get("POETRY_CACHE_DIR", None)
    if cache_dir_str and (cache_dir := Path(cache_dir_str)).is_dir():
        return cache_dir
    if operating_system() is Os.WINDOWS:
        return windows_poetry_cache_dir()
    if operating_system() is Os.MACOS:
        return macos_poetry_cache_dir()
    if operating_system() is Os.LINUX:
        return linux_poetry_cache_dir()
    return None


def linux_poetry_cache_dir() -> Union[Path, None]:
    """Return the poetry cache directory for Linux."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    if (cache_dir := Path(xdg_cache) / "pypoetry").is_dir():
        return cache_dir
    return None


def macos_poetry_cache_dir() -> Union[Path, None]:
    """Return the poetry cache directory for MacOS."""
    cache_dir = Path.home() / "Library" / "Caches" / "pypoetry"
    if cache_dir.is_dir():
        return cache_dir
    return None


def windows_poetry_cache_dir() -> Union[Path, None]:
    """Return the poetry cache directory for Windows."""
    app_data = os.environ.get("LOCALAPPDATA", None)
    if app_data and (cache_dir := Path(app_data) / "pypoetry").is_dir():
        return cache_dir
    return None


def poetry_env_name(directory: Path) -> Union[str, None]:
    """
    Get the name of the poetry environment defined in the given directory.

    Logic comes from the poetry source code:
    https://github.com/python-poetry/poetry/blob/2b15ce10f02b0c6347fe2f12ae902488edeaaf7c/src/poetry/utils/env.py#L1207.
    """
    if (name := poetry_project_name(directory)) is None:
        return None
    name = name.lower()
    sanitized_name = re.sub(r'[ $`!*@"\\\r\n\t]', "_", name)[:42]
    normalized_path = os.path.normcase(directory.resolve())
    path_hash = hashlib.sha256(normalized_path.encode()).digest()
    b64_hash = base64.urlsafe_b64encode(path_hash).decode()[:8]
    return f"{sanitized_name}-{b64_hash}"


def poetry_env_list(directory: Path) -> List[Path]:
    """Return list of poetry environments for the given directory."""
    if (cache_dir := poetry_cache_dir()) is None:
        return []
    if (env_name := poetry_env_name(directory)) is None:
        return []
    return list((cache_dir / "virtualenvs").glob(f"{env_name}-py*"))


def poetry_project_name(directory: Path) -> Union[str, None]:
    """Parse the poetry project name from the given directory."""
    try:
        with (directory / "pyproject.toml").open() as f:
            pyproject = f.readlines()
    except OSError:
        return None
    in_tool_poetry = False
    for line in pyproject:
        if line.strip() == "[tool.poetry]":
            in_tool_poetry = True
            continue
        if line.strip().startswith("["):
            in_tool_poetry = False
        if not in_tool_poetry:
            continue
        if re.match(r'name *= * ".*"', line.strip()):
            try:
                return line.split("=")[1].strip().strip('"')
            except IndexError:
                continue
    return None


if __name__ == "__main__":
    import sys

    try:
        exit_code = main(sys.argv[1:], sys.stdout)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"pyautoenv: {exc}\n")
        sys.exit(1)
    sys.exit(exit_code)
