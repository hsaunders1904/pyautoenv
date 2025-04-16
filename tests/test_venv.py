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
import abc
import os
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import pyautoenv
from tests.tools import (
    OPERATING_SYSTEM,
    activate_venv,
    make_poetry_project,
    root_dir,
)


class VenvTester(abc.ABC):
    PY_PROJ = root_dir() / "python_project"
    VENV_DIR = PY_PROJ / ".venv"

    @property
    @abc.abstractmethod
    def os(self) -> int:
        """The operating system the class is testing on."""

    @property
    @abc.abstractmethod
    def flag(self) -> str:
        """The command line flag to select the activator."""

    @property
    @abc.abstractmethod
    def activator(self) -> str:
        """The name of the activator script."""

    def setup_method(self):
        pyautoenv.poetry_cache_dir.cache_clear()
        os.environ = {}  # noqa: B003
        self.os_patch = mock.patch(OPERATING_SYSTEM, return_value=self.os)
        self.os_patch.start()

    def teardown_method(self):
        self.os_patch.stop()

    @pytest.fixture(autouse=True)
    def fs(self, fs: FakeFilesystem) -> FakeFilesystem:
        """Create a mock filesystem for every test in this class."""
        fs.create_dir(self.PY_PROJ / "src")
        fs.create_file(self.VENV_DIR / "bin" / "activate")
        fs.create_file(self.VENV_DIR / "bin" / "activate.fish")
        fs.create_file(self.VENV_DIR / "bin" / "activate.ps1")
        fs.create_file(self.VENV_DIR / "Scripts" / "activate")
        fs.create_file(self.VENV_DIR / "Scripts" / "Activate.ps1")
        fs.create_dir("not_a_venv")
        return fs

    def test_activates_given_venv_dir(self):
        stdout = StringIO()

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert stdout.getvalue() == f". '{self.VENV_DIR / self.activator}'"

    def test_activates_if_venv_in_parent(self):
        stdout = StringIO()

        assert (
            pyautoenv.main([str(self.PY_PROJ / "src"), self.flag], stdout) == 0
        )
        assert stdout.getvalue() == f". '{self.VENV_DIR / self.activator}'"

    def test_nothing_happens_given_venv_dir_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_in_parent_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.PY_PROJ / "src")], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_not_venv_dir_and_venv_not_active(self):
        stdout = StringIO()

        assert pyautoenv.main(["not_a_venv", self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_deactivate_given_active_and_not_venv_dir(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main(["not_a_venv", self.flag], stdout) == 0
        assert stdout.getvalue() == "deactivate"

    def test_deactivate_and_activate_switching_to_new_venv(self, fs):
        stdout = StringIO()
        new_venv_activate = root_dir() / "pyproj2" / ".venv" / self.activator
        fs.create_file(new_venv_activate)
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main(["pyproj2", self.flag], stdout=stdout) == 0
        assert stdout.getvalue() == f"deactivate && . '{new_venv_activate}'"

    @mock.patch("pyautoenv.poetry_activator")
    def test_deactivate_and_activate_switching_to_poetry(
        self,
        poetry_env_mock,
        fs,
    ):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)
        # create a poetry venv to switch into
        poetry_env = Path("poetry_proj-X-py3.8")
        activator = poetry_env / self.activator
        poetry_env_mock.return_value = activator
        fs = make_poetry_project(fs, "project", Path("/poetry_proj"))
        fs.create_file(activator)

        assert pyautoenv.main(["poetry_proj", self.flag], stdout) == 0
        assert stdout.getvalue() == f"deactivate && . '{activator}'"

    def test_does_nothing_if_activate_script_is_not_file(self, fs):
        stdout = StringIO()
        # venv directory exists, but not the activate script
        fs.remove(self.VENV_DIR / self.activator)

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_first_existing_venv_name_taken_from_environment_variable(
        self,
        fs,
    ):
        stdout = StringIO()
        venv_activate = self.PY_PROJ / "venv" / self.activator
        fs.create_file(venv_activate)
        fs.create_file(self.PY_PROJ / "other_venv" / self.activator)
        os.environ["PYAUTOENV_VENV_NAME"] = "foo;venv;other_venv"

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert stdout.getvalue() == f". '{venv_activate}'"

    def test_venv_dir_name_environment_variable_ignored_if_set_but_empty(self):
        stdout = StringIO()
        os.environ["PYAUTOENV_VENV_NAME"] = ""

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert stdout.getvalue() == f". '{self.VENV_DIR / self.activator}'"

    def test_nothing_happens_given_changing_to_ignored_directory(self):
        stdout = StringIO()
        ignore = f"some_dir;{self.PY_PROJ.resolve()}"
        os.environ[pyautoenv.IGNORE_DIRS] = ignore

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_change_to_child_of_ignored_directory(self):
        stdout = StringIO()
        ignore = f"some_dir;{self.PY_PROJ.resolve()}"
        os.environ[pyautoenv.IGNORE_DIRS] = ignore

        assert (
            pyautoenv.main([str(self.PY_PROJ / "src"), self.flag], stdout) == 0
        )
        assert not stdout.getvalue()

    def test_deactivate_given_changing_to_ignored_directory(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)
        ignore = f"some_dir;{self.PY_PROJ.resolve()}"
        os.environ[pyautoenv.IGNORE_DIRS] = ignore

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert stdout.getvalue() == "deactivate"


class TestVenvBashLinux(VenvTester):
    activator = "bin/activate"
    flag = ""
    os = pyautoenv.Os.LINUX


class TestVenvPwshLinux(VenvTester):
    activator = "bin/activate.ps1"
    flag = "--pwsh"
    os = pyautoenv.Os.LINUX


class TestVenvFishLinux(VenvTester):
    activator = "bin/activate.fish"
    flag = "--fish"
    os = pyautoenv.Os.LINUX


class TestVenvPwshWindows(VenvTester):
    activator = "Scripts/Activate.ps1"
    flag = "--pwsh"
    os = pyautoenv.Os.WINDOWS
