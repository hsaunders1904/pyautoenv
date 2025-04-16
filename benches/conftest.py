"""Pytest configuration for benchmarks."""

import base64
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest
from typing_extensions import Buffer

import pyautoenv
from benches.tools import environment_variable, make_venv

POETRY_PYPROJECT = """[project]
name = "{project_name}"
version = "0.1.0"
description = ""
authors = [
    {{name = "A Name",email = "someemail@abc.com"}}
]
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
]

[tool.poetry]
packages = [{{include = "{project_name}", from = "src"}}]

[build-system]
requires = ["poetry-core>=2.0.0,<3.0.0"]
build-backend = "poetry.core.masonry.api"
"""


@pytest.fixture(autouse=True)
def reset_caches() -> None:
    """Reset the LRU caches in pyautoenv."""
    pyautoenv.poetry_cache_dir.cache_clear()
    pyautoenv.operating_system.cache_clear()


@pytest.fixture(autouse=True, scope="module")
def capture_logging() -> Generator[None, None, None]:
    """Capture all logging as benchmarks are extremely noisy."""
    if __debug__:
        logging_disable = pyautoenv.logger.disabled
        try:
            pyautoenv.logger.disabled = True
            yield
        finally:
            pyautoenv.logger.disabled = logging_disable
    else:
        yield None


@pytest.fixture(autouse=True, scope="module")
def deactivate_venvs() -> Generator[None, None, None]:
    """Fixture to 'deactivate' any currently active virtualenvs."""
    original_venv = os.environ.get("VIRTUAL_ENV")
    try:
        os.environ.pop("VIRTUAL_ENV", None)
        yield
    finally:
        if original_venv is not None:
            os.environ["VIRTUAL_ENV"] = original_venv


@pytest.fixture
def venv(tmp_path: Path) -> Path:
    """Fixture returning a venv in a temporary directory."""
    return make_venv(tmp_path / "venv_fixture")


@dataclass
class PoetryVenvFixture:
    """Poetry virtual environment fixture data."""

    project_dir: Path
    venv_dir: Path


@pytest.fixture
def poetry_venv(tmp_path: Path) -> Generator[PoetryVenvFixture, None, None]:
    """Create a poetry virtual environment and associated project."""
    # Make poetry's cache directory.
    cache_dir = tmp_path / "pypoetry"
    cache_dir.mkdir()
    virtualenvs_dir = cache_dir / "virtualenvs"
    virtualenvs_dir.mkdir()

    # Create a virtual environment within the cache directory.
    project_name = "benchmark"
    py_version = ".".join(
        str(v) for v in [sys.version_info.major, sys.version_info.minor]
    )
    fake_hash = "SOMEHASH" + "A" * (32 - 8)
    venv_name = f"{project_name}-{fake_hash[:8]}-py{py_version}"
    venv_dir = make_venv(virtualenvs_dir, venv_name)

    # Create a poetry project directory with a lockfile and pyproject.
    project_dir = tmp_path / project_name
    project_dir.mkdir()
    pyproject = project_dir / "pyproject.toml"
    with pyproject.open("w") as f:
        f.write(POETRY_PYPROJECT.format(project_name=project_name))
    (project_dir / "poetry.lock").touch()

    # Mock base64 encode to return a fixed hash so the poetry env is
    # discoverable. Actually run the encoder so the benchmark is more
    # representative, but return a fixed value.
    real_b64_encode = base64.urlsafe_b64encode

    def b64encode(s: Buffer) -> bytes:
        real_b64_encode(s)
        return fake_hash.encode()

    with (
        mock.patch("base64.urlsafe_b64encode", new=b64encode),
        environment_variable("POETRY_CACHE_DIR", str(cache_dir)),
    ):
        yield PoetryVenvFixture(project_dir, venv_dir)
