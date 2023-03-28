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
$PyAutoEnvDir = "${PSScriptRoot}"

if (Test-Path alias:cd) {
  Remove-Alias -Name cd -Force -Scope Global
}

function Invoke-PyAutoEnv() {
  if (${Env:PYAUTOENV_DISABLE} -ne 0 -And "${Env:PYAUTOENV_DISABLE}" -ne "") {
    return
  }
  if (-Not (Test-Command python3)) {
    return
  }
  $PyAutoEnv = Join-Path "${PyAutoEnvDir}" "pyautoenv.py"
  if (Test-Path "${PyAutoEnv}") {
    $Expression = "$(python3 "${PyAutoEnv}")"
    if (${Expression}) {
      Invoke-Expression "${Expression}"
     }
  }
}

function Invoke-AutoEnvPyVersion() {
  $PyAutoEnv = Join-Path "${PyAutoEnvDir}" "pyautoenv.py"
  python3 "${PyAutoEnv}" --version
}

function cd() {
  Set-Location @Args && Invoke-PyAutoEnv
}
