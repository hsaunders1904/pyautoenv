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
import os
import re
from io import StringIO
from pathlib import Path
from typing import Union
from unittest import mock

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import pyautoenv

OPERATING_SYSTEM = "pyautoenv.operating_system"


def test_parse_args_directory_is_cwd_by_default():
    args = pyautoenv.parse_args([])

    assert args.directory == Path.cwd()


def test_parse_args_directory_is_set():
    args = pyautoenv.parse_args(["/some/dir"])

    assert args.directory == Path("/some/dir")


def test_parse_args_version_prints_version_and_exits(capsys):
    with pytest.raises(SystemExit):
        pyautoenv.parse_args(["--version"])
    stdout = capsys.readouterr().out
    assert re.match(r"pyautoenv [0-9]+\.[0-9]+\.[0-9](\.\w+)?\n", stdout)


def test_main_does_nothing_given_directory_does_not_exist():
    stdout = StringIO()

    assert pyautoenv.main(["/not/a/dir"], stdout) == 1
    assert not stdout.getvalue()


@pytest.mark.parametrize(
    ("os_name", "enum_value"),
    [
        ("Linux", pyautoenv.Os.LINUX),
        ("Darwin", pyautoenv.Os.MACOS),
        ("Windows", pyautoenv.Os.WINDOWS),
        ("Java", None),
    ],
)
def test_operating_system_returns_enum_based_on_sys_platform(
    os_name,
    enum_value,
):
    with mock.patch("pyautoenv.platform.system", return_value=os_name):
        assert pyautoenv.operating_system() == enum_value


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
        'names = "not this one!"\n'
        f'name = "{name}"\n'
        'version = "0.2.0"\n',
    )
    return fs


class TestVenv:
    OS_NAME_ACTIVATORS = [
        (pyautoenv.Os.WINDOWS, "Scripts/Activate.ps1"),
        (pyautoenv.Os.LINUX, "bin/activate"),
        (pyautoenv.Os.MACOS, "bin/activate"),
    ]
    PY_PROJ = Path("/python_project")
    VENV_DIR = PY_PROJ / ".venv"

    def setup_method(self):
        os.environ = {}  # noqa: B003

    @pytest.fixture(autouse=True)
    def fs(self, fs: FakeFilesystem) -> FakeFilesystem:
        """Create a mock filesystem for every test in this class."""
        fs.create_dir(self.PY_PROJ / "src")
        fs.create_file(self.VENV_DIR / "bin" / "activate")
        fs.create_file(self.VENV_DIR / "Scripts" / "Activate.ps1")
        fs.create_dir("not_a_venv")
        return fs

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_given_venv_dir(self, os_name, activator):
        stdout = StringIO()

        with mock.patch(OPERATING_SYSTEM, return_value=os_name):
            assert pyautoenv.main([str(self.PY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_if_venv_in_parent(self, os_name, activator):
        stdout = StringIO()

        with mock.patch(OPERATING_SYSTEM, return_value=os_name):
            assert pyautoenv.main([str(self.PY_PROJ / "src")], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    def test_nothing_happens_given_venv_dir_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.PY_PROJ)], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_in_parent_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.PY_PROJ / "src")], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_not_venv_dir_and_venv_not_active(self):
        stdout = StringIO()

        assert pyautoenv.main(["not_a_venv"], stdout) == 0
        assert not stdout.getvalue()

    def test_deactivate_given_active_and_not_venv_dir(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main(["not_a_venv"], stdout) == 0
        assert stdout.getvalue() == "deactivate"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_deactivate_and_activate_switching_to_new_venv(
        self,
        fs,
        os_name,
        activator,
    ):
        stdout = StringIO()
        new_venv_activate = Path("/pyproj2/.venv") / activator
        fs.create_file(new_venv_activate)
        activate_venv(self.VENV_DIR)

        with mock.patch(OPERATING_SYSTEM, return_value=os_name):
            assert pyautoenv.main(["pyproj2"], stdout=stdout) == 0
        assert stdout.getvalue() == f"deactivate && . {new_venv_activate}"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    @mock.patch("pyautoenv.poetry_env_path")
    def test_deactivate_and_activate_switching_to_poetry(
        self,
        poetry_env_mock,
        fs,
        os_name,
        activator,
    ):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)
        # create a poetry venv to switch into
        poetry_env = Path("poetry_proj-X-py3.8")
        poetry_env_mock.return_value = poetry_env
        fs = make_poetry_project(fs, "project", Path("/poetry_proj"))
        fs.create_file(poetry_env / activator)

        with mock.patch(OPERATING_SYSTEM, return_value=os_name):
            assert pyautoenv.main(["poetry_proj"], stdout) == 0
        assert stdout.getvalue() == f"deactivate && . {poetry_env / activator}"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_does_nothing_if_activate_script_is_not_file(
        self,
        fs,
        os_name,
        activator,
    ):
        stdout = StringIO()
        # venv directory exists, but not the activate script
        fs.remove(self.VENV_DIR / activator)

        with mock.patch(OPERATING_SYSTEM, return_value=os_name):
            assert pyautoenv.main([str(self.PY_PROJ)], stdout) == 0
        assert not stdout.getvalue()


