#! /bin/sh

if [ $(tmux ls | grep -c droidcam) -eq 1 ]; then
    tmux kill-session -t droidcam
fi

tmux new-session -d -s droidcam
tmux send-keys -t droidcam "droidcam-cli adb 4747 -dev=/dev/video0 -size=1920x1080" "Enter"
sleep 3
tmux send-keys -t droidcam "L" "Enter"
sleep 1
tmux send-keys -t droidcam "A" "Enter"
