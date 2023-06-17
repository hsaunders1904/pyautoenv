"""Utility functions for tests."""

import os
from pathlib import Path
from typing import Union

from pyfakefs.fake_filesystem import FakeFilesystem

OPERATING_SYSTEM = "pyautoenv.operating_system"


def activate_venv(venv_dir: Union[str, Path]) -> None:
    """Activate the venv at the given path."""
    os.environ["VIRTUAL_ENV"] = str(venv_dir)


def make_poetry_project(
    fs: FakeFilesystem,
    name: str,
    path: Path,
) -> FakeFilesystem:
    """Create a poetry project on the given file system."""
    fs.create_file(path / "poetry.lock")
    fs.create_file(path / "pyproject.toml").set_contents(
        "[build-system]\n"
        'requires = ["poetry-core>=1.0.0"]\n'
        'build-backend = "poetry.core.masonry.api"\n'
        "\n"
        "[tool.poetry]\n"
        "# comment\n"
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
