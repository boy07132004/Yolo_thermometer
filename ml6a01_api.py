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
    global text
    while True:
        while cap is None:
            text = "Camera disconnect."
            cap = get_video_capture(input_path)
            time.sleep(10)
        while cap.isOpened():
            if text == "Camera disconnect.":text="請刷卡量測"
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
    try:
        res_queue = Queue()
        VideoCaptureDaemon(video, res_queue).start()
        return res_queue.get(block=True, timeout=timeout)
    except Empty:
        print('cv2.VideoCapture: could not grab input ({}). Timeout occurred after {:.2f}s'.format(video, timeout))
        return None
     
from flask import Flask,render_template,request
app = Flask(__name__)
last_temp = 0.0
text = "請刷卡量測"


@app.route("/", methods=['GET','POST'])
def submit():
    global flag
    global infer_list
    global last_temp
    global text
    try:
        text = "請刷卡量測" if cap.isOpened() else "Waiting for camera server."
    except:
        text = "Waiting for camera server."
    if request.method=='POST':
        if text != "Camera disconnect.":
            text = "請重新量測"
            print('RECV POST')
            hid = request.values.get('hid')
            time_now = time.time()
            flag = True
            while time.time()-time_now<12 and flag:
                while time.time()-time_now<1.5:infer_list.clear()
                while time.time()-time_now<4:pass
                counter = Counter(infer_list)
                print(counter)
                for temp,times in counter.items():
                    if temp>42 or temp<33:continue
                    if (times>2 and temp!=last_temp) or times>3:
                        text = f"Hi  {hid} 您的體溫是 {temp} °C" if temp<37.4 else "體溫過高，請重新量測"
                        flag = False
                        last_temp=temp
                        break
    return render_template("index.html",text=text)
    

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