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

<#
.SYNOPSIS
  Activate/deactivate Python virtual environments based on the working directory.
.DESCRIPTION
  If a Python virtual environment is defined in the current working directory,
  activate it. If one is not, deactivate any active environment.
.LINK
  https://github.com/hsaunders1904/pyautoenv/
#>
function Invoke-PyAutoEnv() {
  if (${Env:PYAUTOENV_DISABLE} -ne 0 -And "${Env:PYAUTOENV_DISABLE}" -ne "") {
    return
  }
  if (-Not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    return
  }
  $PyAutoEnv = Join-Path "${PyAutoEnvDir}" "pyautoenv.py"
  if (Test-Path "${PyAutoEnv}") {
    $Expression = "$(python "${PyAutoEnv}" --pwsh)"
    if (${Expression}) {
      Invoke-Expression "${Expression}"
     }
  }
}

<#
.SYNOPSIS
  Show the version of pyautoenv.
.LINK
  https://github.com/hsaunders1904/pyautoenv/
#>
function Invoke-PyAutoEnvVersion() {
  $PyAutoEnv = Join-Path "${PyAutoEnvDir}" "pyautoenv.py"
  python "${PyAutoEnv}" --version
}

function cd() {
  Set-Location @Args && Invoke-PyAutoEnv
}
