#!/usr/bin/env bash

# make the VC library reachable
cd /opt/ || exit
tar zxvf ./vc.tgz
echo /opt/vc/lib > /etc/ld.so.conf.d/00-vmcs.conf
ldconfig