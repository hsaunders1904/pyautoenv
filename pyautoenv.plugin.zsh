# zsh-pyautoenv Automatically activate and deactivate Python environments.
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
THIS_DIR="${0:a:h}"

function _zsh_pyautoenv_activate() {
    if [ -z "$(command -v python3)" ]; then
        return
    fi
    if [ -n "${ZSH_pyautoenv_DISABLE}" ] && [ "${ZSH_pyautoenv_DISABLE}" -ne 0 ]; then
        return
    fi
    local cmd
    cmd="$(python3 "${THIS_DIR}/pyautoenv.py")"
    if [ -n "${cmd}" ]; then
        eval "${cmd}"
    fi
}

function _zsh_pyautoenv_version() {
    python3 "${THIS_DIR}/pyautoenv.py" --version
}

autoload -Uz add-zsh-hook
add-zsh-hook chpwd _zsh_pyautoenv_activate
