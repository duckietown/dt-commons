# parameters
ARG REPO_NAME="dt-commons"
ARG MAINTAINER="Andrea F. Daniele (afdaniele@ttic.edu)"
ARG DESCRIPTION="Base image containing common libraries and environment setup for non-ROS applications."
ARG ICON="square"

ARG ARCH=arm32v7
ARG DISTRO=daffy
ARG BASE_TAG=${DISTRO}-${ARCH}
ARG BASE_IMAGE=dt-base-environment
ARG LAUNCHER=default

# define base image
ARG DOCKER_REGISTRY=docker.io
FROM ${DOCKER_REGISTRY}/duckietown/${BASE_IMAGE}:${BASE_TAG} as BASE

# recall all arguments
ARG REPO_NAME
ARG DESCRIPTION
ARG MAINTAINER
ARG ICON
ARG ARCH
ARG DISTRO
ARG OS_DISTRO
ARG BASE_TAG
ARG BASE_IMAGE
ARG LAUNCHER

# define and create repository path
ARG REPO_PATH="${SOURCE_DIR}/${REPO_NAME}"
ARG LAUNCH_PATH="${LAUNCH_DIR}/${REPO_NAME}"
RUN mkdir -p "${REPO_PATH}"
RUN mkdir -p "${LAUNCH_PATH}"
WORKDIR "${REPO_PATH}"

# keep some arguments as environment variables
ENV DT_MODULE_TYPE "${REPO_NAME}"
ENV DT_MODULE_DESCRIPTION "${DESCRIPTION}"
ENV DT_MODULE_ICON "${ICON}"
ENV DT_MAINTAINER "${MAINTAINER}"
ENV DT_REPO_PATH "${REPO_PATH}"
ENV DT_LAUNCH_PATH "${LAUNCH_PATH}"
ENV DT_LAUNCHER "${LAUNCHER}"

# install apt dependencies
COPY ./dependencies-apt.txt "${REPO_PATH}/"
RUN dt-apt-install "${REPO_PATH}/dependencies-apt.txt"

# install python dependencies
ARG PIP_INDEX_URL="https://pypi.org/simple"
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
RUN echo PIP_INDEX_URL=${PIP_INDEX_URL}

COPY ./dependencies-py3.txt "${REPO_PATH}/"
RUN python3 -m pip install  -r ${REPO_PATH}/dependencies-py3.txt

# install LCM
RUN cd /tmp/ \
    && git clone -b v1.4.0 https://github.com/lcm-proj/lcm \
    && mkdir -p lcm/build \
    && cd lcm/build \
    && cmake .. \
    && make \
    && make install \
    && cd ~ \
    && rm -rf /tmp/lcm

# configure arch-specific environment
COPY assets/setup/by-arch/${ARCH} /tmp/.setup-by-arch
RUN /tmp/.setup-by-arch/setup.sh

# copy the source code
COPY ./packages "${REPO_PATH}/packages"

# copy binaries
COPY ./assets/bin/. /usr/local/bin/

# copy environment / entrypoint
COPY assets/entrypoint.sh /entrypoint.sh
COPY assets/environment.sh /environment.sh

# copy code setup script
COPY assets/code/setup.bash /code/setup.bash

# source environment on every bash session
RUN echo "source /environment.sh" >> ~/.bashrc

# configure entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# install launcher scripts
COPY ./launchers/. "${LAUNCH_PATH}/"
RUN dt-install-launchers "${LAUNCH_PATH}"

# define default command
CMD ["bash", "-c", "dt-launcher-${DT_LAUNCHER}"]

# store module metadata
LABEL org.duckietown.label.module.type="${REPO_NAME}" \
    org.duckietown.label.module.description="${DESCRIPTION}" \
    org.duckietown.label.module.icon="${ICON}" \
    org.duckietown.label.architecture="${ARCH}" \
    org.duckietown.label.code.location="${REPO_PATH}" \
    org.duckietown.label.code.version.distro="${DISTRO}" \
    org.duckietown.label.base.image="${BASE_IMAGE}" \
    org.duckietown.label.base.tag="${BASE_TAG}" \
    org.duckietown.label.maintainer="${MAINTAINER}"
