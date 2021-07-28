#!/bin/bash

# source entrypoint if it hasn't been done
if [ "${DT_ENTRYPOINT_SOURCED}" != "1" ]; then
    source /entrypoint.sh
fi

dt-terminate() {
    # send SIGINT signal to monitored process
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
    set -e
    # register signal handlers
    dt-register-signals
    if [ "${1-undefined}" != "--quiet" ]; then
        echo "==> Launching app..."
    fi
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
