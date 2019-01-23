from models import dense201
from models import resnet18
import torch.nn as nn
from models import saver
from utils import alignment
import numpy as np
import torch


class IterModel(nn.Module):

    def __init__(self):
        super(IterModel, self).__init__()
        self.model1 = resnet18.ResNet18()
        self.model2 = dense201.Dense201()

        sv = saver.Saver('backup', 'model')
        sv.load(self.model2, 'aligned_densenet-166400.pth')
        sv.load(self.model1, 'resnet18-9200.pth')

        self.aligner = alignment.Align(reference_path='cache/mean_landmarks.pkl', scale=(224, 224), margin=(0.15, 0.1))
        self.inference = False

    def forward(self, x):
        landmark1 = self.model(x)
        # align
        image = x.cpu().data.numpy()
        # unnormalize
        landmark2 = (landmark1.view(-1, 106, 2) * 223).cpu().data.numpy()
        image = np.transpose(image, [0, 2, 3, 1])
        i_batch = []
        T_batch = []
        for i in range(image.shape[0]):
            aligned, _, T = self.aligner(image[i], landmark2[i], [0, 0, 223, 223])
            aligned = np.transpose(aligned, [2, 0, 1])
            i_batch.append(aligned)
            T[2] /= 223
            T[0:2] = np.linalg.inv(T[0:2])
            T_batch.append(T)
        aligned = torch.tensor(np.stack(aligned, axis=0), requires_grad=False).cuda()
        T = torch.tensor(np.stack(T_batch, axis=0), requires_grad=False).cuda()
        landmark2 = self.model(aligned).cpu().data.numpy()
        landmark2 = np.reshape(landmark2, (-1, 106, 2))
        landmark2 = (landmark2 - T[:, 2:, :]) @ T[:, 0 : 2, ]
        landmark2 = landmark2.view(-1)
        return landmark1, landmark2