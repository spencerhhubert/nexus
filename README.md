# nexus
A machine that sorts LEGO

This is a work in progress

This project consists of three main parts, 1) the feeder 2) classifcation and 3) distribution. Currently the focus is on classifcation.

The general strategy is to train a model primarily on rendered images combined with images of physical pieces such that the model can correlate a connection between the geometry of a rendered peice and its physical counterpart. This will allow us to recognize physical pieces without ever having seen them physically, greatly reducing the amount of work needed to collect data and update the model with new pieces.

segmentation/ contains code for creating masks of pieces on the conveyer belt:
![alt text](https://raw.githubusercontent.com/spencerhhubert/crayon/main/example_pic1.png)
![alt text](https://raw.githubusercontent.com/spencerhhubert/crayon/main/example_pic2.png)

The conveyer belt is checkered to support this process with any color of piece

In classification/ those cropped images are then combined with renders of the same pieces from [Brick Renderer](https://github.com/spencerhhubert/brick-renderer) under the same class names and trained with a transferred ResNet34 model.

We alter the colors with a few transformations and this is generally what the data looks like:

![alt text](https://raw.githubusercontent.com/spencerhhubert/nexus/main/example_pic1.png)

The model needs work, but the theory as been proved true that a piece can be identified only based on its renders. With about 50 classes we're getting about 60% accuracy. I believe with a heiarchical apporach, more data, and adjustments to the layout of the final layers, this can be improved to a working level. At that point I'll be moving onto the distribution segment of the project.
