#! /bin/bash

echo "Running container " $CONTAINER

export MC_USB="/dev/ttyACM0"

docker stop $CONTAINER
docker rm $CONTAINER

docker run -d \
    -v /home/spencer/code/nexus:/nexus/ \
    --gpus all \
    --device=/dev/video0:/dev/video0 \
    --device=/dev/video1:/dev/video1 \
    --device=/dev/video2:/dev/video2 \
    --device=/dev/video3:/dev/video3 \
    --device=$MC_USB:$MC_USB \
    --device=/dev/ttyACM0:/dev/ttyACM0 \
    --device=/dev/ttyACM1:/dev/ttyACM1 \
    --device=/dev/ttyACM2:/dev/ttyACM2 \
    --name $CONTAINER \
    -it $IMAGE
