#!/usr/bin/env bash

# possible values are: BRIDGE, HOST, NONE
netmode=$(dt-get-network-mode)

# robot's switchboard
export DTPS_BASE_SWITCHBOARD_0="http+unix://%2Fdtps%2Fswitchboard.sock"


# avoid using mDNS when running onboard the vehicle
if [ "${DT_DEPLOYED_ONBOARD}" = "1" ] && [ "${netmode}" = "HOST" ]; then
    export DTPS_BASE_SWITCHBOARD_1="http://localhost:11511"
else
    export DTPS_BASE_SWITCHBOARD_1="http://${VEHICLE_NAME}.local:11511"
fi
