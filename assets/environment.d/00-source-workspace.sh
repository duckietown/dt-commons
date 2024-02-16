SETUP_FPATH=${WORKSPACE_DIR}/install/setup.bash

if [ -f ${SETUP_FPATH} ]; then
  source ${WORKSPACE_DIR}/install/setup.bash
else
  echo "WARNING: Workspace ${WORKSPACE_DIR} not built. Some packages might not be available."
fi
