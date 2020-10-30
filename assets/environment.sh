#!/bin/bash

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
    echo "=> Launching app..."
}

dt-launchfile-join() {
    # wait for the process to end
    dt-join
    # wait for stdout to flush, then announce app termination
    sleep 0.5
    printf "<= App terminated!\n"
}

dt-exec() {
    cmd="$@"
    cmd="${cmd%&} &"
    eval "${cmd}"
}
