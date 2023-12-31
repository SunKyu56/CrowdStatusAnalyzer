import torch
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from torchsummary import summary
from torch.optim.lr_scheduler import ReduceLROnPlateau
import torch.optim.lr_scheduler as lr_scheduler
from PIL import Image as Im
import cv2

import os,glob
import torch.nn as nn
import torch.optim as optim
import copy
import time
from MTL.model import resnet,mobilenet,efficientnet,swinT
from utils.train_utils import *
from utils.loss import FocalLoss
from utils.check_mode import check
from utils.visuallize import vis
import wandb

#################################################################
wandb.init(project='emotion',entity='kookmin_ai')
device='cuda:3' if torch.cuda.is_available() else 'cpu'
mode='emotion'
backbone='resnet152'
model=resnet.EmotionModel()
max_epoch=100
wandb.run.name=f'{backbone}'
#wandb.run.save()
################################################################
model_name=f'weight/tmp/{mode}128_{backbone}_xnor.pt'
print(f'device:{device}, mode:{mode}, backbone:{backbone}')
train_dl,val_dl,test_dl,criterion,optimizer,scheduler=check(mode,model)

model.to(device)
best_loss=float('inf')
best_acc=0
#wandb.watch(model,criterion,log='all',log_freq=100) #  gradient를 확인할 수 있음

# 마지막에 두 loss를 합쳐서 한 그래프에 보여주기 위해 loss array선언
train_losses=[]
val_losses=[]
train_acc=[]
val_acc=[]

for epoch in range(max_epoch):
    print('*'*60)
    current_lr=get_lr(optimizer)
    print(f'{epoch+1}/{max_epoch} current_lr:{current_lr}')
    model.train()
    train_loss, train_metric = loss_epoch(model, criterion, train_dl,device, phase='train',opt=optimizer)
    train_losses.append(train_loss)
    train_acc.append(train_metric)
    
    model.eval()
    with torch.no_grad():
        val_loss, val_metric = loss_epoch(model, criterion, val_dl,device,phase='val')
    val_losses.append(val_loss)
    val_acc.append(val_metric)    
    
    # loss 와 acc를 각각 기록하는 코드    
    wandb.log({'train_ loss':train_loss,
               'val_loss':val_loss,
               'train_acc':train_metric*100,
               'val_acc':val_metric*100},step=epoch+1)
    
    if val_loss < best_loss:
        best_loss = val_loss
        best_acc=val_metric
        best_model_wts = copy.deepcopy(model.state_dict())
        torch.save(model.state_dict(), model_name)
        print('Copied best model weights!')

    scheduler.step()
    if current_lr != get_lr(optimizer):
        print('Loading best model weights!')
        model.load_state_dict(best_model_wts)

    print('train loss: %.6f, val loss: %.6f, val_accuracy: %.2f' %(train_loss, val_loss, 100*val_metric))

with torch.no_grad():
    test_loss,test_metric=loss_epoch(model,criterion,test_dl,device,phase='test')

print(f'validation best acc:{best_acc*100:.2f}% best loss:{best_loss:.4f}, backbone:{backbone}')
print(f'test accuracy:{test_metric * 100:.2f}%')

test_imgs=glob.glob('testimgs/*.png')
vis(model,best_model_wts,device,max_epoch,train_losses,val_losses,train_acc,val_acc,test_imgs)
wandb.log({'validation best acc':best_acc*100,
           'test accuracy': test_metric*100})



