import abc
import copy
import os
import re
from io import StringIO
from pathlib import Path
from typing import Dict, Union
from unittest import mock

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

import pyautoenv

OPERATING_SYSTEM = "pyautoenv.operating_system"


def root_dir() -> Path:
    """
    Return the root directory for the current system.

    This is useful for OS-compatibility when we're building paths in
    our tests.
    """
    return Path(os.path.abspath("/"))


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
        "# comment\n"
        'names = "not this one!"\n'
        f'name = "{name}"\n'
        'version = "0.2.0"\n'
        "some_list = [\n"
        "    'val1',\n"
        "    'val2',\n"
        "]\n"
        "\n"
        "[tool.ruff]\n"
        "select = [\n"
        '    "F",\n'
        '    "W",\n'
        "]\n",
    )
    return fs


def test_main_does_nothing_given_directory_does_not_exist():
    stdout = StringIO()

    assert pyautoenv.main(["/not/a/dir"], stdout) == 1
    assert not stdout.getvalue()


@pytest.mark.parametrize(
    ("os_name", "enum_value"),
    [
        ("linux2", pyautoenv.Os.LINUX),
        ("darwin", pyautoenv.Os.MACOS),
        ("win32", pyautoenv.Os.WINDOWS),
        ("Java", None),
    ],
)
def test_operating_system_returns_enum_based_on_sys_platform(
    os_name,
    enum_value,
):
    pyautoenv.operating_system.cache_clear()

    with mock.patch("pyautoenv.sys.platform", new=os_name):
        assert pyautoenv.operating_system() == enum_value


class TestParseArgs:
    def setup_method(self):
        self.stdout = StringIO()

    def test_directory_is_cwd_by_default(self):
        args = pyautoenv.parse_args([], self.stdout)

        assert args.directory == str(Path.cwd())

    def test_directory_is_set(self):
        path = Path("some/dir")

        args = pyautoenv.parse_args([str(path)], self.stdout)

        assert args.directory == os.path.abspath(path)

    @pytest.mark.parametrize(
        "args",
        [["-h"], ["--help"], ["abc", "--help"], ["-V", "--help"]],
    )
    def test_help_prints_help_and_exits(self, args):
        with pytest.raises(SystemExit) as sys_exit:
            pyautoenv.parse_args(args, self.stdout)
        assert re.match(r"usage: pyautoenv(.py)? .*\n", self.stdout.getvalue())
        assert pyautoenv.__doc__ in self.stdout.getvalue()
        assert sys_exit.value.code == 0

    @pytest.mark.parametrize(
        "args",
        [["-V"], ["--version"], ["x", "--version"]],
    )
    def test_version_prints_version_and_exits(self, args):
        with pytest.raises(SystemExit) as sys_exit:
            pyautoenv.parse_args(args, self.stdout)
        version_pattern = r"pyautoenv [0-9]+\.[0-9]+\.[0-9](\.\w+)?\n"
        assert re.match(version_pattern, self.stdout.getvalue())
        assert sys_exit.value.code == 0

    @pytest.mark.parametrize("argv", [[], ["path"]])
    def test_fish_false_given_no_flag(self, argv):
        args = pyautoenv.parse_args(argv, self.stdout)

        assert args.fish is False

    @pytest.mark.parametrize(
        "argv",
        [["--fish"], ["path", "--fish"], ["--fish", "path"]],
    )
    def test_fish_true_given_flag(self, argv):
        args = pyautoenv.parse_args(argv, self.stdout)

        assert args.fish is True

    @pytest.mark.parametrize("argv", [[], ["path"], ["--fish"]])
    def test_pwsh_false_given_no_flag(self, argv):
        args = pyautoenv.parse_args(argv, self.stdout)

        assert args.pwsh is False

    @pytest.mark.parametrize(
        "argv",
        [["--pwsh"], ["path", "--pwsh"], ["--pwsh", "path"]],
    )
    def test_pwsh_true_given_flag(self, argv):
        args = pyautoenv.parse_args(argv, self.stdout)

        assert args.pwsh is True

    @pytest.mark.parametrize("argv_prefix", [[], ["path"]])
    def test_raises_value_error_given_more_than_one_flag(self, argv_prefix):
        argv = argv_prefix + ["--pwsh", "--fish"]

        with pytest.raises(ValueError):
            pyautoenv.parse_args(argv, self.stdout)

    def test_raises_value_error_given_more_than_two_args(self):
        with pytest.raises(ValueError):
            pyautoenv.parse_args(["/some/dir", "/another/dir"], self.stdout)


