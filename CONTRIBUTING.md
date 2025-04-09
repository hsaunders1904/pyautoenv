# Contributing to pyautoenv

Contributions to improve `pyautoenv` are very welcome.
You can contribute to `pyautoenv` in many ways, including:

- Reporting bugs.
- Requesting/recommending features.
- Opening a pull request to implement features or fix bugs.
- Updating, improving, or reporting errors in documentation.

Please open an issue to allow for discussion before starting work.
Also see [`ARCHITECTURE.md`](./ARCHITECTURE.md)
for an overview of how `pyautoenv` works.

## Opening an Issue

When opening an issue please ensure you outline,
in as much detail as possible, the changes you wish to develop.
Also, ensure that this feature/fix has not already been raised
by searching through the existing issues.

If reporting a bug, provide as much detail as possible,
ideally giving a minimal reproducible example
and the scenario which led to the problem.
Tracebacks, images, and scripts are very useful.
If we can't recreate the problem, we can't fix it.

Please make use of the issue templates when opening an issue.

## Setting Up a Development Environment

`pyautoenv` uses [`uv`](https://docs.astral.sh/uv/)
to manage its development environment.
Install `uv`, by following the instructions in their
[docs](https://docs.astral.sh/uv/getting-started/installation/).

To make a virtual environment and install the development dependencies, run:

```console
uv sync --all-extras
```

### Tests

Tests are currently all written in Python using `pytest`.
To run the test suite:

```console
uv run pytest
```

### Code Quality

Python linting and code formatting is provided by `ruff`.
These can be run using:

```console
uv run ruff check .
uv run ruff format .
```

A `pre-commit` config is provided to run check on each commit.
Install pre-commit with:

```console
uv run pre-commit install
```

You can also run all linting/formatting check using `pre-commit`:

```console
uv run pre-commit run --all-files
```
