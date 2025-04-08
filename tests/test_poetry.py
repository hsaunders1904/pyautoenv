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
import copy
import os
from io import StringIO
from pathlib import Path
from typing import Dict
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


class PoetryTester(abc.ABC):
    @property
    def python_proj(self) -> Path:
        """The path to the python project we're creating a test env for."""
        return Path("python_project")

    @property
    def not_poetry_proj(self) -> Path:
        """The path to directory that does not contain an poetry project."""
        return Path("not_a_poetry_proj")

    @abc.abstractproperty
    def os(self) -> int:
        """The operating system the class is testing on."""

    @abc.abstractproperty
    def flag(self) -> str:
        """The command line flag to select the activator."""

    @abc.abstractproperty
    def activator(self) -> Path:
        """The path of the activator script relative to the venv dir."""

    @abc.abstractproperty
    def poetry_cache(self) -> Path:
        """The path to the directory containing poetry virtual environments."""

    @abc.abstractproperty
    def env(self) -> Dict[str, str]:
        """The environment variables to be present during the test."""

    @property
    def venv_dir(self) -> Path:
        """The path to the virtualenv for the test class's python project."""
        # Poetry uses a hash of the path to get the venv name, as the
        # path separator will be different on Windows and Posix, the
        # venv name will be different when these tests are run on
        # Windows and Posix.
        if os.name == "nt":
            return self.poetry_cache / "python_project-1IhmuXCK-py3.11"
        return self.poetry_cache / "python_project-frtSrewI-py3.11"

    @pytest.fixture(autouse=True)
    def fs(self, fs: FakeFilesystem) -> FakeFilesystem:
        """Create a mock filesystem for every test in this class."""
        fs = make_poetry_project(fs, "python_project", self.python_proj)
        fs.create_dir(self.python_proj / "src")
        fs.create_dir(self.not_poetry_proj)
        fs.create_file(self.venv_dir / "bin" / "activate")
        fs.create_file(self.venv_dir / "bin" / "activate.ps1")
        fs.create_file(self.venv_dir / "bin" / "activate.fish")
        fs.create_file(self.venv_dir / "Scripts" / "Activate.ps1")
        return fs

    def setup_method(self):
        pyautoenv.poetry_cache_dir.cache_clear()
        self.os_patch = mock.patch(OPERATING_SYSTEM, return_value=self.os)
        self.os_patch.start()
        os.environ = copy.deepcopy(self.env)  # noqa: B003

    def teardown_method(self):
        self.os_patch.stop()

    def test_activates_given_poetry_dir(self):
        stdout = StringIO()

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert stdout.getvalue() == f". '{self.venv_dir / self.activator}'"

    def test_activates_given_poetry_dir_in_parent(self):
        stdout = StringIO()

        assert pyautoenv.main(["python_project/src", self.flag], stdout) == 0
        assert stdout.getvalue() == f". '{self.venv_dir / self.activator}'"

    def test_nothing_happens_given_not_venv_dir_and_not_active(self):
        stdout = StringIO()

        assert (
            pyautoenv.main([str(self.not_poetry_proj), self.flag], stdout) == 0
        )
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.venv_dir)

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_in_parent_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.venv_dir)

        assert (
            pyautoenv.main([str(self.python_proj / "src"), self.flag], stdout)
            == 0
        )
        assert not stdout.getvalue()

    def test_deactivate_given_active_and_not_venv_dir(self):
        stdout = StringIO()
        activate_venv(self.venv_dir)

        assert (
            pyautoenv.main([str(self.not_poetry_proj), self.flag], stdout) == 0
        )
        assert stdout.getvalue() == "deactivate"

    @pytest.mark.parametrize("name_in_project_section", [True, False])
    def test_deactivate_and_activate_switching_to_new_poetry_env(
        self,
        fs,
        name_in_project_section,
    ):
        stdout = StringIO()
        activate_venv(self.venv_dir)
        fs = make_poetry_project(
            fs,
            "pyproj2",
            Path("pyproj2"),
            name_in_project_section=name_in_project_section,
        )
        if os.name == "nt":
            new_venv = self.poetry_cache / "pyproj2-lbvqfyck-py3.8"
        else:
            new_venv = self.poetry_cache / "pyproj2-NKNCcI25-py3.8"
        new_activate = new_venv / self.activator
        fs.create_file(new_activate)

        assert pyautoenv.main(["pyproj2", self.flag], stdout=stdout) == 0
        assert stdout.getvalue() == f"deactivate && . {new_activate}"

    def test_does_nothing_if_activate_script_is_not_file(self, fs):
        stdout = StringIO()
        # delete the activate script
        fs.remove(self.venv_dir / self.activator)

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_poetry_cache_dir_does_not_exist(self, fs):
        stdout = StringIO()
        fs.remove_object(str(self.venv_dir))

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_poetry_cache_dir_env_var_used_if_set_and_dir_exists(self, fs):
        stdout = StringIO()
        fs = make_poetry_project(fs, "pyproj2", Path("pyproj2"))
        new_poetry_cache_dir = Path("venv")
        new_venv_dir = new_poetry_cache_dir / "virtualenvs"
        if os.name == "nt":
            new_activator = (
                new_venv_dir / "pyproj2-lbvqfyck-py3.8" / self.activator
            )
        else:
            new_activator = (
                new_venv_dir / "pyproj2-NKNCcI25-py3.8" / self.activator
            )
        fs.create_file(new_activator)
        os.environ["POETRY_CACHE_DIR"] = str(new_poetry_cache_dir)

        assert pyautoenv.main(["pyproj2", self.flag], stdout) == 0
        assert stdout.getvalue() == f". '{new_activator}'"

    def test_poetry_cache_dir_env_var_not_used_if_set_and_does_not_exist(self):
        stdout = StringIO()
        os.environ["POETRY_CACHE_DIR"] = "/not/a/dir"

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert stdout.getvalue() == f". '{self.venv_dir / self.activator}'"

    def test_does_nothing_given_poetry_cache_dir_does_not_exist(self, fs):
        stdout = StringIO()
        fs.remove_object(str(self.poetry_cache))

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert not stdout.getvalue()

    @pytest.mark.parametrize(
        "pyproject_toml",
        [
            '[tool.poetry]\nnot_name = "python_project"',
            "[tool.poetry]\nname",
            (
                "[tool.poetry]\n"
                'version = "0.2.0"\n'
                "\n"
                "[tool.black]\n"
                'name = "python_project"\n'
            ),
        ],
    )
    def test_nothing_happens_given_name_cannot_be_parsed_from_pyproject(
        self,
        pyproject_toml,
    ):
        assert (self.python_proj / "pyproject.toml").write_text(pyproject_toml)
        stdout = StringIO()

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_pyproject_toml_does_not_exist(self, fs):
        fs.remove(self.python_proj / "pyproject.toml")
        stdout = StringIO()

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_unknown_operating_system(self):
        stdout = StringIO()

        with mock.patch(OPERATING_SYSTEM, new=mock.Mock(return_value=None)):
            assert (
                pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
            )
        assert not stdout.getvalue()

    def test_nothing_happens_given_active_env_and_relative_subdirectory(self):
        stdout = StringIO()
        os.chdir(self.python_proj)
        activate_venv(self.venv_dir)

        assert pyautoenv.main(["src", self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_changing_to_ignored_directory(self):
        stdout = StringIO()
        ignore = f"some_dir;{self.python_proj.resolve()}"
        os.environ[pyautoenv.IGNORE_DIRS] = ignore

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_change_to_child_of_ignored_directory(self):
        stdout = StringIO()
        ignore = f"some_dir;{self.python_proj.resolve()}"
        os.environ[pyautoenv.IGNORE_DIRS] = ignore

        assert (
            pyautoenv.main([str(self.python_proj / "src"), self.flag], stdout)
            == 0
        )
        assert not stdout.getvalue()

    def test_deactivate_given_changing_to_ignored_directory(self):
        stdout = StringIO()
        activate_venv(self.venv_dir)
        ignore = f"some_dir;{self.python_proj.resolve()}"
        os.environ[pyautoenv.IGNORE_DIRS] = ignore

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert stdout.getvalue() == "deactivate"


class PoetryLinuxTester(PoetryTester):
    env = {
        "HOME": str(root_dir() / "home" / "user"),
        "USERPROFILE": str(root_dir() / "home" / "user"),
    }
    os = pyautoenv.Os.LINUX
    poetry_cache = (
        root_dir() / "home" / "user" / ".cache" / "pypoetry" / "virtualenvs"
    )


class TestPoetryBashLinux(PoetryLinuxTester):
    activator = Path("bin/activate")
    flag = ""


class TestPoetryPwshLinux(PoetryLinuxTester):
    activator = Path("bin/activate.ps1")
    flag = "--pwsh"


class TestPoetryFishLinux(PoetryLinuxTester):
    activator = Path("bin/activate.fish")
    flag = "--fish"


class PoetryMacosTester(PoetryTester):
    env = {
        "HOME": str(root_dir() / "Users" / "user"),
        "USERPROFILE": str(root_dir() / "Users" / "user"),
    }
    os = pyautoenv.Os.MACOS
    poetry_cache = (
        root_dir()
        / "Users"
        / "user"
        / "Library"
        / "Caches"
        / "pypoetry"
        / "virtualenvs"
    )


class TestPoetryBashMacos(PoetryMacosTester):
    activator = Path("bin/activate")
    flag = ""


class TestPoetryPwshMacos(PoetryMacosTester):
    activator = Path("bin/activate.ps1")
    flag = "--pwsh"


class TestPoetryFishMacos(PoetryMacosTester):
    activator = Path("bin/activate.fish")
    flag = "--fish"


class TestPoetryPwshWindows(PoetryTester):
    activator = Path("Scripts/Activate.ps1")
    env = {"LOCALAPPDATA": str(root_dir() / "Users/user/AppData/Local")}
    flag = "--pwsh"
    os = pyautoenv.Os.WINDOWS
    poetry_cache = (
        root_dir()
        / "Users"
        / "user"
        / "AppData"
        / "Local"
        / "pypoetry"
        / "Cache"
        / "virtualenvs"
    )

    def test_nothing_happens_given_app_data_env_var_not_set(self):
        del os.environ["LOCALAPPDATA"]
        stdout = StringIO()

        assert pyautoenv.main([str(self.python_proj)], stdout) == 0
        assert not stdout.getvalue()
