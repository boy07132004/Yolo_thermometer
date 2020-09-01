from ctypes import *
import random
import os
import cv2.cv2 as cv2
import time
import darknet
import argparse
from threading import Thread, enumerate
from queue import Queue,Empty

def parser():
    parser = argparse.ArgumentParser(description="YOLO Object Detection")
    parser.add_argument("--input", type=str, default=0,
                        help="video source. If empty, uses webcam 0 stream")
    parser.add_argument("--out_filename", type=str, default="",
                        help="inference video name. Not saved if empty")
    parser.add_argument("--weights", default="yolov4.weights",
                        help="yolo weights path")
    parser.add_argument("--dont_show", action='store_true',
                        help="windown inference display. For headless systems")
    parser.add_argument("--ext_output", action='store_true',
                        help="display bbox coordinates of detected objects")
    parser.add_argument("--config_file", default="yolov4.cfg",
                        help="path to config file")
    parser.add_argument("--data_file", default="obj.data",
                        help="path to data file")
    parser.add_argument("--thresh", type=float, default=.25,
                        help="remove detections with confidence below this value")
    return parser.parse_args()


def check_arguments_errors(args):
    assert 0 < args.thresh < 1, "Threshold should be a float between zero and one (non-inclusive)"
    if not os.path.exists(args.config_file):
        raise(ValueError("Invalid config path {}".format(os.path.abspath(args.config_file))))
    if not os.path.exists(args.weights):
        raise(ValueError("Invalid weight path {}".format(os.path.abspath(args.weights))))
    if not os.path.exists(args.data_file):
        raise(ValueError("Invalid data file path {}".format(os.path.abspath(args.data_file))))


def video_capture(frame_queue, darknet_image_queue):
    while cap.isOpened():
        for _ in range(10):ret, frame = cap.read()
        frame = cv2.rotate(frame,cv2.ROTATE_90_CLOCKWISE)
        if not ret:break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (width, height),
                                   interpolation=cv2.INTER_LINEAR)
        frame_queue.put(frame_resized)
        darknet.copy_image_from_bytes(darknet_image, frame_resized.tobytes())
        darknet_image_queue.put(darknet_image)
    cap.release()
ans = 0
def inference(darknet_image_queue, detections_queue, fps_queue):
    global ans
    while cap.isOpened():
        darknet_image = darknet_image_queue.get()
        prev_time = time.time()
        detections = darknet.detect_image(network, class_names, darknet_image, thresh=args.thresh)
        detections_queue.put(detections)
        fps = int(1/(time.time() - prev_time))
        fps_queue.put(fps)
        print("FPS: {}".format(fps))
        ans = (darknet.print_detections(detections, True))
    cap.release()


def drawing(frame_queue, detections_queue, fps_queue):
    while cap.isOpened():
        frame_resized = frame_queue.get()
        detections = detections_queue.get()
        fps = fps_queue.get()
        if 0:print(frame_resized,detections,fps)
    cap.release()

class VideoCaptureDaemon(Thread):
    def __init__(self, video, result_queue):
        super().__init__()
        self.daemon = True
        self.video = video
        self.result_queue = result_queue
    def run(self):
        self.result_queue.put(cv2.VideoCapture(self.video))
def get_video_capture(video, timeout=10):
    res_queue = Queue()
    VideoCaptureDaemon(video, res_queue).start()
    try:
        return res_queue.get(block=True, timeout=timeout)
    except Empty:
        print('cv2.VideoCapture: could not grab input ({}). Timeout occurred after {:.2f}s'.format(video, timeout))
        
from flask import Flask
app = Flask(__name__)
@app.route('/')
def home():
    return str(ans)

if __name__ == '__main__':
    frame_queue = Queue()
    darknet_image_queue = Queue(maxsize=1)
    detections_queue = Queue(maxsize=1)
    fps_queue = Queue(maxsize=1)
    args = parser()
    check_arguments_errors(args)
    network, class_names, class_colors = darknet.load_network(
            args.config_file,
            args.data_file,
            args.weights,
            batch_size=1
        )
    # Darknet doesn't accept numpy images.
    # Create one with image we reuse for each detect
    width = darknet.network_width(network)
    height = darknet.network_height(network)
    darknet_image = darknet.make_image(width, height, 3)
    input_path = "http://10.96.32.29:8081"
    cap = get_video_capture(input_path)
    while cap is None:
        cap = get_video_capture(input_path)
        print("Wait cam")
        
    Thread(target=video_capture, args=(frame_queue, darknet_image_queue),daemon=True).start()
    Thread(target=inference, args=(darknet_image_queue, detections_queue, fps_queue),daemon=True).start()
    Thread(target=drawing, args=(frame_queue, detections_queue, fps_queue),daemon=True).start()
    #web.run_app(app)
    app.run(host='0.0.0.0')