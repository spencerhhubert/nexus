#! /bin/bash

echo "Building image " $IMAGE

docker build -t $IMAGE -f Dockerfile.robot.dev $PWD
