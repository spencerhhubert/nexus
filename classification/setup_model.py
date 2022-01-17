import os
import torch
import torchvision
import torch.nn as nn
from torchvision import datasets, models
import torchvision.transforms as T
import matplotlib.pyplot as plt

def get_transform(train):
	transforms = []
	# converts the image, a PIL image, into a PyTorch Tensor
	transforms.append(T.ToTensor())
	#transforms.append(T.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)))
	# want to grayscale all these pictures in the future but as is the model blows up because they're only 1 layer matrices
	transforms.append(T.Pad(25))
	if train:
		# during training, randomly flip the training images
		# and ground-truth for data augmentation
		transforms.append(T.RandomResizedCrop(256))
		transforms.append(T.RandomHorizontalFlip(0.5))
		transforms.append(T.ColorJitter(brightness=0.3, contrast=0.5, saturation=0.5, hue=0.3))
	else:
		transforms.append(T.Resize(256))
	transforms.append(T.Grayscale(3))
	return T.Compose(transforms)


def get_resnet_model(num_classes):
	# get reset model and modify for transfer learning	
	model = models.resnet34(pretrained=True);
	# re-initialize the last layer with new number of output features as num_classes
	model.fc = nn.Linear(model.fc.in_features, num_classes)
	return model;

path = 'monkey'
dataset = datasets.ImageFolder(path, get_transform(True))
dataset_test = datasets.ImageFolder(path, get_transform(False))
print(len(dataset))

torch.manual_seed(1)
indices = torch.randperm(len(dataset)).tolist()

val = 50                                                                                                                                                     
dataset = torch.utils.data.Subset(dataset, indices[:-val])
dataset_test = torch.utils.data.Subset(dataset_test, indices[-val:])

data_loader = torch.utils.data.DataLoader(
        dataset, batch_size=4, shuffle=True, num_workers=2)

data_loader_test = torch.utils.data.DataLoader(
        dataset_test, batch_size=1, shuffle=False, num_workers=2)

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

def imshow(tensor):
	array = tensor.numpy().transpose((1, 2, 0))
	plt.imshow(array)
	plt.pause(1)

inputs, classes = next(iter(data_loader))
imshow(torchvision.utils.make_grid(inputs))

num_classes = len(os.listdir(path))
model = get_resnet_model(num_classes)
model.to(device)

