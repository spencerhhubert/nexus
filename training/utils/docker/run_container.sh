#! /bin/bash
IMAGE="nexus_training:latest"
CONTAINER="nexus_training"

sudo docker stop $CONTAINER
sudo docker rm $CONTAINER

sudo docker run -d \
    -v /home/spencer/code/nexus/:/nexus/ \
    --gpus all \
    --name $CONTAINER \
    -it $IMAGE
