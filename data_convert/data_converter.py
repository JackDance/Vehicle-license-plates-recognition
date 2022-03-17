# -*- coding: utf-8 -*-
"""
-------------------------------------------------
   File Name:     data_converter
   Description: converter CCPD dataset annotations to icdar format and PaddleOCR foramt.
   Author:        zhangluyao
   date:          2022/3/12
-------------------------------------------------
"""
import os
import cv2
import time

def convertCCPD2det(img_path, dst_folder):
    """
    将CCPD数据集的标注转换成文本检测要使用的icdar格式
    img_path: CCPD数据集中ccpd_base所在的文件夹
    dst_folder: 转换后的txt文件所在的文件夹
    """
    words_list = [
        "A", "B", "C", "D", "E",
        "F", "G", "H", "J", "K",
        "L", "M", "N", "P", "Q",
        "R", "S", "T", "U", "V",
        "W", "X", "Y", "Z", "0",
        "1", "2", "3", "4", "5",
        "6", "7", "8", "9"]

    con_list = [
        "皖", "沪", "津", "渝", "冀",
        "晋", "蒙", "辽", "吉", "黑",
        "苏", "浙", "京", "闽", "赣",
        "鲁", "豫", "鄂", "湘", "粤",
        "桂", "琼", "川", "贵", "云",
        "西", "陕", "甘", "青", "宁",
        "新"]

    # if not os.path.exists(dst_folder):
    #     os.mkdir(dst_folder)

    # dst_path = os.path.join(dst_folder, 'data_det.txt')
    # 将转换后的annotations写入data_det.txt中
    data = open(dst_folder + 'data_det.txt', 'w', encoding='UTF-8')
    for item in os.listdir(img_path):
        path = img_path + item
        path_split = path.split('/')[-2:]
        # sub_path为要写入txt文件的图像名
        sub_path = os.path.join(path_split[0],path_split[1])
        _, _, bbox, points, label, _, _ = item.split('-')
        points = points.split('_')
        points = [_.split('&') for _ in points]
        tmp = points[-2:] + points[:2]
        points = []
        for point in tmp:
            points.append([int(_) for _ in point])
        label = label.split('_')
        con = con_list[int(label[0])]
        words = [words_list[int(_)] for _ in label[1:]]
        label = con + ''.join(words)
        line = sub_path + '\t' + '[{"transcription": "%s", "points": %s}]' % (label, str(points))
        line = line[:] + '\n'
        data.write(line)
    #
    total = []
    # 读取data_det.txt中的每一行到total列表中
    with open(dst_folder + 'data_det.txt', 'r', encoding='UTF-8') as f:
        for line in f:
            total.append(line)
    # 生成训练split
    with open(dst_folder + 'train_det.txt', 'w', encoding='UTF-8') as f:
        for line in total[:-1000]:
            f.write(line)
    # 生成验证split
    with open(dst_folder + 'val_det.txt', 'w', encoding='UTF-8') as f:
        for line in total[-1000:]:
            f.write(line)

def convertCCPD2rec(img_path, dst_folder):
    """
    将CCPD数据集的标注转换成文字识别要使用的PaddleOCR格式
    img_path: CCPD数据集中ccpd_base所在的文件夹
    dst_folder: 目标文件夹
    """
    words_list = [
        "A", "B", "C", "D", "E",
        "F", "G", "H", "J", "K",
        "L", "M", "N", "P", "Q",
        "R", "S", "T", "U", "V",
        "W", "X", "Y", "Z", "0",
        "1", "2", "3", "4", "5",
        "6", "7", "8", "9"]

    con_list = [
        "皖", "沪", "津", "渝", "冀",
        "晋", "蒙", "辽", "吉", "黑",
        "苏", "浙", "京", "闽", "赣",
        "鲁", "豫", "鄂", "湘", "粤",
        "桂", "琼", "川", "贵", "云",
        "西", "陕", "甘", "青", "宁",
        "新"]
    # if not os.path.exists(dst_folder):
    #     os.mkdir(dst_folder)

    if not os.path.exists(dst_folder + 'croped_licence_plates'):
        os.mkdir(dst_folder + 'croped_licence_plates')
    dst_img_folder = os.path.join(dst_folder, 'croped_licence_plates/')

    count = 0
    data = open(dst_folder + 'data_rec.txt', 'w', encoding='UTF-8')
    for item in os.listdir(img_path):
        path = img_path + item
        _, _, bbox, _, label, _, _ = item.split('-')
        bbox = bbox.split('_')
        x1, y1 = bbox[0].split('&')
        x2, y2 = bbox[1].split('&')
        label = label.split('_')
        con = con_list[int(label[0])]
        words = [words_list[int(_)] for _ in label[1:]]
        label = con + ''.join(words)
        bbox = [int(_) for _ in [x1, y1, x2, y2]]
        img = cv2.imread(path)
        crop = img[bbox[1]:bbox[3], bbox[0]:bbox[2], :]
        cv2.imwrite('croped_license_plates/' + '%06d.jpg' % count, crop)
        data.write('croped_license_plates/' + '%06d.jpg\t%s\n' % (count, label))
        count += 1
    data.close()

    with open(dst_folder + 'word_dict.txt', 'w', encoding='UTF-8') as f:
        for line in words_list + con_list:
            f.write(line + '\n')

    total = []
    with open(dst_folder + 'data_rec.txt', 'r', encoding='UTF-8') as f:
        for line in f:
            total.append(line)

    with open(dst_folder + 'train_rec.txt', 'w', encoding='UTF-8') as f:
        for line in total[:-1000]:
            f.write(line)

    with open(dst_folder + 'val_rec.txt', 'w', encoding='UTF-8') as f:
        for line in total[-1000:]:
            f.write(line)

def main(img_path, dst_folder):
    print('Start converting! Please waiting...')
    start = time.time()
    # 1. 文本检测的数据格式转换
    # convertCCPD2det(img_path, dst_folder)
    # 2. 文字识别的数据格式转换
    convertCCPD2rec(img_path, dst_folder)
    end = time.time()
    print('Converting completed!\nTotal time is: %04d' % (end - start))

if __name__ == '__main__':
    # img_path和dst_folder要以/结尾
    img_path = r"/home/jackdance/Desktop/Program/PaddleOCR-2.4/train_data/ccpd19/det/imgs/"
    dst_folder = r"/home/jackdance/Desktop/Program/PaddleOCR-2.4/train_data/ccpd19/rec/"
    main(img_path, dst_folder)

    