# pyautoenv

Automatically activate and deactivate Python environments
as you move around the file system.

## ZSH

To install the ZSH plugin, clone this repo into `~/.oh-my-zsh/plugins`
or into `${ZSH_CUSTOM}/plugins`.
Then add `pyautoenv` to your list of enabled plugins in `.zshrc`, e.g.,

```zsh
plugins( pyautoenv )
```

Note that you must have Python >= 3.8 on your path for the plugin to work.


## Bash

To enable the application in bash, source the bash script.

```bash
source <path to pyauotenv>/pyautoenv.bash
```

Add this to your `.bashrc` to activate the application permanently.

Note that this script will clobber the `cd` command.

## PowerShell

To enable the application in PowerShell, dot the `.ps1` file.

```pwsh
. <path to pyauotenv>\PyAutoEnv.ps1
```

Add to your profile (get the path to it using `${Profile}`) to activate
the application permanently.

Note that this script re-aliases `cd`.
