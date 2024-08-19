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

Supports environments managed by venv or poetry. A poetry project
directory must contain a 'poetry.lock' file. A venv project must contain
a directory called '.venv' or one of the names in the
'PYAUTOENV_VENV_NAME' environment variable (names separated by a ';').

To specify specific directories where pyautoenv should not activate
environments, add the directory's path to the 'PYAUTOENV_IGNORE_DIR'
environment variable. Paths should be separated using a ';'.
"""

import os
import sys
from functools import lru_cache
from typing import List, TextIO, Union

__version__ = "0.6.1"

CLI_HELP = f"""usage: pyautoenv [-h] [-V] [--fish | --pwsh] [directory]
{__doc__}
positional arguments:
  directory      the path to look in for a python environment (default: '.')

options:
  --fish         use fish activation script
  --pwsh         use powershell activation script
  -h, --help     show this help message and exit
  -V, --version  show program's version number and exit
"""
IGNORE_DIRS = "PYAUTOENV_IGNORE_DIR"
"""Directories to ignore and not activate environments within."""
VENV_NAMES = "PYAUTOENV_VENV_NAME"
"""Directory names to search in for venv virtual environments."""


class Args:
    """Container for command line arguments."""

    def __init__(
        self,
        directory: str,
        *,
        fish: bool = False,
        pwsh: bool = False,
    ) -> None:
        self.directory = directory
        self.fish = fish
        self.pwsh = pwsh


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
    new_activator = discover_env(args)
    active_env_dir = os.environ.get("VIRTUAL_ENV", None)
    if active_env_dir:
        if not new_activator:
            stdout.write("deactivate")
        elif not activator_in_venv(
            new_activator,
            active_env_dir,
        ) and os.path.isfile(new_activator):
            stdout.write(f"deactivate && . {new_activator}")
    elif new_activator and os.path.isfile(new_activator):
        stdout.write(f". '{new_activator}'")
    return 0


def activator_in_venv(activator_path: str, venv_dir: str) -> bool:
    """Return True if the given activator is in the given venv directory."""
    activator_venv_dir = os.path.dirname(os.path.dirname(activator_path))
    return os.path.samefile(activator_venv_dir, venv_dir)


def parse_args(argv: List[str], stdout: TextIO) -> Args:
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
        return True

    if parse_exit_flag(argv, ["-h", "--help"]):
        stdout.write(CLI_HELP)
        sys.exit(0)
    if parse_exit_flag(argv, ["-V", "--version"]):
        stdout.write(f"pyautoenv {__version__}\n")
        sys.exit(0)

    fish = parse_flag(argv, "--fish")
    pwsh = parse_flag(argv, "--pwsh")
    num_activators = sum([fish, pwsh])
    if num_activators > 1:
        raise ValueError(
            f"zero or one activator flag expected, found {num_activators}",
        )
    # ignore empty arguments
    argv = [a for a in argv if a.strip()]
    if len(argv) > 1:
        raise ValueError(
            f"exactly one positional argument expected, found {len(argv)}",
        )
    directory = os.path.abspath(argv[0]) if len(argv) else os.getcwd()
    return Args(directory=directory, fish=fish, pwsh=pwsh)


def discover_env(args: Args) -> Union[str, None]:
    """Find an environment in the given directory or any of its parents."""
    while (not dir_is_ignored(args.directory)) and (
        args.directory != os.path.dirname(args.directory)
    ):
        env_dir = get_virtual_env(args)
        if env_dir:
            return env_dir
        args.directory = os.path.dirname(args.directory)
    return None


def dir_is_ignored(directory: str) -> bool:
    """Return True if the given directory is marked to be ignored."""
    return any(directory == ignored for ignored in ignored_dirs())


@lru_cache(maxsize=128)
def ignored_dirs() -> List[str]:
    """Get the list of directories to not activate an environment within."""
    dirs = os.environ.get(IGNORE_DIRS, None)
    if dirs:
        return dirs.split(";")
    return []


def get_virtual_env(args: Args) -> Union[str, None]:
    """Return the activator for the venv if defined in the given directory."""
    venv_dir = venv_activator(args)
    if venv_dir:
        return venv_dir
    if has_poetry_env(args.directory):
        return poetry_activator(args)
    return None


def venv_activator(args: Args) -> Union[str, None]:
    """Return the venv activator within the given directory, if it contains a venv."""
    candidate_venv_dirs = venv_candidate_dirs(args)
    for path in candidate_venv_dirs:
        activate_script = activator(path, args)
        if os.path.isfile(activate_script):
            return activate_script
    return None


def venv_candidate_dirs(args: Args) -> List[str]:
    """Get the paths to a list of candidate venvs within the given directory."""
    candidate_paths = []
    for venv_name in venv_dir_names():
        candidate_dir = os.path.join(args.directory, venv_name)
        candidate_paths.append(candidate_dir)
    return candidate_paths


def venv_dir_names() -> List[str]:
    """Get the possible names for a venv directory."""
    name_list = os.environ.get(VENV_NAMES, "")
    if name_list:
        return [x for x in name_list.split(";") if x]
    return [".venv"]


def has_poetry_env(directory: str) -> bool:
    """Return true if the given directory contains a poetry project."""
    return os.path.isfile(os.path.join(directory, "poetry.lock"))


def poetry_activator(args: Args) -> Union[str, None]:
    """
    Return the activator for the venv associated with a poetry project directory.

    If there are multiple poetry environments, pick the one with the
    latest modification time.
    """
    env_list = poetry_env_list(args.directory)
    if env_list:
        env_dir = max(env_list, key=lambda p: os.stat(p).st_mtime)
        return activator(env_dir, args)
    return None


def poetry_env_list(directory: str) -> List[str]:
    """
    Return list of poetry environments for the given directory.

    This can be found via the poetry CLI using
    ``poetry env list --full-path``, but it's painfully slow.
    """
    cache_dir = poetry_cache_dir()
    if cache_dir is None:
        return []
    env_name = poetry_env_name(directory)
    if env_name is None:
        return []
    try:
        return [
            f.path
            for f in os.scandir(os.path.join(cache_dir, "virtualenvs"))
            if f.name.startswith(f"{env_name}-py")
        ]
    except OSError:
        return []


@lru_cache(maxsize=128)
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
    app_data = os.environ.get("LOCALAPPDATA", None)
    if not app_data:
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
    name = poetry_project_name(directory)
    if name is None:
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
    pyproject_file_path = os.path.join(directory, "pyproject.toml")
    try:
        with open(pyproject_file_path, encoding="utf-8") as pyproject_file:
            pyproject_lines = pyproject_file.readlines()
    except OSError:
        return None
    # Ideally we'd use a proper TOML parser to do this, but there isn't
    # one available in the standard library until Python 3.11. This
    # hacked together parser should work for the vast majority of cases.
    in_tool_poetry_section = False
    for line in pyproject_lines:
        if line.strip() == "[tool.poetry]":
            in_tool_poetry_section = True
            continue
        if line.strip().startswith("["):
            in_tool_poetry_section = False
        if not in_tool_poetry_section:
            continue
        try:
            key, val = (part.strip().strip('"') for part in line.split("="))
        except ValueError:
            continue
        if key == "name":
            return val
    return None


def activator(env_directory: str, args: Args) -> str:
    """Get the activator script for the environment in the given directory."""
    dir_name = "Scripts" if operating_system() == Os.WINDOWS else "bin"
    if args.fish:
        script = "activate.fish"
    elif args.pwsh:
        poetry_dir = poetry_cache_dir()
        if (
            poetry_dir is not None
            and env_directory.startswith(poetry_dir)
            and operating_system() != Os.WINDOWS
        ):
            # In poetry environments on *NIX systems, this activator has a lowercase A.
            script = "activate.ps1"
        else:
            # In venv environments, and Windows poetry environments, this activator has
            # an uppercase A.
            script = "Activate.ps1"
    else:
        script = "activate"
    return os.path.join(env_directory, dir_name, f"{script}")


@lru_cache(maxsize=128)
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