class PoetryTester:
    """
    Base class for testing against poetry environments.

    Inherit from this to test against different OSs, where different
    environment variables must be set and different paths are expected.

    When inheriting you must set class-level variables:

    * ACTIVATOR: Path
        the relative path from the venv directory to the 'activate' script
    * OS: pyautoenv.OS
        the OS the test is for
    * POETRY_DIR: Path
        the path to the poetry project
    * VENV_DIR: Path
        the path to the poetry virtual environment directory
    """

    ACTIVATOR: Path
    OS: pyautoenv.Os
    POETRY_DIR: Path
    VENV_DIR: Path
    NOT_POETRY_DIR = "not_a_poetry_project"
    POETRY_PROJ = Path("/python_project")

    def setup_method(self):
        self.os_patch = mock.patch(OPERATING_SYSTEM, return_value=self.OS)
        self.os_patch.start()

    def teardown_method(self):
        self.os_patch.stop()

    def test_activates_given_poetry_dir(self):
        stdout = StringIO()

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / self.ACTIVATOR}"

    def test_activates_given_poetry_dir_in_parent(self):
        stdout = StringIO()

        assert pyautoenv.main(["python_project/src"], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / self.ACTIVATOR}"

    def test_nothing_happens_given_not_venv_dir_and_not_active(self):
        stdout = StringIO()

        assert pyautoenv.main([self.NOT_POETRY_DIR], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_in_parent_is_already_active(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.POETRY_PROJ / "src")], stdout) == 0
        assert not stdout.getvalue()

    def test_deactivate_given_active_and_not_venv_dir(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([self.NOT_POETRY_DIR], stdout) == 0
        assert stdout.getvalue() == "deactivate"

    def test_deactivate_and_activate_switching_to_new_poetry_env(self, fs):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)
        fs = make_poetry_project(fs, "pyproj2", Path("pyproj2"))
        new_venv = self.POETRY_DIR / "virtualenvs" / "pyproj2-NKNCcI25-py3.8"
        new_activate = new_venv / self.ACTIVATOR
        fs.create_file(new_activate)

        assert pyautoenv.main(["pyproj2"], stdout=stdout) == 0
        assert stdout.getvalue() == f"deactivate && . {new_activate}"

    def test_does_nothing_if_activate_script_is_not_file(self, fs):
        stdout = StringIO()
        # delete the activate script
        fs.remove(self.VENV_DIR / self.ACTIVATOR)

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_poetry_cache_dir_does_not_exist(self, fs):
        stdout = StringIO()
        fs.remove_object(str(self.VENV_DIR))

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()

    def test_poetry_cache_dir_env_var_used_if_set_and_dir_exists(self, fs):
        stdout = StringIO()
        fs = make_poetry_project(fs, "pyproj2", Path("pyproj2"))
        new_venv_dir = Path("venv")
        new_activator = (
            new_venv_dir
            / "virtualenvs"
            / "pyproj2-NKNCcI25-py3.8"
            / self.ACTIVATOR
        )
        fs.create_file(new_activator)
        os.environ["POETRY_CACHE_DIR"] = str(new_venv_dir)

        assert pyautoenv.main(["pyproj2"], stdout) == 0
        assert stdout.getvalue() == f". {new_activator}"

    def test_poetry_cache_dir_env_var_not_used_if_set_and_does_not_exist(self):
        stdout = StringIO()
        os.environ["POETRY_CACHE_DIR"] = "/not/a/dir"

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / self.ACTIVATOR}"

    def test_does_nothing_given_poetry_cache_dir_does_not_exist(self, fs):
        stdout = StringIO()
        fs.remove_object(str(self.POETRY_DIR))

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
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
        assert (self.POETRY_PROJ / "pyproject.toml").write_text(pyproject_toml)
        stdout = StringIO()

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()


