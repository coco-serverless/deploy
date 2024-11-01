#!/bin/bash

THIS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJ_ROOT=${THIS_DIR}/..

pushd ${PROJ_ROOT} >> /dev/null

export VIRTUAL_ENV_DISABLE_PROMPT=1

if [ ! -d "venv" ]; then
    ./bin/create_venv.sh
fi
source venv/bin/activate

# Invoke tab-completion
_complete_invoke() {
    local candidates
    candidates=`invoke --complete -- ${COMP_WORDS[*]}`
    COMPREPLY=( $(compgen -W "${candidates}" -- $2) )
}

# If running from zsh, run autoload for tab completion
if [ "$(ps -o comm= -p $$)" = "zsh" ]; then
    autoload bashcompinit
    bashcompinit
fi
complete -F _complete_invoke -o default invoke inv

# Useful env. variables
export KUBECONFIG=${PROJ_ROOT}/.config/kubeadm_kubeconfig
export PATH=${PROJ_ROOT}/bin:${PATH}
export PS1="(sc2-deploy) $PS1"

popd >> /dev/null

