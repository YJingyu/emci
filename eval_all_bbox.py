from data._bbox_dataset import BBoxDataset
import torch
from models.saver import Saver_
from models import dense_local
from models import resnet18
import numpy as np
from utils.metrics import Metrics
from data import utils
import cv2
import os
from torch.utils.data import DataLoader


net = dense_local.DenseLocal().cuda()

#PATH = './ckpt'
a = BBoxDataset('/data/icme/crop/data/picture',
                '/data/icme/crop/data/landmark',
                '/data/icme/bbox',
                '/data/icme/valid',
                phase='eval',img_format='jpg')
#Saver.dir=PATH
saver = Saver_('exp/localcontext/ckpt', 'model')
current = None
net.eval()

epoch_size = len(a)
metrics = Metrics().add_nme().add_auc()
model_name = 'model-51200.pth'
saver.load(net, model_name)


all_pr = []
all_gt = []
save_dir = '/data/icme/crop/data/pred_landmark'
if not os.path.exists(save_dir):
    os.makedirs(save_dir)
batch_iterator = iter(DataLoader(a, batch_size=1, shuffle=False, num_workers=4))

for i in range(len(a)):
    image, gt, shape, name = next(batch_iterator)

    image = image.cuda()
    with torch.no_grad():
        pr = net.forward(image)
    shape = shape.data.numpy()[0]
    pr = pr.cpu().data.numpy()
    gt = gt.data.numpy()
    pr = np.reshape(pr, (-1, 2))
    pr[:, 0] *= shape[1]
    pr[:, 1] *= shape[0]
    # pr = utils.inv_norm_landmark(np.reshape(pr, (-1, 2)), bbox[0])
    gt = np.reshape(gt, (-1, 2))
    all_pr.append(pr)
    all_gt.append(gt)
    # save prediction
    utils.save_landmarks(pr, os.path.join(save_dir, name[0] + '.txt'))

all_gt = np.stack(all_gt, axis=0)
all_pr = np.stack(all_pr, axis=0)

nme = metrics.nme.update(np.reshape(all_gt, (-1, 106, 2)), np.reshape(all_pr, (-1, 106, 2)))
metrics.auc.update(nme)

print("NME: %f\nAUC: %f" % (metrics.nme.value, metrics.auc.value))
