# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name:     train_val_split
   Description: 将PPOCRLabelv2标记出的检测数据Label.txt进行train和val分割
   Author:        zhangluyao
   date:          2022/5/29
-------------------------------------------------
"""
import os
import random

# def address_file_path_name(src_folder):
#     file_path = os.path.join(src_folder, 'data_det.txt')
#     with open(file_path, 'r', encoding='UTF-8') as f1, open('%s.bak' % 'data_det', "w", encoding='UTF-8') as f2:
#         for line in f1:
#             if "超清" in line:
#                 line = line.replace("超清", "imgs")
#             f2.write(line)
#     # os.remove(file_path)
#     os.rename("%s.bak" % 'data_det', 'data_det.txt')




def split_train_val(src_folder, dst_folder, train_ratio):
    total = []
    # 读取data_det.txt中的每一行到total列表中, data_det.txt为Label.txt
    with open(src_folder + 'data_det.txt', 'r', encoding='UTF-8') as f:
        for line in f:
            total.append(line)
    # 打乱列表顺序
    random.shuffle(total)
    # train data num
    train_num = int(len(total) * train_ratio)
    # 生成训练split
    with open(dst_folder + 'train_det.txt', 'w', encoding='UTF-8') as f:
        for line in total[:train_num]:
            f.write(line)
    # 生成验证split
    with open(dst_folder + 'val_det.txt', 'w', encoding='UTF-8') as f:
        for line in total[train_num:]:
            f.write(line)



if __name__ == '__main__':
    src_folder = r"/Users/jack/Downloads/tire/det/"
    dst_folder = r"/Users/jack/Downloads/tire/det/"
    train_ratio = 0.8
    split_train_val(src_folder, dst_folder, train_ratio)


