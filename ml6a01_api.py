import os
import cv2
import time
import pyodbc
from threading import Thread
from queue import Queue,Empty
from collections import Counter
from configparser import ConfigParser
PID = os.getpid()
CFG = "yolov4.cfg"
WEIGHTS = "yolov4.weights"
net = cv2.dnn_DetectionModel(CFG,WEIGHTS)
net.setInputSize(640,480)
net.setInputScale(1.0/255)
net.setInputSwapRB(True)

LAST_TEMP = 0.0 # 紀錄前次體溫讀數，以防辨識到前次的讀數
INFER_LIST = [] # 儲存辨識後讀數
PEOPLE_FLAG = False # 刷卡後Flag轉True開始儲存INFER_LIST
TEXT = "請刷卡量測" # 網頁預設文字

# DATABASE Information
dbconfig = ConfigParser()
dbconfig.read("config.ini")
SERVER = dbconfig["DATABASE"]["SERVER"]
DATABASE = dbconfig["DATABASE"]["DATABASE"] 
USERNAME = dbconfig["DATABASE"]["USERNAME"]
PASSWORD = dbconfig["DATABASE"]["PASSWORD"]

class ipcamCapture:
    def __init__(self, cap):
        self.Frame = []
        self.status = False
        self.isstop = False
        self.capture = cap
    def isOpened(self):return self.capture.isOpened()

    def start(self):
        Thread(target=self.queryframe, daemon=True, args=()).start()

    def stop(self):
        self.isstop = True
   
    def getrotframe(self):
        return cv2.rotate(self.Frame,cv2.ROTATE_90_CLOCKWISE)
        
    def queryframe(self):
        while (not self.isstop):
            self.status, self.Frame = self.capture.read()
        
        self.capture.release()

def image_detection(img,coordinate=False):
    classes,_,boxes = net.detect(img,confThreshold=0.1,nmsThreshold=0.4)
    if len(classes)==3 and coordinate:
        # sort the number read
        min = 9999
        max = 0
        box = []
        ans = 0.0
        for i in boxes:
            if i[0]<min:min=i[0]
            if i[0]>max:max=i[0]
            box.append(i[0])
        for i in range(3):
            if box[i]==min:ans+=classes[i]*10
            elif box[i]==max:ans+=classes[i]*0.1
            else:ans+=classes[i]
        return float(ans)
    elif not coordinate:
        print(classes)
    return 0



def inference():
    global INFER_LIST
    _time = time.time()
    while True:
        try:
            while ipcam.isOpened():
                while time.time()-_time<0.2:pass
                ans = image_detection(ipcam.getrotframe(),True)
                print(f"temp: {ans}")
                if PEOPLE_FLAG:
                    INFER_LIST.append(ans)
                _time = time.time()
        except:
            ipcam.stop()
            print("exit")
            os.system(f"TASKKILL /PID {PID} /F")
   
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
        print("exit")
        os.system(f"TASKKILL /PID {PID} /F")
        print("exit_Done")
     
from flask import Flask,render_template,request
app = Flask(__name__)


@app.route("/", methods=['GET','POST'])
def submit():
    global PEOPLE_FLAG
    global INFER_LIST
    global LAST_TEMP
    global TEXT

    if request.method=='POST':
        TEXT = "請重新量測"
        print('RECV POST')
        time_now = time.time()
        hid = str(request.values.get('hid'))
        INFER_LIST.clear()
        con = pyodbc.connect('DRIVER={SQL Server};SERVER='+SERVER+';DATABASE='+DATABASE+';UID='+USERNAME+';PWD='+ PASSWORD)
        cur = con.cursor()
        try:
            cur.execute(f"select WORKID,NAME FROM HR_COPY WHERE HIDCARD='{hid}'")
            work_ID,name = cur.fetchone()
        except:
            work_ID = ""
            name = hid
        PEOPLE_FLAG = True
        while time.time()-time_now<12 and PEOPLE_FLAG:
            while time.time()-time_now<1:INFER_LIST.clear()
            while time.time()-time_now<1.3:pass
            counter = Counter(INFER_LIST)
            print(counter)
            for temp,times in counter.items():
                if temp>42 or temp<33:continue
                if (times>1 and temp!=LAST_TEMP) or times>3:
                    TEXT = f"Hi  {name} 您的體溫是 {temp} °C" if temp<37.4 else "體溫過高，請重新量測"
                    PEOPLE_FLAG = False
                    LAST_TEMP=temp
                    cur.execute(f"INSERT INTO AUO_TEMP2 values ('{work_ID}','{name}','{temp}','{time.strftime('%Y-%m-%d %H:%M:%S')}','[額]')")
                    con.commit()
                    break
            time.sleep(0.2)
        cur.close()
        con.close()
    return render_template("index.html",text=TEXT)
    

if __name__ == '__main__':
    cap = get_video_capture("http://10.96.32.29:8081") # URL
    ipcam = ipcamCapture(cap)
    ipcam.start()
    time.sleep(1)
    Thread(target=inference, args=(),daemon=True).start()

    app.run(host='0.0.0.0',port=5001,debug=False)