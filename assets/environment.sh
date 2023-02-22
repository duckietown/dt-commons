#!/bin/bash

export ROS_HOME=/tmp
export ROSCONSOLE_STDOUT_LINE_BUFFERED=1
export TRAPPED_SIGNAL=0

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

# TODO(from A.Daniele): 'challenges' stuff this close to duckietown core, arghhh!!
copy-ros-logs() {
    find /tmp/log  -type f  -name "*.log" -exec cp {} /challenges/challenge-solution-output \;
}

# if anything weird happens from now on, CONTINUE
set +e
