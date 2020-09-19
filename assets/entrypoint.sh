#!/bin/bash

# constants
CONFIG_DIR=/data/config
USER_SOURCE_DIR=/user-code
ROBOT_TYPE_FILE=${CONFIG_DIR}/robot_type
ROBOT_CONFIGURATION_FILE=${CONFIG_DIR}/robot_configuration
ROBOT_HARDWARE_FILE=${CONFIG_DIR}/robot_hardware

# if anything weird happens from now on, STOP
set -e

# reset health
echo ND > /health

# get container ID
DT_MODULE_INSTANCE=$(basename "$(cat /proc/1/cpuset)")
export DT_MODULE_INSTANCE


debug(){
  if [ "${DEBUG}" = "1" ]; then
    echo "$1";
  fi
}


configure_vehicle(){
  # check the mandatory arguments
  VEHICLE_NAME_IS_SET=1
  if [ ${#VEHICLE_NAME} -le 0 ]; then
    VEHICLE_NAME_IS_SET=0
    VEHICLE_NAME=$(hostname)
    echo "The environment variable VEHICLE_NAME is not set. Using '${VEHICLE_NAME}'."
  fi
  export VEHICLE_NAME="${VEHICLE_NAME}"

  # check optional arguments
  if [ ${#VEHICLE_IP} -ne 0 ]; then
    echo "The environment variable VEHICLE_IP is set to '${VEHICLE_IP}'. Adding to /etc/hosts."
    {
      echo "${VEHICLE_IP} ${VEHICLE_NAME} ${VEHICLE_NAME}.local" | dd of=/etc/hosts &>/dev/null
    } || {
      echo "WARNING: Failed writing to /etc/hosts. Will continue anyway."
    }
  fi

  # configure hosts
  if [ "${VEHICLE_NAME_IS_SET}" -eq "0" ]; then
    # vehicle name not set (assume vehicle is localhost)
    {
      echo "127.0.0.1 ${VEHICLE_NAME} ${VEHICLE_NAME}.local" | dd of=/etc/hosts &>/dev/null
    } || {
      echo "WARNING: Failed writing to /etc/hosts. Will continue anyway."
    }
  fi

  # robot_type
  if [ -f "${ROBOT_TYPE_FILE}" ]; then
      ROBOT_TYPE=$(cat "${ROBOT_TYPE_FILE}")
      export ROBOT_TYPE
  else
      echo "WARNING: robot_type file does not exist. Using 'duckiebot' as default type."
      export ROBOT_TYPE="duckiebot"
  fi

  # robot_configuration
  if [ -f "${ROBOT_CONFIGURATION_FILE}" ]; then
      ROBOT_CONFIGURATION=$(cat "${ROBOT_CONFIGURATION_FILE}")
      export ROBOT_CONFIGURATION
  else
      echo "WARNING: robot_configuration file does not exist."
      export ROBOT_CONFIGURATION="__NOTSET__"
  fi

  # robot_hardware
  if [ -f "${ROBOT_HARDWARE_FILE}" ]; then
      ROBOT_HARDWARE=$(cat "${ROBOT_HARDWARE_FILE}")
      export ROBOT_HARDWARE
  else
      echo "WARNING: robot_hardware file does not exist."
      export ROBOT_HARDWARE="__NOTSET__"
  fi
}


configure_python(){
  # make the code discoverable by python
  for d in $(find "${SOURCE_DIR}" -mindepth 1 -maxdepth 1 -type d); do
    debug " > Adding ${d}/packages to PYTHONPATH"
    export PYTHONPATH="${d}/packages:${PYTHONPATH}"
  done
  # make the (user) code discoverable by python
  if [ -d "${USER_SOURCE_DIR}" ]; then
      for d in $(find "${USER_SOURCE_DIR}" -mindepth 1 -maxdepth 1 -type d); do
        debug " > Adding ${d}/packages to PYTHONPATH"
        export PYTHONPATH="${d}/packages:${PYTHONPATH}"
      done
  fi
}


configure_ROS(){
  # check if ROS_MASTER_URI is set
  ROS_MASTER_URI_IS_SET=0
  if [ -n "${ROS_MASTER_URI}" ]; then
    ROS_MASTER_URI_IS_SET=1
  fi

  # constants
  ROS_SETUP=(
    "/opt/ros/${ROS_DISTRO}/setup.bash"
    "${SOURCE_DIR}/catkin_ws/devel/setup.bash"
    "${SOURCE_DIR}/setup.sh"
    "${USER_SOURCE_DIR}/catkin_ws/devel/setup.bash"
  )

  # setup ros environment
  for ROS_SETUP_FILE in "${ROS_SETUP[@]}"; do
    if [ -f "${ROS_SETUP_FILE}" ]; then
      debug "Sourcing file '${ROS_SETUP_FILE}'."
      source "${ROS_SETUP_FILE}";
    fi
  done

  # configure ROS IP
  CONTAINER_IP=$(hostname -I 2>/dev/null | cut -d " " -f 1)
  export ROS_IP=${CONTAINER_IP}

  # configure ROS MASTER URI
  if [ "${ROS_MASTER_URI_IS_SET}" -eq "0" ]; then
    export ROS_MASTER_URI="http://${VEHICLE_NAME}.local:11311/"
  fi
}


# configure
debug "=> Setting up vehicle configuration..."
configure_vehicle
debug "<= Done!\n"

debug "=> Setting up PYTHONPATH..."
configure_python
debug "<= Done!\n"

debug "=> Setting up ROS environment..."
configure_ROS
debug "<= Done!\n"


# if anything weird happens from now on, CONTINUE
set +e


# reuse DT_LAUNCHER as CMD if the var is set and the first argument is `--`
if [ ${#DT_LAUNCHER} -gt 0 ] && [ "$1" == "--" ]; then
  shift
  exec bash -c "dt-launcher-$DT_LAUNCHER $*"
else
  exec "$@"
fi
