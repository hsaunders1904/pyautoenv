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

Supports Python versions 3.9 and up.

## Install

Follow the installation instructions for your favourite shell.

### Zsh

<details>
<summary>Expand instructions</summary>

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
source pyautoenv.plugin.zsh
```

Add this to your `.zshrc` to activate the application permanently.

</details>

### Bash

<details>
<summary>Expand instructions</summary>

To enable the application in bash, source the bash script.

```bash
source <path to pyauotenv>/pyautoenv.bash
```

Add this to your `.bashrc` to activate the application permanently.

Note that this script will clobber the `cd` command.
It is highly recommended to use a more modern shell,
like ZSH or Fish, when using `pyautoenv`.

</details>

### Fish

<details>
<summary>Expand instructions</summary>

To enable the application in fish-shell, source the fish script.

```fish
source <path to pyauotenv>/pyautoenv.fish
```

Add this to your `config.fish` file to activate the application permanently.

</details>

### PowerShell

<details>
<summary>Expand instructions</summary>

To enable the application in PowerShell, dot the `.ps1` file.

```pwsh
. <path to pyauotenv>\PyAutoEnv.ps1
```

Add this to your profile to activate the application permanently.

</details>

## Options

There are some environment variables you can set to configure `pyautoenv`.

- `PYAUTOENV_DISABLE`: Set to a non-zero value to disable all functionality.
- `PYAUTOENV_VENV_NAME`:
  If you name your virtualenv directories something other than `.venv`,
  you can use this to override directory names to search within.
  Use `;` as a delimiter to separate directory names.
  For example, if set to `.venv;venv`, on each directory change,
  `pyautoenv` will look for an environment within `.venv`,
  if that directory does not exist, it will look for an environment in `venv`.
- `PYAUTOENV_IGNORE_DIR`:
  If you wish to disable `pyautoenv` for a specific set of directories,
  you can list these directories here,
  separated with a `;`.
  The directories, and their children,
  will be treated as though no virtual environment exists for them.
  This means any active environment will be deactivated when changing to them.
- `PYAUTOENV_DEBUG`: Set to a non-zero value to enable logging.
  When active, you can also use `PYAUTOENV_LOG_LEVEL`
  to set the logging level to something supported by Python's `logging` module.
  The default log level is `DEBUG`.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).
