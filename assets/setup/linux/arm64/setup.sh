#!/usr/bin/env bash

set -e

# install VC library
apt-get update
apt-get install -y --no-install-recommends \
    libraspberrypi-bin
rm -rf /var/lib/apt/lists/*

set +e