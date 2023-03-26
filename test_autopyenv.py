import os
from io import StringIO
from pathlib import Path
from unittest import mock

from pyfakefs.fake_filesystem import FakeFilesystem

import autopyenv as aenv


def test_parse_args_directory_is_pwd_by_default():
    args = aenv.parse_args([])

    assert args.directory == Path.cwd()


def test_parse_args_directory_is_set():
    args = aenv.parse_args(["/some/dir"])

    assert args.directory == Path("/some/dir")


def make_venv_fs_structure(fs: FakeFilesystem) -> FakeFilesystem:
    fs.create_dir("python_project/src")
    fs.create_file("python_project/.venv/bin/activate")
    fs.create_dir("not_a_venv")
    return fs


def test_main_does_nothing_given_directory_does_not_exist():
    stdout = StringIO()

    assert aenv.main(["/not/a/dir"], stdout) == 1
    stdout.seek(0)
    assert stdout.read() == ""


class TestVenv:
    def setup_method(self):
        os.environ = {}

    def test_activates_given_venv_dir(self, fs: FakeFilesystem):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        expected_path = Path("python_project") / ".venv" / "bin" / "activate"
        assert Path(stdout.read().strip()).samefile(expected_path)

    def test_activates_if_venv_in_parent(self, fs: FakeFilesystem):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)

        assert aenv.main(["python_project/src"], stdout) == 0
        stdout.seek(0)
        expected_path = Path("python_project") / ".venv" / "bin" / "activate"
        assert Path(stdout.read().strip()).samefile(expected_path)

    def test_nothing_happens_given_venv_dir_is_already_activate(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == ""

    def test_nothing_happens_given_not_venv_dir_and_not_activate(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)

        assert aenv.main(["not_a_venv"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == ""

    def test_deactivate_given_active_and_not_venv_dir(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["not_a_venv"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == "deactivate\n"

    def test_deactivate_and_activate_switching_to_new_venv(self, fs):
        stdout = StringIO()
        fs = make_venv_fs_structure(fs)
        fs.create_file("pyproj2/.venv/bin/activate")
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["pyproj2"], stdout=stdout) == 0
        stdout.seek(0)
        assert stdout.read() == "deactivate && pyproj2/.venv/bin/activate\n"


def make_poetry_fs_structure(fs: FakeFilesystem) -> FakeFilesystem:
    fs.create_file("python_project/poetry.lock")
    fs.create_dir("python_project/src")
    fs.create_dir("not_a_poetry_project")
    fs.create_dir("virtualenvs/python_project-X-py3.11")
    return fs


class TestPoetry:
    def setup_class(cls):
        cls.env_path_patch = mock.patch("autopyenv.poetry_env_path")
        cls.env_path_mock = cls.env_path_patch.start()
        cls.which_patch = mock.patch(
            "autopyenv.shutil.which", new=lambda p: p == "poetry"
        )
        cls.which_mock = cls.which_patch.start()

    def teardown_class(cls):
        cls.env_path_patch.stop()
        cls.which_patch.stop()

    def setup_method(self):
        os.environ = {"PATH": "/bin"}

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
        assert stdout.read().strip() == str(expected_path)

    def test_activates_given_poetry_dir_in_parent(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = Path("/virtualenvs/python_project-X-py3.11")
        self.env_path_mock.return_value = venv_path

        assert aenv.main(["python_project/src"], stdout) == 0
        stdout.seek(0)
        expected_path = venv_path / "bin" / "activate"
        assert stdout.read().strip() == str(expected_path)

    def test_nothing_happens_given_not_venv_dir_and_not_activate(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)

        assert aenv.main(["not_a_poetry_project"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == ""

    def test_nothing_happens_given_venv_dir_is_already_activate(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        venv_path = Path("/virtualenvs/python_project-X-py3.11")
        self.env_path_mock.return_value = venv_path
        os.environ["VIRTUAL_ENV"] = venv_path

        assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == ""

    def test_deactivate_given_active_and_not_venv_dir(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)
        os.environ["VIRTUAL_ENV"] = "/python_project"

        assert aenv.main(["not_a_poetry_project"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == "deactivate\n"

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
            stdout.read() == "deactivate && virtualenvs/pyproj2-Y-py3.8/bin/activate\n"
        )

    def test_nothing_happens_given_poetry_not_on_path(self, fs):
        stdout = StringIO()
        fs = make_poetry_fs_structure(fs)

        with mock.patch("autopyenv.shutil.which", new=lambda p: p != "poetry"):
            assert aenv.main(["python_project"], stdout) == 0
        stdout.seek(0)
        assert stdout.read() == ""
