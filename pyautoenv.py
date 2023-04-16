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

Supports environments managed by venv and poetry. A venv project directory
must contain a directory called '.venv', a poetry project directory must
contain a 'poetry.lock' file.
"""
import os
import sys
from typing import List, TextIO, Union

__version__ = "0.2.1"

CLI_HELP = f"""usage: pyautoenv [-h] [-V] [directory]
{__doc__}
positional arguments:
  directory      the path to look in for a python environment

options:
  -h, --help     show this help message and exit
  -V, --version  show program's version number and exit
"""


class Os:
    """Pseudo-enum for supported operating systems."""

    LINUX = 0
    MACOS = 1
    WINDOWS = 2
    # a variable to cache the current OS once it's checked.
    CURRENT: Union[int, None] = -1


def main(sys_args: List[str], stdout: TextIO) -> int:
    """Write commands to activate/deactivate environments."""
    directory = parse_args(sys_args, stdout)
    if not os.path.isdir(directory):
        return 1
    new_env_path = discover_env(directory)
    if active_env_path := os.environ.get("VIRTUAL_ENV", None):
        if not new_env_path:
            stdout.write("deactivate")
        elif not os.path.samefile(new_env_path, active_env_path):
            stdout.write("deactivate")
            if activate := env_activation_path(new_env_path):
                stdout.write(f" && . {activate}")
    elif new_env_path and (activate := env_activation_path(new_env_path)):
        stdout.write(f". {activate}")
    return 0


def parse_args(argv: List[str], stdout: TextIO) -> str:
    """Parse the sequence of command line arguments."""
    # Avoiding argparse gives a good speed boost and the parsing logic
    # is not too complex. We won't get a full 'bells and whistles' CLI
    # experience, but that's fine for our use-case.
    if len(argv) == 0:
        return os.getcwd()
    if any(h in argv for h in ["-h", "--help"]):
        stdout.write(CLI_HELP)
        sys.exit(0)
    if any(v in argv for v in ["-V", "--version"]):
        stdout.write(f"pyautoenv {__version__}\n")
        sys.exit(0)
    if len(argv) > 1:
        raise ValueError(  # noqa: TRY003
            f"exactly one argument expected, found {len(argv)}",
        )
    return os.path.abspath(argv[0])


def discover_env(directory: str) -> Union[str, None]:
    """Find an environment in the given directory or any of its parents."""
    while directory != os.path.dirname(directory):
        if env_dir := get_virtual_env(directory):
            return env_dir
        directory = os.path.dirname(directory)
    return None


def get_virtual_env(directory: str) -> Union[str, None]:
    """Return the environment if defined in the given directory."""
    if has_venv(directory):
        return os.path.join(directory, ".venv")
    if has_poetry_env(directory) and (env_path := poetry_env_path(directory)):
        return env_path
    return None


def has_venv(directory: str) -> bool:
    """Return true if the given directory contains a project with a venv."""
    candidate_path = venv_path(directory)
    return os.path.isfile(candidate_path)


def venv_path(directory: str) -> str:
    """Get the path to the activate script for a venv."""
    if operating_system() == Os.WINDOWS:
        return os.path.join(directory, ".venv", "Scripts", "Activate.ps1")
    return os.path.join(directory, ".venv", "bin", "activate")


def has_poetry_env(directory: str) -> bool:
    """Return true if the given directory contains a poetry project."""
    return os.path.isfile(os.path.join(directory, "poetry.lock"))


def poetry_env_path(directory: str) -> Union[str, None]:
    """
    Return the path of the venv associated with a poetry project directory.

    If there are multiple poetry environments, pick the one with the
    latest modification time.
    """
    if env_list := poetry_env_list(directory):
        return max(env_list, key=lambda p: os.stat(p).st_mtime)
    return None


def poetry_env_list(directory: str) -> List[str]:
    """
    Return list of poetry environments for the given directory.

    This can be found via the poetry CLI using
    ``poetry env list --full-path``, but it's painfully slow.
    """
    if (cache_dir := poetry_cache_dir()) is None:
        return []
    if (env_name := poetry_env_name(directory)) is None:
        return []
    try:
        return [
            f.path
            for f in os.scandir(os.path.join(cache_dir, "virtualenvs"))
            if f.name.startswith(f"{env_name}-py")
        ]
    except OSError:
        return []


def poetry_cache_dir() -> Union[str, None]:
    """Return the poetry cache directory, or None if it's not found."""
    cache_dir = os.environ.get("POETRY_CACHE_DIR", None)
    if cache_dir and os.path.isdir(cache_dir):
        return cache_dir
    op_sys = operating_system()
    if op_sys == Os.WINDOWS:
        return windows_poetry_cache_dir()
    if op_sys == Os.MACOS:
        return macos_poetry_cache_dir()
    if op_sys == Os.LINUX:
        return linux_poetry_cache_dir()
    return None


