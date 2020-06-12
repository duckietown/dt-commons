#!/bin/bash

dt-terminate() {
  # send SIGINT signal to monitored process
  kill -INT $(pgrep -P $$) 2> /dev/null
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
  wait &> /dev/null
  set -e
}

dt-launchfile-init() {
  set -e
  # register signal handlers
  dt-register-signals
  # create CODE_DIR variable
  # TODO: in template v2, LAUNCHFILE is not declared anymore, so this will not work
  CODE_DIR="$( cd "$( dirname "${LAUNCHFILE}" )" > /dev/null 2>&1 && pwd )"
  export CODE_DIR
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
  echo "=> Launching app..."
  eval "${cmd}"
}