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
from subprocess import CalledProcessError
from typing import Union
from unittest import mock

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import pyautoenv

OS_NAME = "pyautoenv.os.name"
OS_NAME_ACTIVATORS = [
    ("nt", "Scripts/Activate.ps1"),
    ("posix", "bin/activate"),
]


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


def activate_venv(venv_dir: Union[str, Path]) -> None:
    """Activate the venv at the given path."""
    os.environ["VIRTUAL_ENV"] = str(venv_dir)


class TestVenv:
    PY_PROJ = Path("python_project")
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

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main([str(self.PY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_if_venv_in_parent(self, os_name, activator):
        stdout = StringIO()

        with mock.patch(OS_NAME, new=os_name):
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
        new_venv_activate = Path("pyproj2/.venv") / activator
        fs.create_file(new_venv_activate)
        activate_venv(self.VENV_DIR)

        with mock.patch(OS_NAME, new=os_name):
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
        fs.create_file("poetry_proj/poetry.lock")
        fs.create_file(poetry_env / activator)

        with mock.patch(OS_NAME, new=os_name):
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

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main([str(self.PY_PROJ)], stdout) == 0
        assert not stdout.getvalue()


class TestPoetry:
    POETRY_PROJ = Path("python_project")
    VENV_DIR = Path("/virtualenvs/python_project-X-py3.11")

    def setup_method(self):
        os.environ = {}  # noqa: B003
        self.env_path_patch = mock.patch(
            "pyautoenv.poetry_env_list_path_subprocess",
        )
        self.env_list_path_mock = self.env_path_patch.start()

    def teardown_method(self):
        self.env_path_patch.stop()

    @pytest.fixture(autouse=True)
    def fs(self, fs: FakeFilesystem) -> FakeFilesystem:
        """Create a mock filesystem for every test in this class."""
        fs.create_file(self.POETRY_PROJ / "poetry.lock")
        fs.create_dir(self.POETRY_PROJ / "src")
        fs.create_dir("not_a_poetry_project")
        fs.create_file(self.VENV_DIR / "bin" / "activate")
        fs.create_file(self.VENV_DIR / "Scripts" / "Activate.ps1")
        return fs

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_given_poetry_dir(self, os_name, activator):
        stdout = StringIO()
        self.env_list_path_mock.return_value = str(self.VENV_DIR)

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_given_poetry_dir_in_parent(self, os_name, activator):
        stdout = StringIO()
        self.env_list_path_mock.return_value = str(self.VENV_DIR)

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main(["python_project/src"], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    def test_nothing_happens_given_not_venv_dir_and_not_active(self):
        stdout = StringIO()

        assert pyautoenv.main(["not_a_poetry_project"], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_is_already_active(self):
        stdout = StringIO()
        self.env_list_path_mock.return_value = str(self.VENV_DIR)
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()

    def test_nothing_happens_given_venv_dir_in_parent_is_already_active(self):
        stdout = StringIO()
        self.env_list_path_mock.return_value = str(self.VENV_DIR)
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main([str(self.POETRY_PROJ / "src")], stdout) == 0
        assert not stdout.getvalue()

    def test_deactivate_given_active_and_not_venv_dir(self):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)

        assert pyautoenv.main(["not_a_poetry_project"], stdout) == 0
        assert stdout.getvalue() == "deactivate"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_deactivate_and_activate_switching_to_new_poetry_env(
        self,
        fs,
        os_name,
        activator,
    ):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)
        # create new poetry project and venv to associate with it
        fs.create_file("pyproj2/poetry.lock")
        new_venv = Path("virtualenvs/pyproj2-Y-py3.8")
        new_activate = new_venv / activator
        fs.create_file(new_activate)
        self.env_list_path_mock.return_value = str(new_venv)

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main(["pyproj2"], stdout=stdout) == 0
        assert stdout.getvalue() == f"deactivate && . {new_activate}"

    @pytest.mark.parametrize(
        "exception",
        [FileNotFoundError, CalledProcessError(1, [])],
    )
    def test_nothing_happens_given_poetry_env_list_fails(self, exception):
        stdout = StringIO()
        self.env_list_path_mock.side_effect = lambda _: raise_(exception)

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_poetry_env_with_activated_path_suffix(
        self,
        fs,
        os_name,
        activator,
    ):
        stdout = StringIO()
        new_venv = Path("/virtualenvs/python_project-Y-py3.9")
        fs.create_file(new_venv / activator)
        self.env_list_path_mock.return_value = "\n".join(
            [str(new_venv), f"{self.VENV_DIR} (Activated)"],
        )

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_with_first_poetry_env_if_no_activated_path_suffix(
        self,
        fs,
        os_name,
        activator,
    ):
        stdout = StringIO()
        new_venv = Path("/virtualenvs/python_project-Y-py3.9")
        fs.create_file(new_venv / activator)
        self.env_list_path_mock.return_value = "\n".join(
            [str(self.VENV_DIR), str(new_venv)],
        )

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_activates_with_poetry_env_only_if_it_exists(
        self,
        os_name,
        activator,
    ):
        stdout = StringIO()
        new_venv = Path("/virtualenvs/python_project-Y-py3.9")
        self.env_list_path_mock.return_value = "\n".join(
            [f"{self.VENV_DIR}", f"{new_venv} (Activated)"],
        )

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / activator}"

    def test_does_nothing_if_all_paths_returned_by_poetry_not_dirs(self, fs):
        stdout = StringIO()
        fs.create_file("/is/a/file")
        self.env_list_path_mock.return_value = "\n".join(
            ["/not/a/dir", "/is/a/file"],
        )

        assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()

    @pytest.mark.parametrize(("os_name", "activator"), OS_NAME_ACTIVATORS)
    def test_does_nothing_if_activate_script_is_not_file(
        self,
        fs,
        os_name,
        activator,
    ):
        stdout = StringIO()
        # delete the activate script
        fs.remove(self.VENV_DIR / activator)
        self.env_list_path_mock.return_value = str(self.VENV_DIR)

        with mock.patch(OS_NAME, new=os_name):
            assert pyautoenv.main([str(self.POETRY_PROJ)], stdout) == 0
        assert not stdout.getvalue()


def raise_(exc: Exception):
    raise exc
