#! /bin/bash
sudo docker run -d \
    --gpus all --runtime nvidia --privileged -e DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix \
    -it --name "nexus_ros" "nexus_ros"
