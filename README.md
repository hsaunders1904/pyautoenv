# pyautoenv

[![Build Status](https://github.com/hsaunders1904/pyautoenv/actions/workflows/ci.yaml/badge.svg?branch=main)](https://github.com/hsaunders1904/pyautoenv/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/hsaunders1904/pyautoenv/branch/main/graph/badge.svg?token=YABNBQOS1S)](https://codecov.io/gh/hsaunders1904/pyautoenv)

Automatically activate and deactivate Python environments
as you move around the file system.

## Description

Heavily inspired by [autoenv](https://github.com/hyperupcall/autoenv).
`pyautoenv` activates a
[Poetry](https://python-poetry.org/) or
[venv](https://docs.python.org/3/library/venv.html)
Python environment when you cd into the directory that defines that environment
(i.e., when a directory, or any of its parents,
contains a `poetry.lock` file or a `.venv/` directory).
Environments are automatically deactivated when you leave the directory.

Supports Python versions 3.8 and up.

## Install

Follow the installation instructions for your favourite shell.

You can disable `pyautoenv` by setting the
`PYAUTOENV_DISABLE` environment variable to a non-zero value.

### Zsh

If you're using [oh-my-zsh](https://ohmyz.sh/),
clone this repo into `~/.oh-my-zsh/plugins` or `${ZSH_CUSTOM}/plugins`.
Then add `pyautoenv` to the list of enabled plugins in your `.zshrc`:

```zsh
plugins=(
    pyautoenv
)
```

If you're not using `oh-my-zsh`, `source` the `pyautoenv.plugin.zsh` script.

```zsh
source pyauotenv.plugin.zsh
```

Add this to your `.zshrc` to activate the application permanently.

### Bash

To enable the application in bash, source the bash script.

```bash
source <path to pyauotenv>/pyautoenv.bash
```

Add this to your `.bashrc` to activate the application permanently.

Note that this script will clobber the `cd` command.

### PowerShell

To enable the application in PowerShell, dot the `.ps1` file.

```pwsh
. <path to pyauotenv>\PyAutoEnv.ps1
```

Add this to your profile to activate the application permanently.

Note that this script re-aliases `cd`
and only PowerShell running on Windows is supported.
