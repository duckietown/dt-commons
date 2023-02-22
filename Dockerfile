# parameters
ARG REPO_NAME="dt-commons"
ARG MAINTAINER="Andrea F. Daniele (afdaniele@duckietown.com)"
ARG DESCRIPTION="Base image containing common libraries and environment setup for non-ROS applications."
ARG ICON="square"

ARG ARCH
ARG DISTRO=ente
ARG DOCKER_REGISTRY=docker.io
ARG BASE_IMAGE=dt-base-environment
ARG BASE_TAG=${DISTRO}-${ARCH}
ARG LAUNCHER=default

# define base image
FROM ${DOCKER_REGISTRY}/duckietown/${BASE_IMAGE}:${BASE_TAG} as base

# recall all arguments
ARG REPO_NAME
ARG DESCRIPTION
ARG MAINTAINER
ARG ICON
ARG DISTRO
ARG OS_DISTRO
ARG BASE_TAG
ARG BASE_IMAGE
ARG LAUNCHER
# - buildkit
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH
ARG TARGETVARIANT

# define and create repository path
ARG REPO_PATH="${SOURCE_DIR}/${REPO_NAME}"
ARG LAUNCH_PATH="${LAUNCH_DIR}/${REPO_NAME}"
RUN mkdir -p "${REPO_PATH}" "${LAUNCH_PATH}"
WORKDIR "${REPO_PATH}"

# keep some arguments as environment variables
ENV DT_MODULE_TYPE="${REPO_NAME}" \
    DT_MODULE_DESCRIPTION="${DESCRIPTION}" \
    DT_MODULE_ICON="${ICON}" \
    DT_MAINTAINER="${MAINTAINER}" \
    DT_REPO_PATH="${REPO_PATH}" \
    DT_LAUNCH_PATH="${LAUNCH_PATH}" \
    DT_LAUNCHER="${LAUNCHER}"

# duckie user
ENV DT_USER_NAME="duckie" \
    DT_USER_UID=2222 \
    DT_GROUP_NAME="duckie" \
    DT_GROUP_GID=2222 \
    DT_USER_HOME="/home/duckie"

# install apt dependencies
COPY ./dependencies-apt.txt "${REPO_PATH}/"
RUN dt-apt-install "${REPO_PATH}/dependencies-apt.txt"

# install python dependencies
ARG PIP_INDEX_URL="https://pypi.org/simple/"
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
COPY ./dependencies-py3.* "${REPO_PATH}/"
RUN python3 -m pip install -U -r ${REPO_PATH}/dependencies-py3.txt

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
COPY assets/setup/${TARGETPLATFORM}/setup.sh /tmp/setup-by-arch.sh
RUN /tmp/setup-by-arch.sh

# create `duckie` user
RUN addgroup --gid ${DT_GROUP_GID} "${DT_GROUP_NAME}" && \
    useradd \
        --create-home \
        --home-dir "${DT_USER_HOME}" \
        --comment "Duckietown User" \
        --shell "/bin/bash" \
        --password "aa26uhROPk6sA" \
        --uid ${DT_USER_UID} \
        --gid ${DT_GROUP_GID} \
        "${DT_USER_NAME}"

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
    org.duckietown.label.platform.os="${TARGETOS}" \
    org.duckietown.label.platform.architecture="${TARGETARCH}" \
    org.duckietown.label.platform.variant="${TARGETVARIANT}" \
    org.duckietown.label.code.location="${REPO_PATH}" \
    org.duckietown.label.code.version.distro="${DISTRO}" \
    org.duckietown.label.base.image="${BASE_IMAGE}" \
    org.duckietown.label.base.tag="${BASE_TAG}" \
    org.duckietown.label.maintainer="${MAINTAINER}"

# relax healthcheck to include ND as healthy state
HEALTHCHECK \
    --interval=5s \
    CMD cat /health && grep -q '^healthy\|ND$' /health
