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
