#! /bin/bash

echo "Running container " $CONTAINER

export MC_USB="/dev/ttyACM0"

docker stop $CONTAINER
docker rm $CONTAINER

docker run -d \
    -v /home/spencer/code/nexus:/nexus/ \
    --gpus all \
    --device=/dev/video0:/dev/video0 \
    --device=$MC_USB:$MC_USB \
    --name $CONTAINER \
    -it $IMAGE
