# Contributing to pyautoenv

Contributions to improve `pyautoenv` are very welcome.
You can contribute to `pyautoenv` in many ways, including:

- Reporting bugs.
- Requesting/recommending features.
- Opening a pull request to implement features or fix bugs.
- Updating, improving, or reporting errors in documentation.

Please open an issue to allow for discussion before starting work.

## How `pyautoenv` Works

The majority of work is done by the `pyautoenv.py` script.
The script generates activation/deactivation commands
based on environment variables and the working directory.

Activation scripts for each shell call the Python script
and run the generated commands on each change of directory.

## Opening an Issue

When opening an issue please ensure you outline,
in as much detail as possible, the changes you wish to develop.

If reporting a bug, provide as much detail as possible,
ideally giving a minimal reproducible example
and the scenario which led to the problem.
Tracebacks and/or scripts are very useful.

## Setting Up a Development Environment

`pyautoenv` uses [`uv`](https://docs.astral.sh/uv/)
to manage its development environment.
Install `uv`, by following the instructions in their
[docs](https://docs.astral.sh/uv/getting-started/installation/).

To make a virtual environment and install the development dependencies, run:

```console
uv sync --all-groups
```

### Tests

Tests are currently all written in Python using `pytest`.
To run the test suite:

```console
uv run pytest tests/
```

### Code Quality

Python linting and code formatting is provided by `ruff`.
These can be run using:

```console
uv run ruff check .
uv run ruff format .
```

A `pre-commit` config is provided to run checks on each commit.
Install pre-commit with:

```console
uv run pre-commit install
```

You can also run all linting/formatting checks using `pre-commit`:

```console
uv run pre-commit run --all-files
```
