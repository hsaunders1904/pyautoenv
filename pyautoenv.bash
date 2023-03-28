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

THIS_DIR="$(cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

function _bash_pyautoenv_activate() {
    if [ "${PYAUTOENV_DISABLE-0}" -ne 0 ]; then
        return
    fi
    if [ -z "$(command -v python3)" ]; then
        return
    fi
    local pyautoenv_py="${THIS_DIR}/pyautoenv.py"
    if [ -f "${pyautoenv_py}" ]; then
        eval "$(python3 "${pyautoenv_py}")"
    fi
}

function _bash_pyautoenv_version() {
    python3 "${THIS_DIR}/pyautoenv.py" --version
}

function cd() {
    builtin cd "$@" && _bash_pyautoenv_activate
}
