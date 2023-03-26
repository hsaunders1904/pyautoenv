THIS_DIR="${0:a:h}"

function _auto_pyenv_activate() {
    if [ -n "${ZSH_AUTOPYENV_DISABLE}" ] && [ "${ZSH_AUTOPYENV_DISABLE}" -ne 0 ]; then
        return
    fi
    local cmd
    cmd="$(python3 "${THIS_DIR}/autopyenv.py")"
    if [ -n "${cmd}" ]; then
        eval "${cmd}"
    fi
}

autoload -Uz add-zsh-hook
add-zsh-hook chpwd _auto_pyenv_activate
