import os
from io import StringIO
from pathlib import Path
from unittest import mock

from pyfakefs.fake_filesystem import FakeFilesystem

import autopyenv as aenv


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
        assert stdout.read() == "deactivate && source pyproj2/.venv/bin/activate"

    @mock.patch("autopyenv.poetry_env_path")
    def test_deactivate_and_activate_switching_to_poetry(
        self,
        poetry_env_mock,
        fs,
    ):
        poetry_env_mock.return_value = Path("poetry_proj-X-py3.8")
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        fs.create_file("poetry_proj/poetry.lock")
        fs.create_dir(poetry_env_mock.return_value)
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["poetry_proj"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == "deactivate && source poetry_proj-X-py3.8/bin/activate"


def make_poetry_fs_structure(fs: FakeFilesystem) -> FakeFilesystem:
    fs.create_file("python_project/poetry.lock")
    fs.create_dir("python_project/src")
    fs.create_dir("not_a_poetry_project")
    fs.create_dir("virtualenvs/python_project-X-py3.11")
    return fs


class TestPoetry:
    @classmethod
    def setup_class(cls):
        cls.env_path_patch = mock.patch("autopyenv.poetry_env_path")
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
        venv_path = Path("/virtualenvs/python_project-X-py3.11")
        self.env_path_mock.return_value = venv_path

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        expected_path = venv_path / "bin" / "activate"
        assert stdout.read() == f"source {expected_path}"

    def test_activates_given_poetry_dir_in_parent(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = Path("/virtualenvs/python_project-X-py3.11")
        self.env_path_mock.return_value = venv_path

        assert aenv.main(["python_project/src"], stdout) == 0
        stdout.seek(0)
        expected_path = venv_path / "bin" / "activate"
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
        venv_path = Path("/virtualenvs/python_project-X-py3.11")
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
        new_venv = Path("virtualenvs/pyproj2-Y-py3.8")
        self.env_path_mock.return_value = new_venv
        fs.create_dir(new_venv)
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
