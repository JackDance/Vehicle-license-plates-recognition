# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import sys
import subprocess

__dir__ = os.path.dirname(os.path.abspath(__file__))
sys.path.append(__dir__)
sys.path.append(os.path.abspath(os.path.join(__dir__, '../..')))

os.environ["FLAGS_allocator_strategy"] = 'auto_growth'

import cv2
import copy
import numpy as np
import time
import logging
from PIL import Image
import tools.infer.utility as utility
import tools.infer.predict_rec as predict_rec
import tools.infer.predict_det as predict_det
from ppocr.utils.utility import get_image_file_list, check_and_read_gif
from ppocr.utils.logging import get_logger
from tools.infer.utility import draw_ocr_box_txt, get_rotate_crop_image, draw_box_txt
logger = get_logger()


class TextSystem(object):
    def __init__(self, args):
        if not args.show_log:
            logger.setLevel(logging.INFO)

        self.text_detector = predict_det.TextDetector(args)
        self.text_recognizer = predict_rec.TextRecognizer(args)
        self.drop_score = args.drop_score

        self.args = args
        self.crop_image_res_index = 0

    def draw_crop_rec_res(self, output_dir, img_crop_list, rec_res):
        os.makedirs(output_dir, exist_ok=True)
        bbox_num = len(img_crop_list)
        for bno in range(bbox_num):
            cv2.imwrite(
                os.path.join(output_dir,
                             f"mg_crop_{bno+self.crop_image_res_index}.jpg"),
                img_crop_list[bno])
            logger.debug(f"{bno}, {rec_res[bno]}")
        self.crop_image_res_index += bbox_num

    def __call__(self, img, cls=True):
        ori_im = img.copy()
        # start text detect
        dt_boxes, elapse = self.text_detector(img)

        logger.debug("dt_boxes num : {}, elapse : {}".format(
            len(dt_boxes), elapse))
        if dt_boxes is None:
            return None, None
        img_crop_list = []

        dt_boxes = sorted_boxes(dt_boxes)

        for bno in range(len(dt_boxes)):
            tmp_box = copy.deepcopy(dt_boxes[bno])
            img_crop = get_rotate_crop_image(ori_im, tmp_box)
            img_crop_list.append(img_crop)
        # start text recognize
        rec_res, elapse = self.text_recognizer(img_crop_list)
        logger.debug("rec_res num  : {}, elapse : {}".format(
            len(rec_res), elapse))
        if self.args.save_crop_res:
            self.draw_crop_rec_res(self.args.crop_res_save_dir, img_crop_list,
                                   rec_res)
        filter_boxes, filter_rec_res = [], []
        for box, rec_reuslt in zip(dt_boxes, rec_res):
            text, score = rec_reuslt
            if score >= self.drop_score:
                filter_boxes.append(box)
                filter_rec_res.append(rec_reuslt)
        return filter_boxes, filter_rec_res


