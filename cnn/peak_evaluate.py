import numpy as np
import os
import sys
import torch
from cnn.cnn_model import CNN
from cnn.peakonly_cnn import Classifier
from scipy.interpolate import interp1d


def peak_eval(orin_inten):
    # peakonly_path = r'D:\Bionet\DnsCl_CNN\cnn\peakonly_cnn.pt'
    # cnn_path = r'D:\Bionet\DnsCl_CNN\cnn\CNN_1000.pth'  # 调试时用这一行
    cnn_path = os.path.dirname(os.path.abspath(sys.executable)) + '/model.pth'  # 打包时用这一行
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    # print(f"Using {device} device")
    cnn = CNN().to(device)
    cnn.load_state_dict(torch.load(cnn_path, map_location=device))  # 加载模型
    cnn.eval()
    # classifier = Classifier().to(device)
    # classifier.load_state_dict(torch.load(peakonly_path, map_location=device))  # 加载模型
    # classifier.eval()

    # cnn_result = []
    # classifier_result = []

    interpolate = interp1d(np.arange(len(orin_inten)), orin_inten, kind='linear')
    inter_inten = interpolate(np.arange(256) / (256 - 1) * (len(orin_inten) - 1))  # 将输入长度插值为256
    inter_inten = torch.tensor(inter_inten / np.max(inter_inten), dtype=torch.float32, device=device)
    # length = len(orin_inten) * (len(x_ind) - 1) // (len(orin_inten) - 1)
    roi = inter_inten.view(1, 1, -1)

    cnn_output, _ = cnn(roi)
    cnn_output = cnn_output.view(-1)
    cnn_output = cnn_output.data.cpu().numpy()
    cnn_output = "{:.2f}".format(cnn_output[0] * 10)
    print(cnn_output)

    # classifier_output, _ = classifier(roi)
    # classifier_output = classifier_output.view(-1)
    # classifier_output = classifier_output.data.cpu().numpy()
    # classifier_output = "{:.2f}".format(classifier_output[1])
    # print(classifier_output)

    return cnn_output
