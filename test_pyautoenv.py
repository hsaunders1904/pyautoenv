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
from io import StringIO
from pathlib import Path
from unittest import mock

from pyfakefs.fake_filesystem import FakeFilesystem

import pyautoenv as aenv


def test_parse_args_directory_is_cwd_by_default():
    args = aenv.parse_args([])

    assert args.directory == Path.cwd()


def test_parse_args_directory_is_set():
    args = aenv.parse_args(["/some/dir"])

    assert args.directory == Path("/some/dir")


def test_main_does_nothing_given_directory_does_not_exist():
    stdout = StringIO()

    assert aenv.main(["/not/a/dir"], stdout) == 1
    stdout.seek(0)
    assert not stdout.read()


def make_venv_fs_structure(fs: FakeFilesystem) -> FakeFilesystem:
    fs.create_dir("python_project/src")
    fs.create_file("python_project/.venv/bin/activate")
    fs.create_dir("not_a_venv")
    return fs


class TestVenv:
    def setup_method(self):
        os.environ = {}  # noqa: B003

    def test_activates_given_venv_dir(self, fs: FakeFilesystem):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        expected_path = Path("python_project") / ".venv" / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_activates_if_venv_in_parent(self, fs: FakeFilesystem):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)

        assert aenv.main(["python_project/src"], stdout) == 0
        stdout.seek(0)
        expected_path = Path("python_project") / ".venv" / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_nothing_happens_given_venv_dir_is_already_activate(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()

    def test_nothing_happens_given_not_venv_dir_and_not_activate(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)

        assert aenv.main(["not_a_venv"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()

    def test_deactivate_given_active_and_not_venv_dir(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["not_a_venv"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == "deactivate"

    def test_deactivate_and_activate_switching_to_new_venv(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        fs.create_file("pyproj2/.venv/bin/activate")
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["pyproj2"], stdout=stdout) == 0
        stdout.seek(0)
        assert (
            stdout.read() == "deactivate && source pyproj2/.venv/bin/activate"
        )

    @mock.patch("pyautoenv.poetry_env_path")
    def test_deactivate_and_activate_switching_to_poetry(
        self,
        poetry_env_mock,
        fs,
    ):
        poetry_env_mock.return_value = Path("poetry_proj-X-py3.8")
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        fs.create_file("poetry_proj/poetry.lock")
        fs.create_file(f"{poetry_env_mock.return_value}/bin/activate")
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["poetry_proj"], stdout) == 0
        stdout.seek(0)
        assert (
            stdout.read()
            == "deactivate && source poetry_proj-X-py3.8/bin/activate"
        )

    def test_does_nothing_if_activate_script_is_not_file(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        # venv directory exists, but not the activate script
        fs.remove("python_project/.venv/bin/activate")

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()


def make_poetry_fs_structure(fs: FakeFilesystem) -> FakeFilesystem:
    fs.create_file("python_project/poetry.lock")
    fs.create_dir("python_project/src")
    fs.create_dir("not_a_poetry_project")
    fs.create_file("virtualenvs/python_project-X-py3.11/bin/activate")
    return fs


class TestPoetry:
    @classmethod
    def setup_class(cls):
        cls.env_path_patch = mock.patch("pyautoenv.poetry_env_list_path")
        cls.env_path_mock = cls.env_path_patch.start()

    @classmethod
    def teardown_class(cls):
        cls.env_path_patch.stop()

    def setup_method(self):
        os.environ = {"PATH": "/bin"}  # noqa: B003

    def teardown_method(self):
        self.env_path_mock.reset_mock()

    def test_activates_given_poetry_dir(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = "/virtualenvs/python_project-X-py3.11"
        self.env_path_mock.return_value = venv_path

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        expected_path = Path(venv_path) / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_activates_given_poetry_dir_in_parent(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = "/virtualenvs/python_project-X-py3.11"
        self.env_path_mock.return_value = venv_path

        assert aenv.main(["python_project/src"], stdout) == 0
        stdout.seek(0)
        expected_path = Path(venv_path) / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_nothing_happens_given_not_venv_dir_and_not_activate(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)

        assert aenv.main(["not_a_poetry_project"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()

    def test_nothing_happens_given_venv_dir_is_already_activate(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = "/virtualenvs/python_project-X-py3.11"
        self.env_path_mock.return_value = venv_path
        os.environ["VIRTUAL_ENV"] = venv_path

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()

    def test_deactivate_given_active_and_not_venv_dir(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["not_a_poetry_project"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == "deactivate"

    def test_deactivate_and_activate_switching_to_new_poetry_env(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        fs.create_file("pyproj2/poetry.lock")
        new_venv = "virtualenvs/pyproj2-Y-py3.8"
        self.env_path_mock.return_value = new_venv
        fs.create_file(f"{new_venv}/bin/activate")
        active_venv = Path("virtualenvs/python_project-X-py3.11")
        os.environ["VIRTUAL_ENV"] = active_venv

        assert aenv.main(["pyproj2"], stdout=stdout) == 0
        stdout.seek(0)
        assert (
            stdout.read()
            == "deactivate && source virtualenvs/pyproj2-Y-py3.8/bin/activate"
        )

    def test_nothing_happens_given_poetry_path_cannot_be_found(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        # cannot find the poetry environment directory
        self.env_path_mock.return_value = None

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()

    def test_activates_with_poetry_env_with_activated_path_prefix(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        fs.create_dir("/virtualenvs/python_project-Y-py3.9")
        venv_path = "/virtualenvs/python_project-X-py3.11"
        self.env_path_mock.return_value = "\n".join(
            [
                "/virtualenvs/python_project-Y-py3.9",
                f"{venv_path} (Activated)",
            ],
        )

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        expected_path = Path(venv_path) / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_activates_with_first_poetry_env_if_no_activated_path_prefix(
        self,
        fs,
    ):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = "/virtualenvs/python_project-X-py3.11"
        fs.create_dir("/virtualenvs/python_project-Y-py3.9")
        self.env_path_mock.return_value = "\n".join(
            [f"{venv_path}", "/virtualenvs/python_project-Y-py3.9"],
        )

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        expected_path = Path(venv_path) / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_activates_with_poetry_env_only_if_dir_exists(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = "/virtualenvs/python_project-X-py3.11"
        self.env_path_mock.return_value = "\n".join(
            [
                f"{venv_path}",
                "/virtualenvs/python_project-Y-py3.9 (Activated)",
            ],
        )

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        expected_path = Path(venv_path) / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_does_nothing_if_all_paths_returned_by_poetry_not_dirs(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        fs.create_file("/is/a/file")
        self.env_path_mock.return_value = "\n".join(
            ["/not/a/dir", "/is/a/file"],
        )

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()

    def test_does_nothing_if_activate_script_is_not_file(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = "/virtualenvs/python_project-X-py3.11"
        # delete the activate script
        fs.remove(f"{venv_path}/bin/activate")
        self.env_path_mock.return_value = venv_path

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert not stdout.read()