class TestPoetryWindows(PoetryTester):
    ACTIVATOR = Path("Scripts") / "Activate.ps1"
    OS = pyautoenv.Os.WINDOWS
    POETRY_DIR = (
        Path("C") / "Users" / "user" / "AppData" / "Local" / "pypoetry"
    )
    VENV_DIR = POETRY_DIR / "virtualenvs" / "python_project-frtSrewI-py3.11"

    @pytest.fixture(autouse=True)
    def fs(self, fs: FakeFilesystem) -> FakeFilesystem:
        """Create a mock filesystem for every test in this class."""
        fs = make_poetry_project(fs, "python_project", self.POETRY_PROJ)
        fs.create_dir(self.POETRY_PROJ / "src")
        fs.create_dir(self.NOT_POETRY_DIR)
        fs.create_file(self.VENV_DIR / "Scripts" / "Activate.ps1")
        return fs

    def setup_method(self):
        super().setup_method()
        os.environ = {  # noqa: B003
            "LOCALAPPDATA": "C/Users/user/AppData/Local",
        }


class TestPoetryMacOs(PoetryTester):
    ACTIVATOR = Path("bin") / "activate"
    OS = pyautoenv.Os.MACOS
    POETRY_DIR = (
        Path("/") / "Users" / "user" / "Library" / "Caches" / "pypoetry"
    )
    VENV_DIR = POETRY_DIR / "virtualenvs" / "python_project-frtSrewI-py3.11"

    @pytest.fixture(autouse=True)
    def fs(self, fs: FakeFilesystem) -> FakeFilesystem:
        """Create a mock filesystem for every test in this class."""
        fs = make_poetry_project(fs, "python_project", self.POETRY_PROJ)
        fs.create_dir(self.POETRY_PROJ / "src")
        fs.create_dir(self.NOT_POETRY_DIR)
        fs.create_file(self.VENV_DIR / "bin" / "activate")
        return fs

    def setup_method(self):
        super().setup_method()
        os.environ = {"HOME": "/Users/user/"}  # noqa: B003


class TestPoetryLinux(PoetryTester):
    ACTIVATOR = Path("bin") / "activate"
    OS = pyautoenv.Os.LINUX
    POETRY_DIR = Path("/") / "Users" / "user" / ".cache" / "pypoetry"
    VENV_DIR = POETRY_DIR / "virtualenvs" / "python_project-frtSrewI-py3.11"

    @pytest.fixture(autouse=True)
    def fs(self, fs: FakeFilesystem) -> FakeFilesystem:
        """Create a mock filesystem for every test in this class."""
        fs = make_poetry_project(fs, "python_project", self.POETRY_PROJ)
        fs.create_dir(self.POETRY_PROJ / "src")
        fs.create_dir(self.NOT_POETRY_DIR)
        fs.create_file(self.VENV_DIR / "bin" / "activate")
        return fs

    def setup_method(self):
        super().setup_method()
        os.environ = {"HOME": "/Users/user/"}  # noqa: B003
