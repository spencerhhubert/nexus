During development I'm using a Logitech C920, which OpenCV is unable to control the focus for apparently. I'm going to control the focus directly through Ubuntu, but that needs to be added to the code in the final version with the final camera sensor.

https://christitus.com/logitech-c920-linux-driver/

I let the camera focus on the piece and gave:
```
v4l2-ctl -d /dev/video0 --set-ctrl=focus_auto=0
v4l2-ctl -d /dev/video0 --set-ctrl=focus_absolute=50

```
The following delivers the device ID
```
v4l2-ctl --list-devices

```
These are the controls
```
v4l2-ctl -d /dev/video0 --list-ctrls

```
