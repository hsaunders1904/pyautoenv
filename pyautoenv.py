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

When running the script with __debug__, the logging level can be set
using the 'PYAUTOENV_LOG_LEVEL' environment variable. The level can be
set to any supported by Python's 'logging' module.
"""

import os
import sys
from functools import lru_cache
from typing import Iterator, List, TextIO, Union

__version__ = "0.7.1"

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

OS_LINUX = 0
OS_MACOS = 1
OS_WINDOWS = 2


if __debug__:
    import logging

    LOG_LEVEL = "PYAUTOENV_LOG_LEVEL"
    """The level to set the logger at."""

    logging.basicConfig(
        level=getattr(
            logging,
            os.environ.get(LOG_LEVEL, "DEBUG").upper(),
            logging.DEBUG,
        ),
        stream=sys.stderr,
        format="%(name)s: %(levelname)s: [%(asctime)s]: %(message)s",
    )
    logger = logging.getLogger("pyautoenv")


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


def main(sys_args: List[str], stdout: TextIO) -> int:
    """Write commands to activate/deactivate environments."""
    if __debug__:
        logger.debug("main(%s)", sys_args)
    args = parse_args(sys_args, stdout)
    if not os.path.isdir(args.directory):
        logger.warning("path '%s' is not a directory", args.directory)
        return 1
    new_activator = discover_env(args)
    active_env_dir = active_environment()
    if active_env_dir:
        if not new_activator:
            deactivate(stdout)
        elif not activator_in_venv(new_activator, active_env_dir):
            deactivate_and_activate(stdout, new_activator)
    elif new_activator:
        activate(stdout, new_activator)
    return 0


def activate(stream: TextIO, activator: str) -> None:
    """Write the command to execute the given venv activator."""
    command = f". '{activator}'"
    if __debug__:
        logger.debug("activate: '%s'", command)
    stream.write(command)


def deactivate(stream: TextIO) -> None:
    """Write the deactivation command to the given stream."""
    command = "deactivate"
    if __debug__:
        logger.debug("deactivate: '%s'", command)
    stream.write(command)


def deactivate_and_activate(stream: TextIO, new_activator: str) -> None:
    """Write command to deactivate the current env and activate another."""
    command = f"deactivate && . '{new_activator}'"
    if __debug__:
        logger.debug("deactivate_and_activate: '%s'", command)
    stream.write(command)


def activator_in_venv(activator_path: str, venv_dir: str) -> bool:
    """Return True if the given activator is in the given venv directory."""
    activator_venv_dir = os.path.dirname(os.path.dirname(activator_path))
    return os.path.samefile(activator_venv_dir, venv_dir)


def active_environment() -> Union[str, None]:
    """Return the directory of the currently active environment."""
    active_env_dir = os.environ.get("VIRTUAL_ENV")
    if __debug__:
        logger.debug("active_environment: '%s'", active_env_dir)
    return active_env_dir


def parse_args(argv: List[str], stdout: TextIO) -> Args:
    """Parse the sequence of command line arguments."""
    # Avoiding argparse gives a good speed boost and the parsing logic
    # is not too complex. We won't get a full 'bells and whistles' CLI
    # experience, but that's fine for our use-case.
    if not argv:
        return Args(os.getcwd())

    def parse_flag(argv: List[str], flag: str) -> bool:
        try:
            del argv[argv.index(flag)]
        except ValueError:
            return False
        return True

    fish = parse_flag(argv, "--fish")
    pwsh = parse_flag(argv, "--pwsh")
    num_activators = sum([fish, pwsh])
    if num_activators > 1:
        raise ValueError(
            f"zero or one activator flag expected, found {num_activators}",
        )
    if not argv:
        return Args(os.getcwd(), fish=fish, pwsh=pwsh)

    def parse_exit_flag(argv: List[str], flags: List[str]) -> bool:
        return any(f in argv for f in flags)

    if parse_exit_flag(argv, ["-h", "--help"]):
        stdout.write(CLI_HELP)
        sys.exit(0)
    if parse_exit_flag(argv, ["-V", "--version"]):
        stdout.write(f"pyautoenv {__version__}\n")
        sys.exit(0)

    # Ignore empty arguments.
    argv = [a for a in argv if a.strip()]
    if len(argv) > 1:
        raise ValueError(
            f"exactly one positional argument expected, found {len(argv)}",
        )
    directory = os.path.abspath(argv[0]) if argv else os.getcwd()
    return Args(directory=directory, fish=fish, pwsh=pwsh)


def discover_env(args: Args) -> Union[str, None]:
    """Find an environment activator in or above the given directory."""
    while (not dir_is_ignored(args.directory)) and (
        args.directory != os.path.dirname(args.directory)
    ):
        env_activator = get_virtual_env(args)
        if env_activator:
            if __debug__:
                logger.debug("discover_env: '%s'", env_activator)
            return env_activator
        args.directory = os.path.dirname(args.directory)
    if __debug__:
        logger.debug("discover_env: 'None'")
    return None


def dir_is_ignored(directory: str) -> bool:
    """Return True if the given directory is marked to be ignored."""
    return directory in ignored_dirs()


@lru_cache(maxsize=1)
def ignored_dirs() -> List[str]:
    """Get the list of directories to not activate an environment within."""
    dirs = os.environ.get(IGNORE_DIRS)
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
    """
    Return the venv activator within the given directory.

    Return None if the directory does not contain a venv, or the venv
    does not contain a suitable activator script.
    """
    for path in venv_candidate_dirs(args):
        for activate_script in iter_candidate_activators(path, args):
            if __debug__:
                logger.debug("venv_activator: candidate '%s'", activate_script)
            if os.path.isfile(activate_script):
                return activate_script
    return None


def venv_candidate_dirs(args: Args) -> Iterator[str]:
    """Get candidate venv paths within the given directory."""
    for venv_name in venv_dir_names():
        yield os.path.join(args.directory, venv_name)


@lru_cache(maxsize=1)
def venv_dir_names() -> List[str]:
    """Get the possible names for a venv directory."""
    name_list = os.environ.get(VENV_NAMES)
    if name_list:
        return [x for x in name_list.split(";") if x]
    return [".venv"]


def has_poetry_env(directory: str) -> bool:
    """Return true if the given directory contains a poetry project."""
    return os.path.isfile(os.path.join(directory, "poetry.lock"))


def poetry_activator(args: Args) -> Union[str, None]:
    """
    Return the activator associated with a poetry project directory.

    If there are multiple poetry environments, pick the one with the
    latest modification time.
    """
    env_list = poetry_env_list(args.directory)
    if env_list:
        env_dir = max(env_list, key=lambda p: os.stat(p).st_mtime)
        for env_activator in iter_candidate_activators(env_dir, args):
            if __debug__:
                logger.debug(
                    "poetry_activator: candidate: '%s'", env_activator
                )
            if os.path.isfile(env_activator):
                return env_activator
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
    if __debug__:
        logger.debug("poetry_env_list: env name: '%s'", env_name)
    if env_name is None:
        return []
    virtual_env_path = os.path.join(cache_dir, "virtualenvs")
    if __debug__:
        logger.debug("poetry_env_list: venvs path: '%s'", virtual_env_path)
    try:
        return [
            f.path
            for f in os.scandir(virtual_env_path)
            if f.name.startswith(f"{env_name}-py")
        ]
    except OSError:
        if __debug__:
            logger.debug("poetry_env_list: os error:")
            logger.exception("")
        return []


@lru_cache(maxsize=1)
def poetry_cache_dir() -> Union[str, None]:
    """Return the poetry cache directory, or None if it's not found."""
    cache_dir = os.environ.get("POETRY_CACHE_DIR")
    if cache_dir and os.path.isdir(cache_dir):
        return cache_dir
    op_sys = operating_system()
    if op_sys == OS_WINDOWS:
        return windows_poetry_cache_dir()
    if op_sys == OS_MACOS:
        return macos_poetry_cache_dir()
    if op_sys == OS_LINUX:
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
        .lower()[:42]
    )
    normalized_path = os.path.normcase(directory)
    path_hash = hashlib.sha256(normalized_path.encode()).digest()
    b64_hash = base64.urlsafe_b64encode(path_hash).decode()[:8]
    return f"{sanitized_name}-{b64_hash}"


