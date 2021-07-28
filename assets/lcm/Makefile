THIS:=$(firstword $(MAKEFILE_LIST))
DIR:=$(shell dirname $(realpath ${THIS}))

all:
	@$(MAKE) -f ${THIS} clean
	@$(MAKE) -f ${THIS} build
	@$(MAKE) -f ${THIS} install
	@$(MAKE) -f ${THIS} clean

build:
	cd ${DIR}
	# build for Python
	lcm-gen -p ${DIR}/dt_communication_msg_t.lcm
	echo "Messages built!"
	# ---

clean:
	# clean-up
	rm -rf ${DIR}/dt_communication_utils
	echo "All cleaned up!"
	# ---

install:
	# move build message to the package
	mv ${DIR}/dt_communication_utils/dt_communication_msg_t.py \
	   ${DIR}/../../packages/dt_communication_utils/dt_communication_msg_t.py
	echo "Messages installed!"
	# ---

