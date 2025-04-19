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
if ! [[ $- == *i* ]]; then
    # do not activate if the shell is not interactive
    return
fi
if ! [ "$(type cd)" == "cd is a shell builtin" ]; then
    >&2 echo "pyautoenv: cd is non-default, aborting activation so things don't break!"
    return
fi

_pyautoenv_path="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

function _pyautoenv_activate() {
    if [ "${PYAUTOENV_DISABLE-0}" -ne 0 ]; then
        return
    fi
    if [ -z "$(command -v python3)" ]; then
        return
    fi
    local pyautoenv_py="${_pyautoenv_path}/pyautoenv.py"
    if [ -f "${pyautoenv_py}" ]; then
        if [ "${PYAUTOENV_DEBUG-0}" -ne 0 ]; then
            eval "$(python3 "${pyautoenv_py}")"
        else
            eval "$(python3 -OO "${pyautoenv_py}")"
        fi
    fi
}

function _pyautoenv_version() {
    python3 -O "${_pyautoenv_path}/pyautoenv.py" --version
}

function cd() {
    builtin cd "$@" && _pyautoenv_activate
}

_pyautoenv_activate
