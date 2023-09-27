#!/usr/bin/env bash

# Script that runs all tests.

action() {
    local shell_is_zsh=$( [ -z "${ZSH_VERSION}" ] && echo "false" || echo "true" )
    local this_file="$( ${shell_is_zsh} && echo "${(%):-%x}" || echo "${BASH_SOURCE[0]}" )"
    local this_dir="$( cd "$( dirname "${this_file}" )" && pwd )"
    local order_dir="$( dirname "${this_dir}" )"

    (
        cd "${order_dir}" &&
        python -m unittest tests
    )
}
action "$@"