class VenvTester(abc.ABC):
    PY_PROJ = root_dir() / "python_project"
    VENV_DIR = PY_PROJ / ".venv"

    @abc.abstractproperty
    def os(self) -> int:
        """The operating system the class is testing on."""

    @abc.abstractproperty
    def flag(self) -> str:
        """The command line flag to select the activator."""

    @abc.abstractproperty
    def activator(self) -> str:
        """The name of the activator script."""

    def setup_method(self):
        pyautoenv.operating_system.cache_clear()
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
        fs.create_file(self.VENV_DIR / "bin" / "Activate.ps1")
        fs.create_file(self.VENV_DIR / "Scripts" / "activate")
        fs.create_file(self.VENV_DIR / "Scripts" / "Activate.ps1")
        fs.create_dir("not_a_venv")
        return fs

    def test_activates_given_venv_dir(self):
        stdout = StringIO()

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / self.activator}"

    def test_activates_if_venv_in_parent(self):
        stdout = StringIO()

        assert (
            pyautoenv.main([str(self.PY_PROJ / "src"), self.flag], stdout) == 0
        )
        assert stdout.getvalue() == f". {self.VENV_DIR / self.activator}"

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
        assert stdout.getvalue() == f"deactivate && . {new_venv_activate}"

    @mock.patch("pyautoenv.poetry_env_path")
    def test_deactivate_and_activate_switching_to_poetry(
        self,
        poetry_env_mock,
        fs,
    ):
        stdout = StringIO()
        activate_venv(self.VENV_DIR)
        # create a poetry venv to switch into
        poetry_env = Path("poetry_proj-X-py3.8")
        poetry_env_mock.return_value = poetry_env / self.activator
        fs = make_poetry_project(fs, "project", Path("/poetry_proj"))
        fs.create_file(poetry_env / self.activator)

        assert pyautoenv.main(["poetry_proj", self.flag], stdout) == 0
        assert (
            stdout.getvalue()
            == f"deactivate && . {poetry_env / self.activator}"
        )

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
        assert stdout.getvalue() == f". {venv_activate}"

    def test_venv_dir_name_environment_variable_ignored_if_set_but_empty(self):
        stdout = StringIO()
        os.environ["PYAUTOENV_VENV_NAME"] = ""

        assert pyautoenv.main([str(self.PY_PROJ), self.flag], stdout) == 0
        assert stdout.getvalue() == f". {self.VENV_DIR / self.activator}"


class TestVenvShLinux(VenvTester):
    activator = "bin/activate"
    flag = ""
    os = pyautoenv.Os.LINUX


class TestVenvPwshLinux(VenvTester):
    activator = "bin/Activate.ps1"
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


class PoetryTester(abc.ABC):
    python_proj = Path("python_project")
    not_poetry_proj = Path("not_a_poetry_proj")

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
        fs.create_file(self.venv_dir / "bin" / "Activate.ps1")
        fs.create_file(self.venv_dir / "bin" / "Activate.fish")
        fs.create_file(self.venv_dir / "Scripts" / "Activate.ps1")
        return fs

    def setup_method(self):
        pyautoenv.operating_system.cache_clear()
        self.os_patch = mock.patch(OPERATING_SYSTEM, return_value=self.os)
        self.os_patch.start()
        os.environ = copy.deepcopy(self.env)  # noqa: B003

    def teardown_method(self):
        self.os_patch.stop()

    def test_activates_given_poetry_dir(self):
        stdout = StringIO()

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert stdout.getvalue() == f". {self.venv_dir / self.activator}"

    def test_activates_given_poetry_dir_in_parent(self):
        stdout = StringIO()

        assert pyautoenv.main(["python_project/src", self.flag], stdout) == 0
        assert stdout.getvalue() == f". {self.venv_dir / self.activator}"

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

    def test_deactivate_and_activate_switching_to_new_poetry_env(self, fs):
        stdout = StringIO()
        activate_venv(self.venv_dir)
        fs = make_poetry_project(fs, "pyproj2", Path("pyproj2"))
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

        assert pyautoenv.main([str(self.python_proj)], stdout) == 0
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
        assert stdout.getvalue() == f". {new_activator}"

    def test_poetry_cache_dir_env_var_not_used_if_set_and_does_not_exist(self):
        stdout = StringIO()
        os.environ["POETRY_CACHE_DIR"] = "/not/a/dir"

        assert pyautoenv.main([str(self.python_proj), self.flag], stdout) == 0
        assert stdout.getvalue() == f". {self.venv_dir / self.activator}"

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


class PoetryLinuxTester(PoetryTester):
    env = {
        "HOME": str(root_dir() / "home" / "user"),
        "USERPROFILE": str(root_dir() / "home" / "user"),
    }
    os = pyautoenv.Os.LINUX
    poetry_cache = (
        root_dir() / "home" / "user" / ".cache" / "pypoetry" / "virtualenvs"
    )


class TestPoetryShLinux(PoetryLinuxTester):
    activator = Path("bin/activate")
    flag = ""


class TestPoetryPwshLinux(PoetryLinuxTester):
    activator = Path("bin/Activate.ps1")
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


class TestPoetryShMacos(PoetryMacosTester):
    activator = Path("bin/activate")
    flag = ""


class TestPoetryPwshMacos(PoetryMacosTester):
    activator = Path("bin/Activate.ps1")
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
