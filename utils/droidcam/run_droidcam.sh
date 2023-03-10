#! /bin/sh

tmux kill-session -t droidcam

tmux new-session -d -s droidcam
tmux send-keys -t droidcam "droidcam-cli 192.168.1.44 4747 -dev=/dev/video2 -size=1920x1080" "Enter"
sleep 3
tmux send-keys -t droidcam "L" "Enter"
