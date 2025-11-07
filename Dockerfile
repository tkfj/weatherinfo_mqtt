FROM python:3.13-slim

ARG USERNAME=appuser
ARG USER_UID=1000
ARG USER_GID=${USER_UID}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        sudo \
        locales \
        build-essential \
        git ca-certificates gnupg \
        && rm -rf /var/lib/apt/lists/*

RUN locale-gen --lang C.UTF-8

ENV LANG C.UTF-8
ENV LANGUAGE C
ENV LC_ALL C.UTF-8
ENV TZ Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive

RUN groupadd --gid ${USER_GID} ${USERNAME} \
  && useradd -m --shell /bin/bash --uid ${USER_UID} --gid ${USER_GID} ${USERNAME} \
  && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN echo "alias ll='ls -alF'" >> /etc/bash.bashrc && \
    echo "alias la='ls -A'" >> /etc/bash.bashrc && \
    echo "alias l='ls -CF'" >> /etc/bash.bashrc

RUN pip install --no-cache-dir \
    slack-sdk \
    python-dotenv \
    Pillow \
    paho-mqtt \
    requests 

WORKDIR /usr/src/app
USER ${USERNAME}
