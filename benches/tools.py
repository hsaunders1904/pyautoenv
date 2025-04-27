"""Utilities for benchmarks."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import virtualenv


def make_venv(path: Path, venv_name: str = ".venv") -> Path:
    """Make a virtual environment in the given directory."""
    venv_dir = path / venv_name
    virtualenv.cli_run([str(venv_dir)])
    return venv_dir


@contextmanager
def environment_variable(
    variable: str, value: str
) -> Generator[None, None, None]:
    """Set an environment variable within a context."""
    original_value = os.environ.get(variable)
    try:
        os.environ[variable] = value
        yield
    finally:
        if original_value:
            os.environ[variable] = original_value
        else:
            os.environ.pop(variable)


@contextmanager
def working_directory(path: Path) -> Generator[None, None, None]:
    """Set the current working directory within a context."""
    original_path = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original_path)


@contextmanager
def venv_active(venv_dir: Path) -> Generator[None, None, None]:
    """Activate a virtual environment within a context."""
    if not venv_dir.is_dir():
        raise ValueError(f"Directory '{venv_dir}' does not exist.")
    with environment_variable("VIRTUAL_ENV", str(venv_dir)):
        yield
