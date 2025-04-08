"""Tests for the versioning of pyautoenv."""

import re

from packaging.version import VERSION_PATTERN

import pyautoenv


def test_version_is_pep440_compliant():
    pattern = re.compile(VERSION_PATTERN, flags=re.IGNORECASE | re.VERBOSE)

    assert pattern.match(pyautoenv.__version__)
