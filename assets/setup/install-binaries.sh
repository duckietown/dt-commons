#!/usr/bin/env bash

# install binaries
for file in $(ls ${SOURCE_DIR}/dt-commons/assets/bin/); do
    echo "Installing ./assets/bin/$file -> /usr/local/bin/$file"
    sudo ln -s ${SOURCE_DIR}/dt-commons/assets/bin/$file /usr/local/bin/$file
done

# install entrypoint and environment scripts
echo "Installing ./assets/entrypoint.sh -> /entrypoint.sh"
sudo ln -s ${SOURCE_DIR}/dt-commons/assets/entrypoint.sh /entrypoint.sh
echo "Installing ./assets/environment.sh -> /environment.sh"
sudo ln -s ${SOURCE_DIR}/dt-commons/assets/environment.sh /environment.sh