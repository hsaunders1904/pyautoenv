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
$pyAutoEnvDir = "${PSScriptRoot}"

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
  $pyAutoEnv = Join-Path "${pyAutoEnvDir}" "pyautoenv.py"
  if (Test-Path "${pyAutoEnv}") {
    $expression = "$(python "${pyAutoEnv}" --pwsh)"
    if (${expression}) {
      Invoke-Expression "${expression}"
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
  $pyAutoEnv = Join-Path "${pyAutoEnvDir}" "pyautoenv.py"
  python "${pyAutoEnv}" --version
}

<#
.SYNOPSIS
  Create a proxy function definition for a Cmdlet that executes pyautoenv.
.LINK
  https://github.com/hsaunders1904/pyautoenv/
#>
function New-PyAutoEnvProxyFunctionDefinition([string] $commandString)
{
  # Generate base code for the Proxy function.
  $originalCommand = Get-Command -Name "$commandString" -CommandType Cmdlet
  $metaData = New-Object System.Management.Automation.CommandMetaData $originalCommand
  $proxyCode = [System.Management.Automation.ProxyCommand]::Create($metaData)

  # Find the 'end' block of Set-Location's source.
  $ast = [System.Management.Automation.Language.Parser]::ParseInput($proxyCode, [ref]$null, [ref]$null)
  $endBlock = $ast.EndBlock.Extent.Text
  $endBlockClosingIndex = $endBlock.LastIndexOf('}')
  if ($endBlockClosingIndex -Le 0) {
    # If we can't find the opening brace, something's not right, so exit early
    # without editing the proxy to avoid breaking things.
    $body = $ast.ToString()
    return "function $commandString {`n${body}`n}"
  }

  # Insert the pyautoenv function call into the 'end' block of the proxy code.
  $tab = "    "
  $insert = "`n${tab}try {`n${tab}${tab}Invoke-PyAutoEnv`n${tab}} catch {}`n"
  $newEndBlockOpen = $endBlock.Substring(0, $endBlockClosingIndex) + $insert
  $newEndBlock = $newEndBlockOpen + $endBlock.Substring($endBlockClosingIndex)
  $updatedProxyCmd = $proxyCode.Replace($endBlock, $newEndBlock)
  return "function global:$commandString {`n$updatedProxyCmd`n}"
}

foreach ($commandName in ("Set-Location", "Push-Location", "Pop-Location")) {
  Invoke-Expression (& {
    (New-PyAutoEnvProxyFunctionDefinition "$commandName" | Out-String)
  })
}
Invoke-PyAutoEnv  # Look for environment in initial directory.
