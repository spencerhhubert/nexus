ARG BASE_IMAGE=ros:humble

FROM ${BASE_IMAGE} as base

ENV ROS_VERSION=humble
ENV PYTHON_VERSION=3.10

SHELL ["/bin/bash", "-c"]

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates ccache cmake curl git libjpeg-dev libgl1-mesa-glx \
        libegl1-mesa libxrandr2 libxrandr2 libxss1 libxcursor1 libxcomposite1 libasound2 \
        libxi6 libxtst6 wget libpng-dev p7zip-rar vim && \
    rm -rf /var/lib/apt/lists/*
RUN /usr/sbin/update-ccache-symlinks

RUN apt-get update && apt-get install -y python${PYTHON_VERSION} python3-pip
RUN ln -sf /usr/bin/python${PYTHON_VERSION} /usr/local/bin/python
RUN alias pip=pip3

RUN echo "source /opt/ros/${ROS_VERSION}/setup.bash" >> /root/.bashrc
RUN echo "export ROS_DOMAIN_ID=1" >> /root/.bashrc

RUN apt update && apt -y upgrade
#RUN apt install -y ~nros-rolling-rqt*
