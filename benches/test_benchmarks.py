"""Benchmarks for pyautoenv's main function."""

from io import StringIO
from pathlib import Path

import pytest

import pyautoenv
from benches.conftest import PoetryVenvFixture
from benches.tools import make_venv, venv_active


class ResettingStream(StringIO):
    """
    A writable stream that resets its position to 0 after each write.

    We can use this in benchmarks to check what's written to the stream
    in the final iteration.
    """

    def write(self, s):
        r = super().write(s)
        self.seek(0)
        return r


def run_main_benchmark(benchmark, path: Path | str, shell: str | None = None):
    stream = ResettingStream()
    argv = [str(path)]
    if shell:
        argv.append(f"--{shell}")
    benchmark(lambda: pyautoenv.main(argv, stdout=stream))
    return stream.getvalue()


def test_no_activation(benchmark, tmp_path: Path):
    assert not run_main_benchmark(benchmark, tmp_path)


def test_deactivate(benchmark, venv: Path, tmp_path: Path):
    with venv_active(venv):
        assert run_main_benchmark(benchmark, tmp_path) == "deactivate"


@pytest.mark.parametrize("shell", [None, "fish", "pwsh"])
def test_venv_activate(shell, benchmark, venv: Path):
    output = run_main_benchmark(benchmark, venv, shell=shell)

    assert all(s in output.lower() for s in ["activate", str(venv).lower()]), (
        output
    )


def test_venv_already_active(benchmark, venv: Path):
    with venv_active(venv):
        assert not run_main_benchmark(benchmark, venv)


@pytest.mark.parametrize("shell", [None, "fish", "pwsh"])
def test_venv_switch_venv(shell, benchmark, venv: Path, tmp_path: Path):
    make_venv(tmp_path)

    with venv_active(venv):
        output = run_main_benchmark(benchmark, tmp_path, shell=shell)

    assert all(
        s in output for s in ["deactivate", "&&", str(tmp_path), "activate"]
    ), output


@pytest.mark.parametrize("shell", [None, "fish", "pwsh"])
def test_poetry_activate(shell, benchmark, poetry_venv: PoetryVenvFixture):
    output = run_main_benchmark(
        benchmark, poetry_venv.project_dir, shell=shell
    )

    assert "activate" in output.lower()
    assert str(poetry_venv.venv_dir).lower() in output.lower()


def test_poetry_already_activate(benchmark, poetry_venv: PoetryVenvFixture):
    with venv_active(poetry_venv.venv_dir):
        assert not run_main_benchmark(benchmark, poetry_venv.project_dir)


@pytest.mark.parametrize("shell", [None, "fish", "pwsh"])
def test_poetry_switch_to_venv(
    shell, benchmark, poetry_venv: PoetryVenvFixture, venv: Path
):
    with venv_active(venv):
        output = run_main_benchmark(
            benchmark, poetry_venv.project_dir, shell=shell
        )

    assert all(
        s in output
        for s in ["deactivate", "&&", str(poetry_venv.venv_dir), "activate"]
    ), output


@pytest.mark.parametrize("shell", [None, "fish", "pwsh"])
def test_venv_switch_to_poetry(
    shell, benchmark, poetry_venv: PoetryVenvFixture, venv: Path
):
    with venv_active(poetry_venv.venv_dir):
        output = run_main_benchmark(benchmark, venv, shell=shell)

    assert all(
        s in output for s in ["deactivate", "&&", str(venv), "activate"]
    ), output
