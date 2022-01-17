from PIL import Image
import numpy as np
import sys
np.set_printoptions(threshold=sys.maxsize)
pic1 = 'PennFudanPed/PedMasks/FudanPed00001_mask.png'
pic2 = 'data/masked/part-9-11.jpg_masked.jpg'

def info(path):
	img = Image.open(path)
	data = np.asarray(img)
	print(data)
	print(data.shape)
	print(type(data))
	display(path)

def display(name):
	mask = Image.open(name)
	mask.putpalette([
	    0, 0, 0, # black background
	    255, 0, 0, # index 1 is red
	    255, 255, 0, # index 2 is yellow
	    255, 153, 0, # index 3 is orange
	])
	mask.show()


#info(pic1);
info(pic2)

