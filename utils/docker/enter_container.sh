#! /bin/bash

echo "Entering container " $CONTAINER

docker exec -it $CONTAINER /bin/bash
