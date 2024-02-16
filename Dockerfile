# parameters
ARG PROJECT_NAME
ARG PROJECT_DESCRIPTION
ARG PROJECT_MAINTAINER
# pick an icon from: https://fontawesome.com/v4.7.0/icons/
ARG PROJECT_ICON="cube"
ARG PROJECT_FORMAT_VERSION

# ==================================================>
# ==> Do not change the code below this line
ARG ARCH
ARG DISTRO
ARG DOCKER_REGISTRY
ARG BASE_REPOSITORY
ARG BASE_ORGANIZATION=duckietown
ARG BASE_TAG=${DISTRO}-${ARCH}
ARG LAUNCHER=default

# define base image
FROM ${DOCKER_REGISTRY}/${BASE_ORGANIZATION}/${BASE_REPOSITORY}:${BASE_TAG} as base

# recall all arguments
ARG ARCH
ARG DISTRO
ARG DOCKER_REGISTRY
ARG PROJECT_NAME
ARG PROJECT_DESCRIPTION
ARG PROJECT_MAINTAINER
ARG PROJECT_ICON
ARG PROJECT_FORMAT_VERSION
ARG BASE_TAG
ARG BASE_REPOSITORY
ARG BASE_ORGANIZATION
ARG LAUNCHER
# - buildkit
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH
ARG TARGETVARIANT

# check build arguments
RUN dt-args-check \
    "PROJECT_NAME" "${PROJECT_NAME}" \
    "PROJECT_DESCRIPTION" "${PROJECT_DESCRIPTION}" \
    "PROJECT_MAINTAINER" "${PROJECT_MAINTAINER}" \
    "PROJECT_ICON" "${PROJECT_ICON}" \
    "PROJECT_FORMAT_VERSION" "${PROJECT_FORMAT_VERSION}" \
    "ARCH" "${ARCH}" \
    "DISTRO" "${DISTRO}" \
    "DOCKER_REGISTRY" "${DOCKER_REGISTRY}" \
    "BASE_REPOSITORY" "${BASE_REPOSITORY}" \
    && dt-check-project-format "${PROJECT_FORMAT_VERSION}"

# define/create repository path
ARG PROJECT_PATH="${SOURCE_DIR}/${PROJECT_NAME}"
ARG PROJECT_LAUNCHERS_PATH="${LAUNCHERS_DIR}/${PROJECT_NAME}"
RUN mkdir -p "${PROJECT_PATH}" "${PROJECT_LAUNCHERS_PATH}"
WORKDIR "${PROJECT_PATH}"

# keep some arguments as environment variables
ENV DT_PROJECT_NAME="${PROJECT_NAME}" \
    DT_PROJECT_DESCRIPTION="${PROJECT_DESCRIPTION}" \
    DT_PROJECT_MAINTAINER="${PROJECT_MAINTAINER}" \
    DT_PROJECT_ICON="${PROJECT_ICON}" \
    DT_PROJECT_PATH="${PROJECT_PATH}" \
    DT_PROJECT_LAUNCHERS_PATH="${PROJECT_LAUNCHERS_PATH}" \
    DT_LAUNCHER="${LAUNCHER}"

# duckie user
ENV DT_USER_NAME="duckie" \
    DT_USER_UID=2222 \
    DT_GROUP_NAME="duckie" \
    DT_GROUP_GID=2222 \
    DT_USER_HOME="/home/duckie"

# install apt dependencies
COPY ./dependencies-apt.txt "${PROJECT_PATH}/"
RUN dt-apt-install ${PROJECT_PATH}/dependencies-apt.txt

# install python3 dependencies
ARG PIP_INDEX_URL="https://pypi.org/simple"
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
COPY ./dependencies-py3.* "${PROJECT_PATH}/"
RUN dt-pip3-install "${PROJECT_PATH}/dependencies-py3.*"

# install LCM
ENV LCM_VERSION="1.5.0"
RUN cd /tmp/ \
    && git clone -b "v${LCM_VERSION}" https://github.com/lcm-proj/lcm \
    && mkdir -p lcm/build \
    && cd lcm/build \
    && cmake .. \
    && make \
    && make install \
    && cd ~ \
    && rm -rf /tmp/lcm

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

# copy the assets (needed by sibling images)
COPY ./assets "${PROJECT_PATH}/assets"

# copy image root
COPY ./assets/root/. /

# configure arch-specific environment
RUN ${PROJECT_PATH}/assets/setup/${TARGETPLATFORM}/setup.sh

# install assets
RUN cp ${PROJECT_PATH}/assets/bin/* /usr/local/bin/ && \
    cp ${PROJECT_PATH}/assets/entrypoint.sh /entrypoint.sh && \
    cp ${PROJECT_PATH}/assets/environment.sh /environment.sh

# copy the source code
COPY ./packages "${PROJECT_PATH}/packages"

# build packages
RUN dt-colcon-build ${WORKSPACE_DIR}

# source environment on every bash session
RUN echo "source /environment.sh" >> /etc/bash.bashrc

# configure entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# install launcher scripts
COPY ./launchers/. "${PROJECT_LAUNCHERS_PATH}/"
RUN dt-install-launchers "${PROJECT_LAUNCHERS_PATH}"

# create health file
RUN echo ND > /health &&  \
    chmod 777 /health && \
    sudo -u ${DT_USER_NAME} touch /health

# define healthcheck
HEALTHCHECK \
    --interval=30s \
    CMD cat /health && grep -q '^healthy\|ND$' /health

# define default command
CMD ["bash", "-c", "dt-launcher-${DT_LAUNCHER}"]

# store module metadata
LABEL \
    # module info
    org.duckietown.label.project.name="${PROJECT_NAME}" \
    org.duckietown.label.project.description="${PROJECT_DESCRIPTION}" \
    org.duckietown.label.project.maintainer="${PROJECT_MAINTAINER}" \
    org.duckietown.label.project.icon="${PROJECT_ICON}" \
    org.duckietown.label.project.path="${PROJECT_PATH}" \
    org.duckietown.label.project.launchers.path="${PROJECT_LAUNCHERS_PATH}" \
    # format
    org.duckietown.label.format.version="${PROJECT_FORMAT_VERSION}" \
    # platform info
    org.duckietown.label.platform.os="${TARGETOS}" \
    org.duckietown.label.platform.architecture="${TARGETARCH}" \
    org.duckietown.label.platform.variant="${TARGETVARIANT}" \
    # code info
    org.duckietown.label.code.distro="${DISTRO}" \
    org.duckietown.label.code.launcher="${LAUNCHER}" \
    org.duckietown.label.code.python.registry="${PIP_INDEX_URL}" \
    # base info
    org.duckietown.label.base.organization="${BASE_ORGANIZATION}" \
    org.duckietown.label.base.repository="${BASE_REPOSITORY}" \
    org.duckietown.label.base.tag="${BASE_TAG}"
# <== Do not change the code above this line
# <==================================================
