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
"""Utility functions for tests."""

import inspect
import os
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Protocol, Union

from pyfakefs.fake_filesystem import FakeFilesystem

OPERATING_SYSTEM = "pyautoenv.operating_system"


def activate_venv(venv_dir: Union[str, Path]) -> None:
    """Activate the venv at the given path."""
    os.environ["VIRTUAL_ENV"] = str(venv_dir)


def make_poetry_project(
    fs: FakeFilesystem,
    name: str,
    path: Path,
    *,
    name_in_project_section: bool = False,
) -> FakeFilesystem:
    """Create a poetry project on the given file system."""
    fs.create_file(path / "poetry.lock")
    fs.create_file(path / "pyproject.toml").set_contents(
        "[build-system]\n"
        'requires = ["poetry-core>=1.0.0"]\n'
        'build-backend = "poetry.core.masonry.api"\n'
        "\n"
        + ("[project]\n" if name_in_project_section else "[tool.poetry]\n")
        + "# comment\n"
        'names = "not this one!"\n'
        f'name = "{name}"\n'
        'version = "0.2.0"\n'
        "some_list = [\n"
        "    'val1',\n"
        "    'val2',\n"
        "]\n"
        "\n"
        "[tool.ruff]\n"
        "select = [\n"
        '    "F",\n'
        '    "W",\n'
        "]\n",
    )
    return fs


def root_dir() -> Path:
    """
    Return the root directory for the current system.

    This is useful for OS-compatibility when we're building paths in
    our tests.
    """
    return Path(os.path.abspath("/"))


def clear_lru_caches(module: ModuleType) -> None:
    """Clear all the caches in ``lru_cache`` decorated functions."""
    for func in _find_lru_cached_functions(module):
        func.cache_clear()


class _LruCachedFunction(Protocol):
    def cache_clear(self) -> None: ...


@lru_cache
def _find_lru_cached_functions(module: ModuleType) -> list[_LruCachedFunction]:
    """Find all function that are decorated with ``lru_cache``."""
    return [
        func
        for _, func in inspect.getmembers(
            module, lambda x: hasattr(x, "cache_clear")
        )
    ]
