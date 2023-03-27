THIS_DIR="${0:a:h}"

function _zsh_autopyenv_activate() {
    if [ -z "$(command -v python3)" ]; then
        return
    fi
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
add-zsh-hook chpwd _zsh_autopyenv_activate
