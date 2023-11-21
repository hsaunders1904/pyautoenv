"""Tests for the versioning of pyautoenv."""

import re
from pathlib import Path

import toml
from packaging.version import VERSION_PATTERN

import pyautoenv


def test_version_is_pep440_compliant():
    pattern = re.compile(VERSION_PATTERN, flags=re.IGNORECASE | re.VERBOSE)

    assert pattern.match(pyautoenv.__version__)


def test_version_in_pyproject_eq_to_module_version():
    pyproject_file = Path(__file__).parent.parent / "pyproject.toml"
    pyproject = toml.loads(pyproject_file.read_text())
    pyproject_version = pyproject["tool"]["poetry"]["version"]

    assert pyautoenv.__version__ == pyproject_version
