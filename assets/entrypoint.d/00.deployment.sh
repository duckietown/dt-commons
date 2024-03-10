#!/usr/bin/env bash

# output
DT_DEPLOYED_ONBOARD=0

# possible values are: BRIDGE, HOST, NONE
netmode=$(dt-get-network-mode)
hostname=$(hostname)

# net=bridge
if [ "${netmode}" = "BRIDGE" ]; then
    DT_DEPLOYED_ONBOARD=0
fi

# net=host
if [ "${netmode}" = "HOST" ]; then
    if [ "${hostname}" = "${VEHICLE_NAME}" ]; then
        DT_DEPLOYED_ONBOARD=1
    fi
fi

# export
export DT_DEPLOYED_ONBOARD
