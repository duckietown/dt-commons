#!/usr/bin/env bash

# possible values are: BRIDGE, HOST, NONE
netmode=$(dt-get-network-mode)

# robot's switchboard
export DTPS_BASE_SWITCHBOARD_0="http+unix://%2Fdtps%2Fswitchboard.sock/"

# avoid using mDNS when running onboard the vehicle
if [ "${DT_DEPLOYED_ONBOARD}" = "1" ] && [ "${netmode}" = "HOST" ]; then
    export DTPS_BASE_SWITCHBOARD_1="http://localhost:11811/"
else
    # prefer IP address over mDNS
    if [ -n "${VEHICLE_IP}" ]; then
        export DTPS_BASE_SWITCHBOARD_1="http://${VEHICLE_IP}:11811/"
    else
        export DTPS_BASE_SWITCHBOARD_1="http://${VEHICLE_NAME}.local:11811/"
    fi
fi


# robot's kvstore
export DTPS_BASE_KVSTORE_0="http+unix://%2Fdtps%2Fkvstore.sock/"

# avoid using mDNS when running onboard the vehicle
if [ "${DT_DEPLOYED_ONBOARD}" = "1" ] && [ "${netmode}" = "HOST" ]; then
    export DTPS_BASE_KVSTORE_1="http://localhost:11411/"
else
    # prefer IP address over mDNS
    if [ -n "${VEHICLE_IP}" ]; then
        export DTPS_BASE_KVSTORE_1="http://${VEHICLE_IP}:11411/"
    else
        export DTPS_BASE_KVSTORE_1="http://${VEHICLE_NAME}.local:11411/"
    fi
fi
