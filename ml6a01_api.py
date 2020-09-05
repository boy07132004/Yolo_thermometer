from ctypes import *
import random
import os
import cv2.cv2 as cv2
import time
import darknet
import argparse
from threading import Thread, enumerate
from queue import Queue,Empty
from collections import Counter

def parser():
    parser = argparse.ArgumentParser(description="YOLO Object Detection")
    parser.add_argument("--weights", default="yolov4.weights",
                        help="yolo weights path")

    parser.add_argument("--input", type=str, default="http://192.168.0.200:8081",
                        help="URL")

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


def video_capture(darknet_image_queue):
    global cap
    while True:
        while cap is None:
            cap = get_video_capture(input_path)
            time.sleep(10)
        while cap.isOpened():
            for _ in range(10):ret, frame = cap.read()
            frame = cv2.rotate(frame,cv2.ROTATE_90_CLOCKWISE)
            if not ret:break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (width, height),
                                       interpolation=cv2.INTER_LINEAR)
            darknet.copy_image_from_bytes(darknet_image, frame_resized.tobytes())
            darknet_image_queue.put(darknet_image)
        try:cap.release()
        except:pass
        cap = get_video_capture(input_path)
infer_list = []
flag = False
def inference(darknet_image_queue):
    global infer_list
    while True:
        while cap is None:ans=-99
        while cap.isOpened():
            darknet_image = darknet_image_queue.get()
            prev_time = time.time()
            detections = darknet.detect_image(network, class_names, darknet_image, thresh=args.thresh)
            fps = int(1/(time.time() - prev_time))
            ans = (darknet.print_detections(detections, True))
            print(f"FPS: {fps} temp: {ans}")
            if flag:infer_list.append(ans)
            
        try:cap.release()
        except:time.sleep(10)


# Set IPCAM connection timeout
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
        return None
     
from flask import Flask,render_template,request
app = Flask(__name__)

info = {"name":None,"temp":0.0}
@app.route("/", methods=['GET','POST'])
def submit():
    global info
    global flag
    global infer_list
    if request.method=='POST':
        print('RECV POST')
        hid = request.values.get('hid')
        time_now = time.time()
        infer_list = []
        flag = True
        while time.time()-time_now<10 and flag:
            while time.time()-time_now<2:pass
            while time.time()-time_now<5:pass
            counter = Counter(infer_list)
            print(counter)
            for temp,times in counter.items():
                if temp>42 or temp<33:continue
                if (times>4 and temp!=info['temp']) or times>5:
                    info = {"name":hid,"temp":temp}
                    flag = False
                    break
        print(info)
    return render_template("index.html",name=info["name"],temp=info['temp'])
    

if __name__ == '__main__':
    frame_queue = Queue()
    darknet_image_queue = Queue(maxsize=1)
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
    input_path = args.input
    cap = get_video_capture(input_path)
    while cap is None:
        cap = get_video_capture(input_path)
        print("Wait cam")
        
    Thread(target=video_capture, args=(darknet_image_queue,),daemon=True).start()
    Thread(target=inference, args=(darknet_image_queue,),daemon=True).start()
    app.run(host='0.0.0.0',debug=False)