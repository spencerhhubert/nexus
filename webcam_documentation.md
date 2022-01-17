# main settings set
v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0
v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50
# find device id
v4l2-ctl --list-devices
# more controls
v4l2-ctl -d /dev/video0 --list-ctrls

