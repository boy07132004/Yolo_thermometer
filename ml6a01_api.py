import os
import cv2
import time
import pyodbc
from threading import Thread
from queue import Queue,Empty
from collections import Counter
PID = os.getpid()
CFG = "yolov4.cfg"
WEIGHTS = "yolov4.weights"
net = cv2.dnn_DetectionModel(CFG,WEIGHTS)
net.setInputSize(640,480)
net.setInputScale(1.0/255)
net.setInputSwapRB(True)

class ipcamCapture:
    def __init__(self, cap):
        self.Frame = []
        self.status = False
        self.isstop = False

        self.capture = cap
    def isOpened(self):
        return self.capture.isOpened()
        
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

infer_list = []
flag = False
def inference():
    global infer_list
    TIME = time.time()
    while True:
        try:
            while ipcam.isOpened():
                while time.time()-TIME<0.3:pass
                imgg = ipcam.getrotframe()
                ans = image_detection(imgg,1)
                print(f"temp: {ans}")
                if flag:infer_list.append(ans)
                TIME = time.time()
        except:
            ipcam.stop()
            print("exit")
            os.system(f"TASKKILL /PID {PID} /F")
   

     
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

    if request.method=='POST':
        text = "請重新量測"
        print('RECV POST')
        time_now = time.time()
        hid = str(request.values.get('hid'))
        infer_list.clear()
        try:
            cur.execute(f"select WORKID,NAME FROM HR_COPY WHERE HIDCARD='{hid}'")
            work_ID,name = cur.fetchall()[0]
        except:
            work_ID = ""
            name = hid
        flag = True
        while time.time()-time_now<12 and flag:
            while time.time()-time_now<1:infer_list.clear()
            while time.time()-time_now<1.5:pass
            counter = Counter(infer_list)
            print(counter)
            for temp,times in counter.items():
                if temp>42 or temp<33:continue
                if (times>2 and temp!=last_temp) or times>4:
                    text = f"Hi  {name} 您的體溫是 {temp} °C" if temp<37.4 else "體溫過高，請重新量測"
                    flag = False
                    last_temp=temp
                    cur2.execute(f"INSERT INTO AUO_TEMP2 values ('{work_ID}','{name}','{temp}','{time.strftime('%Y-%m-%d %H:%M:%S')}','[額]')")
                    con2.commit()
                    break
    return render_template("index.html",text=text)
    

if __name__ == '__main__':
    cap = get_video_capture("http://10.96.32.29:8081") # URL
    ipcam = ipcamCapture(cap)
    ipcam.start()
    time.sleep(1)
    Thread(target=inference, args=(),daemon=True).start()
    
    # DATABASE Information
    server = '' 
    database = '' 
    username = ''
    password = '' 
    
    con2 = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
    cur = con2.cursor()
    cur2 = con2.cursor()
    app.run(host='0.0.0.0',port=5001,debug=False)
    cur.close()
    cur2.close()