#! /bin/bash

CONTAINER_ID="nexus_ros"
IMAGE_ID="nexus_ros"

docker stop $CONTAINER_ID
docker rm $CONTAINER_ID

docker run -d \
    --env="DISPLAY" \
    --env="QT_X11_NO_MITSHM=1" \
    --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
    --name $CONTAINER_ID \
    -it $IMAGE_ID

xhost +local:`docker inspect --format='{{ .Config.Hostname }}' $CONTAINER_ID`

#docker start $CONTAINER_ID
