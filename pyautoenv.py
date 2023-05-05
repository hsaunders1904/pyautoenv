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
from functools import lru_cache
from typing import List, TextIO, Union

__version__ = "0.4.0"

CLI_HELP = f"""usage: pyautoenv [-h] [-V] [--fish] [directory]
{__doc__}
positional arguments:
  directory      the path to look in for a python environment (default: '.')

options:
  --fish         use fish activation script
  -h, --help     show this help message and exit
  -V, --version  show program's version number and exit
"""
VENV_NAMES = "PYAUTOENV_VENV_NAME"


class CliArgs:
    """Container for command line arguments."""

    def __init__(self, directory: str, *, fish: bool) -> None:
        self.directory = directory
        self.fish = fish


class Os:
    """Pseudo-enum for supported operating systems."""

    LINUX = 0
    MACOS = 1
    WINDOWS = 2


def main(sys_args: List[str], stdout: TextIO) -> int:
    """Write commands to activate/deactivate environments."""
    args = parse_args(sys_args, stdout)
    if not os.path.isdir(args.directory):
        return 1
    new_env_path = discover_env(args.directory)
    if active_env_path := os.environ.get("VIRTUAL_ENV", None):
        if not new_env_path:
            stdout.write("deactivate")
        elif not os.path.samefile(new_env_path, active_env_path):
            stdout.write("deactivate")
            if activate := env_activation_path(new_env_path, fish=args.fish):
                stdout.write(f" && . {activate}")
    elif new_env_path and (
        activate := env_activation_path(new_env_path, fish=args.fish)
    ):
        stdout.write(f". {activate}")
    return 0


def parse_args(argv: List[str], stdout: TextIO) -> CliArgs:
    """Parse the sequence of command line arguments."""
    # Avoiding argparse gives a good speed boost and the parsing logic
    # is not too complex. We won't get a full 'bells and whistles' CLI
    # experience, but that's fine for our use-case.

    def parse_exit_flag(argv: List[str], flags: List[str]) -> bool:
        return any(f in argv for f in flags)

    def parse_flag(argv: List[str], flag: str) -> bool:
        try:
            argv.pop(argv.index(flag))
        except ValueError:
            return False
        else:
            return True

    if parse_exit_flag(argv, ["-h", "--help"]):
        stdout.write(CLI_HELP)
        sys.exit(0)
    if parse_exit_flag(argv, ["-V", "--version"]):
        stdout.write(f"pyautoenv {__version__}\n")
        sys.exit(0)

    fish = parse_flag(argv, "--fish")
    if len(argv) == 0:
        return CliArgs(directory=os.getcwd(), fish=fish)
    if len(argv) > 1:
        raise ValueError(  # noqa: TRY003
            f"exactly one positional argument expected, found {len(argv)}",
        )
    return CliArgs(directory=os.path.abspath(argv[0]), fish=fish)


def discover_env(directory: str) -> Union[str, None]:
    """Find an environment in the given directory or any of its parents."""
    while directory != os.path.dirname(directory):
        if env_dir := get_virtual_env(directory):
            return env_dir
        directory = os.path.dirname(directory)
    return None


def get_virtual_env(directory: str) -> Union[str, None]:
    """Return the environment if defined in the given directory."""
    if venv_dir := has_venv(directory):
        return venv_dir
    if has_poetry_env(directory) and (env_path := poetry_env_path(directory)):
        return env_path
    return None


def has_venv(directory: str) -> Union[str, None]:
    """Return the venv within the given directory if it contains one."""
    candidate_paths = venv_path(directory)
    for path in candidate_paths:
        if os.path.isfile(activator(path)):
            return path
    return None


def venv_path(directory: str) -> List[str]:
    """Get the paths to the activate scripts for a list of candidate venvs."""
    venv_paths = []
    for venv_name in venv_dir_names():
        activator_path = os.path.join(directory, venv_name)
        venv_paths.append(activator_path)
    return venv_paths


def venv_dir_names() -> List[str]:
    """Get the possible names for a venv directory."""
    if name_list := os.environ.get(VENV_NAMES, ""):
        return [x for x in name_list.split(";") if x]
    return [".venv"]


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
        os.path.join(os.path.expanduser("~"), ".cache"),
    )
    return os.path.join(xdg_cache, "pypoetry")


def macos_poetry_cache_dir() -> str:
    """Return the poetry cache directory for MacOS."""
    return os.path.join(
        os.path.expanduser("~"),
        "Library",
        "Caches",
        "pypoetry",
    )


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

    # These two take roughly the same amount of time to import as it
    # does to run the rest of the script. Import locally here, so we're
    # only importing when we know that we need to.
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


def env_activation_path(env_dir: str, *, fish: bool) -> Union[str, None]:
    """Get the path to the activation script for the environment, if it exists."""
    activate_script = activator(env_dir, fish=fish)
    if os.path.isfile(activate_script):
        return activate_script
    return None


def activator(env_directory: str, *, fish: bool = False) -> str:
    """Get the activator script for the environment in the given directory."""
    if operating_system() == Os.WINDOWS:
        return os.path.join(env_directory, "Scripts", "Activate.ps1")
    path = os.path.join(env_directory, "bin", "activate")
    if fish:
        path += ".fish"
    return path


@lru_cache
def operating_system() -> Union[int, None]:
    """
    Return the operating system the script's being run on.

    Return 'None' if we're on an operating system we can't handle.
    """
    if sys.platform.startswith("darwin"):
        return Os.MACOS
    if sys.platform.startswith("win"):
        return Os.WINDOWS
    if sys.platform.startswith("linux"):
        return Os.LINUX
    return None


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:], sys.stdout))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"pyautoenv: error: {exc}\n")
        sys.exit(1)
