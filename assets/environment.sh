#!/bin/bash

export ROS_HOME=/tmp
export ROSCONSOLE_STDOUT_LINE_BUFFERED=1
export TRAPPED_SIGNAL=0

# locations where dtprojects are stored
PROJECTS_LOCATIONS=("${SOURCE_DIR}")
# add catkin src if it exists
if [ ${#CATKIN_WS_DIR} -gt 0 ] && [ -d "${CATKIN_WS_DIR}/src" ]; then
    PROJECTS_LOCATIONS[${#PROJECTS_LOCATIONS[@]}]="${CATKIN_WS_DIR}/src"
fi

debug() {
    if [ "${DEBUG}" = "1" ]; then
        echo -e "  DEBUG: $1"
    fi
}

info() {
    echo -e "   INFO: $1"
}

warning() {
    echo -e "WARNING: $1"
}

error() {
    echo -e "  ERROR: $1"
}

# if anything weird happens from now on, STOP
set -e

# source entrypoint if it hasn't been done
if [ "${DT_ENTRYPOINT_SOURCED-unset}" != "1" ]; then
    source /entrypoint.sh
fi

dt-terminate() {
    # send SIGINT signal to monitored process
    export TRAPPED_SIGNAL=1
    kill -INT $(pgrep -P $$) 2>/dev/null
}

dt-register-signals() {
    trap dt-terminate SIGINT
    trap dt-terminate SIGTERM
}

dt-init() {
    # register signal handlers
    dt-register-signals
}

dt-join() {
    # wait for all the processes in the background to terminate
    set +e
    wait &>/dev/null
    set -e
}

dt-launchfile-init() {
    # if anything weird happens from now on, STOP
    set -e
    # register signal handlers
    dt-register-signals
    if [ "${1-undefined}" != "--quiet" ]; then
        echo "==> Launching app..."
    fi
    # if anything weird happens from now on, CONTINUE
    set +e
}

dt-launchfile-join() {
    # wait for the process to end
    dt-join
    # wait for stdout to flush, then announce app termination
    sleep 0.5
    if [ "${1-undefined}" != "--quiet" ]; then
        printf "<== App terminated!\n"
    fi
}

dt-exec() {
    cmd="$@"
    cmd="${cmd%&} &"
    eval "${cmd}"
}

dt-exec-BG() {
    cmd="$@"
    eval "stdbuf -o L ${cmd%&} 1>&2 &"
}

dt-exec-FG() {
    cmd="$@"
    eval "stdbuf -o L ${cmd%&} 1>&2 "
}

configure_environment() {
    # source all the environment scripts provided by the dtprojects
    for src in "${PROJECTS_LOCATIONS[@]}"; do
        # iterate over directories in chronological order of their creation
        for d in $(find "${src}" -mindepth 1 -maxdepth 1 -type d -printf "%T@ %p\n" | sort -n | cut -d " " -f 2); do
            PROJECT_ENVIRONMENT_DIR="${d}/assets/environment.d"
            if [ -d "${PROJECT_ENVIRONMENT_DIR}" ]; then
                debug " > Sourcing ${PROJECT_ENVIRONMENT_DIR}/"
                for f in $(find "${PROJECT_ENVIRONMENT_DIR}" -mindepth 1 -maxdepth 1 -type f -name "*.sh"); do
                    debug "  > Sourcing ${f}"
                    source ${f}
                    debug "  < Sourced ${f}"
                done
                debug " > Sourced ${PROJECT_ENVIRONMENT_DIR}/"
            fi
        done
    done
}

debug "=> Setting up environment..."
configure_environment
debug "<= Done!"

# if anything weird happens from now on, CONTINUE
set +e
