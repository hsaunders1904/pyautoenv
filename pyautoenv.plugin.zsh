#!/usr/bin/env zsh
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
_pyautoenv_path="${0:a:h}"

function _pyautoenv_activate() {
    add-zsh-hook chpwd _pyautoenv_activate
    add-zsh-hook -d precmd _pyautoenv_activate
    if [ "${PYAUTOENV_DISABLE-0}" -ne 0 ]; then
        return
    fi
    if [ -z "$(command -v python3)" ]; then
        return
    fi
    local pyautoenv_py="${_pyautoenv_path}/pyautoenv.py"
    if [ -f "${pyautoenv_py}" ]; then
        eval "$(python3 "${pyautoenv_py}")"
    fi
}

function _pyautoenv_version() {
    python3 "${_pyautoenv_path}/pyautoenv.py" --version
}

# We need to make sure the shell is fully initialised before we activate the
# virtual environment, otherwise there's some weirdness when the environment
# is deactivated (the user's zshrc is essentially undone).
#
# To work around this, use 'precmd' to run pyautoenv just before the shell
# prompt is written. Then, within the activate function, remove the 'precmd'
# hook and hook into 'chpwd' instead, so we only run on a change of directory.
# The effect of this is that the activation script is run last thing on shell
# startup and then on any change of directory.
autoload -Uz add-zsh-hook
add-zsh-hook precmd _pyautoenv_activate
