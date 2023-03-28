# pyautoenv

Automatically activate and deactivate Python environments
as you move around the file system.

Heavily inspired by [autoenv](https://github.com/hyperupcall/autoenv).
[Poetry](https://python-poetry.org/) or
[venv](https://docs.python.org/3/library/venv.html)
Python environments will automatically be activated when you cd into
a directory that defines an environment
(i.e., if a directory, or any of its parents,
contains `.venv/` or `poetry.lock`).
Environments are automatically deactivated when you leave the directory.

## Install

Follow the installation instructions for your favourite shell.

### Zsh

To install the ZSH plugin, you'll need [oh-my-zsh](https://ohmyz.sh/).
Clone this repo into `~/.oh-my-zsh/plugins` or into `${ZSH_CUSTOM}/plugins`.
Then add `pyautoenv` to your list of enabled plugins in `.zshrc`, e.g.,

```zsh
plugins( pyautoenv )
```

Note that you must have Python >= 3.8 on your path for the plugin to work.


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

Add to your profile (get the path to it using `${Profile}`) to activate
the application permanently.

Note that this script re-aliases `cd`.
