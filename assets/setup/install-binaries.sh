#!/usr/bin/env bash

# install binaries
for file in $(ls ${DT_PROJECT_PATH}/assets/bin/); do
    echo "Installing ./assets/bin/$file -> /usr/local/bin/$file"
    sudo ln -s ${DT_PROJECT_PATH}/assets/bin/$file /usr/local/bin/$file
done

# install entrypoint and environment scripts
echo "Installing ./assets/entrypoint.sh -> /entrypoint.sh"
sudo ln -s ${DT_PROJECT_PATH}/assets/entrypoint.sh /entrypoint.sh
echo "Installing ./assets/environment.sh -> /environment.sh"
sudo ln -s ${DT_PROJECT_PATH}/assets/environment.sh /environment.sh