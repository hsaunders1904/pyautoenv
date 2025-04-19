#!/usr/bin/env fish
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

if ! status --is-interactive
    exit 0
end

set _pyautoenv_path (dirname (realpath (status current-filename)))

function _pyautoenv_activate \
        --on-variable PWD \
        --on-event _pyautoenv_fish_init \
        --description 'Activate/deactivate python environments based on the current directory'
    if test -n "$PYAUTOENV_DISABLE"; and test "$PYAUTOENV_DISABLE" != "0"
        return
    end
    if ! command --search python3 >/dev/null
        return
    end
    set --local _pyautoenv_py "$_pyautoenv_path/pyautoenv.py"
    if test -f "$_pyautoenv_py"
        if not set -q PYAUTOENV_DEBUG; or test $PYAUTOENV_DEBUG -eq 0
            eval (python3 -OO "$_pyautoenv_py" --fish)
        else
            eval (python3 "$_pyautoenv_py" --fish)
        end
    end
end

function _pyautoenv_version --description 'Print pyautoenv version'
    python3 -O "$_pyautoenv_path/pyautoenv.py" --version
end

emit _pyautoenv_fish_init
