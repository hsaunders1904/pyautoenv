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