def sorted_boxes(dt_boxes):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """
    num_boxes = dt_boxes.shape[0]
    sorted_boxes = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))
    _boxes = list(sorted_boxes)

    for i in range(num_boxes - 1):
        if abs(_boxes[i + 1][0][1] - _boxes[i][0][1]) < 10 and \
                (_boxes[i + 1][0][0] < _boxes[i][0][0]):
            tmp = _boxes[i]
            _boxes[i] = _boxes[i + 1]
            _boxes[i + 1] = tmp
    return _boxes


def main(args):
    # predict from video file or camera video stream
    if args.video_file is not None or args.camera_id != -1:
        # ?????????????????????????????????????????????
        if args.camera_id != -1:
            capture = cv2.VideoCapture(args.camera_id)
        else:
            capture = cv2.VideoCapture(args.video_file)
            video_name = os.path.splitext(os.path.basename(args.video_file))[
                             0] + '.mp4'
        # Get Video info : resolution, fps, frame count
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.debug("fps: %d, frame_count: %d" % (fps, frame_count))

        index = 0
        while (1):
            # read every frame
            ret, frame = capture.read()
            if not ret:
                break
            index += 1
            logger.debug('detect frame: %d' % index)

            text_sys = TextSystem(args)
            is_visualize = True
            font_path = args.vis_font_path
            drop_score = args.drop_score

            # warm up 10 times
            if args.warmup:
                img = np.random.uniform(0, 255, [640, 640, 3]).astype(np.uint8)
                for i in range(10):
                    res = text_sys(img)

            total_time = 0
            cpu_mem, gpu_mem, gpu_util = 0, 0, 0
            _st = time.time()
            count = 0

            if frame is None:
                logger.debug("error in loading image:{}".format(frame))
                continue
            starttime = time.time()
            # rec_res is the last recognition results.
            dt_boxes, rec_res = text_sys(frame)
            elapse = time.time() - starttime
            total_time += elapse

            logger.debug(
                str(index) + "  Predict time of frame%d: %.3fs" % (index, elapse))
            for text, score in rec_res:
                logger.debug("{}, {:.3f}".format(text, score))

            if is_visualize:
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                boxes = dt_boxes
                txts = [rec_res[i][0] for i in range(len(rec_res))]
                scores = [rec_res[i][1] for i in range(len(rec_res))]

                draw_img = draw_ocr_box_txt(
                    image,
                    boxes,
                    txts,
                    scores,
                    drop_score=drop_score,
                    font_path=font_path)
                draw_img_save_dir = args.draw_img_save_dir
                os.makedirs(draw_img_save_dir, exist_ok=True)

                frame2_name = str(index) + '.png'

                cv2.imwrite(
                    os.path.join(draw_img_save_dir, frame2_name),
                    draw_img[:, :, ::-1])
                logger.debug("The visualized image saved in {}".format(
                    os.path.join(draw_img_save_dir, frame2_name)))

                # ??????????????????????????????????????????????????????
                cv2.namedWindow("Detected Images:", 0)
                cv2.resizeWindow("Detected Images:", 640, 480)
                cv2.imshow("Detected Images:", draw_img[:, :, ::-1])
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        logger.info("The predict total time is {}".format(time.time() - _st))
        if args.benchmark:
            text_sys.text_detector.autolog.report()
            text_sys.text_recognizer.autolog.report()

    else:
        # predict from image
        image_file_list = get_image_file_list(args.image_dir)
        image_file_list = image_file_list[args.process_id::args.total_process_num]
        text_sys = TextSystem(args)
        is_visualize = True
        font_path = args.vis_font_path
        drop_score = args.drop_score

        # warm up 10 times
        if args.warmup:
            img = np.random.uniform(0, 255, [640, 640, 3]).astype(np.uint8)
            for i in range(10):
                res = text_sys(img)

        total_time = 0
        cpu_mem, gpu_mem, gpu_util = 0, 0, 0
        _st = time.time()
        count = 0
        for idx, image_file in enumerate(image_file_list):

            img, flag = check_and_read_gif(image_file)
            if not flag:
                img = cv2.imread(image_file)
            if img is None:
                logger.debug("error in loading image:{}".format(image_file))
                continue
            starttime = time.time()
            # rec_res is the last recognition results.
            dt_boxes, rec_res = text_sys(img)
            elapse = time.time() - starttime
            total_time += elapse

            logger.debug(
                str(idx) + "  Predict time of %s: %.3fs" % (image_file, elapse))
            for text, score in rec_res:
                logger.debug("{}, {:.3f}".format(text, score))

            if is_visualize:
                image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                boxes = dt_boxes
                txts = [rec_res[i][0] for i in range(len(rec_res))]
                scores = [rec_res[i][1] for i in range(len(rec_res))]

                # ??????
                draw_img = draw_ocr_box_txt(
                    image,
                    boxes,
                    txts,
                    scores,
                    drop_score=drop_score,
                    font_path=font_path)
                draw_img_save_dir = args.draw_img_save_dir
                os.makedirs(draw_img_save_dir, exist_ok=True)
                if flag:
                    image_file = image_file[:-3] + "png"
                cv2.imwrite(
                    os.path.join(draw_img_save_dir, os.path.basename(image_file)),
                    draw_img[:, :, ::-1])
                logger.debug("The visualized image saved in {}".format(
                    os.path.join(draw_img_save_dir, os.path.basename(image_file))))

        logger.info("The predict total time is {}".format(time.time() - _st))
        if args.benchmark:
            text_sys.text_detector.autolog.report()
            text_sys.text_recognizer.autolog.report()


if __name__ == "__main__":
    args = utility.parse_args()
    if args.use_mp:
        p_list = []
        total_process_num = args.total_process_num
        for process_id in range(total_process_num):
            cmd = [sys.executable, "-u"] + sys.argv + [
                "--process_id={}".format(process_id),
                "--use_mp={}".format(False)
            ]
            p = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stdout)
            p_list.append(p)
        for p in p_list:
            p.wait()
    else:
        main(args)
