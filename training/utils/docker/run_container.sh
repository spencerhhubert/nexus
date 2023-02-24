#! /bin/bash
IMAGE="nexus_training:latest"
CONTAINER="nexus_training"

sudo docker stop $CONTAINER
sudo docker rm $CONTAINER

sudo docker run -d \
    -v /home/spencer/code/nexus/:/nexus/ \
    --gpus all \
    --device=/dev/video0:/dev/video0 \
    --name $CONTAINER \
    -it $IMAGE
