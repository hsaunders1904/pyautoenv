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
from unittest import mock

import pytest

import pyautoenv
from tests.tools import root_dir

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

    def test_empty_args_are_ignored(self):
        argv = ["   ", "\t", str(root_dir() / "some" / "dir"), ""]

        args = pyautoenv.parse_args(argv, self.stdout)

        assert args.directory == str(root_dir() / "some" / "dir")
        assert args.fish is False
        assert args.pwsh is False