def poetry_project_name(directory: str) -> Union[str, None]:
    """Parse the poetry project name from the given directory."""
    pyproject_file_path = os.path.join(directory, "pyproject.toml")
    try:
        with open(pyproject_file_path, encoding="utf-8") as pyproject_file:
            return parse_name_from_pyproject_file(pyproject_file)
    except OSError:
        return None


def parse_name_from_pyproject_file(file: TextIO) -> Union[str, None]:
    """
    Parse the project name from a pyproject.toml file.

    Return ``None`` if the name cannot be parsed.
    """
    # Ideally we'd use a proper TOML parser to do this, but there isn't
    # one available in the standard library until Python 3.11. This
    # hacked together parser should work for the vast majority of cases.
    for line in file:
        line = line.strip()  # noqa: PLW2901
        if line in ("[project]", "[tool.poetry]"):
            for project_line in file:
                project_line = project_line.lstrip().lstrip("'\"")  # noqa: PLW2901
                if project_line.startswith("["):
                    # New block started without finding the project name.
                    return None
                if not project_line.startswith("name"):
                    continue
                try:
                    key, val = project_line.split("=", maxsplit=1)
                except ValueError:
                    continue
                if key.rstrip().rstrip("'\"") == "name":
                    return val.strip().strip("'\"")
    return None


def iter_candidate_activators(env_directory: str, args: Args) -> Iterator[str]:
    """
    Iterate over candidate activator paths.

    In general we'll know exactly the activator we want given the
    environment directory and the shell we're using. However, in some
    cases there may be slightly different activator script names
    depending on how the venv was created.
    """
    bin_dir = "Scripts" if operating_system() == OS_WINDOWS else "bin"
    if args.fish:
        script = "activate.fish"
    elif args.pwsh:
        # PowerShell activation scripts on *Nix systems have some
        # slightly inconsistent naming. When using Poetry or uv, the
        # activation script is lower case, using the venv module,
        # the script is title case.
        for script in ("activate.ps1", "Activate.ps1"):
            script_path = os.path.join(env_directory, bin_dir, script)
            yield script_path
    else:
        script = "activate"
    yield os.path.join(env_directory, bin_dir, script)


@lru_cache(maxsize=1)
def operating_system() -> Union[int, None]:
    """
    Return the operating system the script's being run on.

    Return 'None' if we're on an operating system we can't handle.
    """
    if sys.platform.startswith("darwin"):
        return OS_MACOS
    if sys.platform.startswith("win"):
        return OS_WINDOWS
    if sys.platform.startswith("linux"):
        return OS_LINUX
    return None


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:], sys.stdout))
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"pyautoenv: error: {exc}\n")
        if __debug__:
            logger.exception("backtrace:")
        sys.exit(1)