def linux_poetry_cache_dir() -> Union[str, None]:
    """Return the poetry cache directory for Linux."""
    xdg_cache = os.environ.get(
        "XDG_CACHE_HOME",
        os.path.expanduser("~/.cache"),
    )
    return os.path.join(xdg_cache, "pypoetry")


def macos_poetry_cache_dir() -> str:
    """Return the poetry cache directory for MacOS."""
    return os.path.expanduser("~/Library/Caches/pypoetry")


def windows_poetry_cache_dir() -> Union[str, None]:
    """Return the poetry cache directory for Windows."""
    if not (app_data := os.environ.get("LOCALAPPDATA", None)):
        return None
    return os.path.join(app_data, "pypoetry", "Cache")


def poetry_env_name(directory: str) -> Union[str, None]:
    """
    Get the name of the poetry environment defined in the given directory.

    A poetry environment directory will have a name of the form
    ``pyautoenv-AacnJhVq-py3.10``. Where the first part is the
    (sanitized) project name taken from 'pyproject.toml'. The second
    part is the first 8 characters of the (base64 encoded) SHA256 hash
    of the absolute path of the project directory. The final part is
    'py' followed by the Python version (<major>.<minor>).

    This function derives the first two parts of this name. There may be
    multiple environments (using different Python versions) for a given
    poetry project, so we must search for the final part of the name
    later.

    Logic comes from the poetry source code:
    https://github.com/python-poetry/poetry/blob/2b15ce10f02b0c6347fe2f12ae902488edeaaf7c/src/poetry/utils/env.py#L1207.
    """
    if (name := poetry_project_name(directory)) is None:
        return None

    import base64
    import hashlib

    name = name.lower()
    sanitized_name = (
        # This is a bit ugly, but it's more performant than using a regex.
        # The import time for the 're' module is also a factor.
        name.replace(" ", "_")
        .replace("$", "_")
        .replace("`", "_")
        .replace("!", "_")
        .replace("*", "_")
        .replace("@", "_")
        .replace("\\", "_")
        .replace("\r", "_")
        .replace("\n", "_")
        .replace("\t", "_")
    )
    normalized_path = os.path.normcase(os.path.realpath(directory))
    path_hash = hashlib.sha256(normalized_path.encode()).digest()
    b64_hash = base64.urlsafe_b64encode(path_hash).decode()[:8]
    return f"{sanitized_name}-{b64_hash}"


def poetry_project_name(directory: str) -> Union[str, None]:
    """Parse the poetry project name from the given directory."""
    try:
        with open(os.path.join(directory, "pyproject.toml")) as f:
            pyproject = f.readlines()
    except OSError:
        return None
    # Ideally we'd use a proper TOML parser to do this, but there isn't
    # one available in the standard library until Python 3.11. This
    # hacked together parser should work for the vast majority of cases.
    in_tool_poetry = False
    for line in pyproject:
        if line.strip() == "[tool.poetry]":
            in_tool_poetry = True
            continue
        if line.strip().startswith("["):
            in_tool_poetry = False
        if not in_tool_poetry:
            continue
        try:
            key, val = (part.strip().strip('"') for part in line.split("="))
        except ValueError:
            continue
        if key == "name":
            return val
    return None


def env_activation_path(env_dir: str) -> Union[str, None]:
    """Get the path to the activation script for the environment."""
    if operating_system() == Os.WINDOWS:
        path = os.path.join(env_dir, "Scripts", "Activate.ps1")
        if os.path.isfile(path):
            return path
    else:
        path = os.path.join(env_dir, "bin", "activate")
        if os.path.isfile(path):
            return path
    return None


def operating_system() -> Union[int, None]:
    """
    Return the operating system the script's being run on.

    Return 'None' if we're on an operating system we can't handle.
    """
    if Os.CURRENT == -1:
        if sys.platform.startswith("darwin"):
            Os.CURRENT = Os.MACOS
        elif sys.platform.startswith("win"):
            Os.CURRENT = Os.WINDOWS
        elif sys.platform.startswith("linux"):
            Os.CURRENT = Os.LINUX
        else:
            Os.CURRENT = None
    return Os.CURRENT


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:], sys.stdout))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"pyautoenv: error: {exc}\n")
        sys.exit(1)
