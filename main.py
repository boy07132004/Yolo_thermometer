import subprocess
import time

pid = None
proc = None

def run():
    global pid
    global proc
    count = 1
    try:
        while True:
            # Check camera is online now.
            try:
                cam_server = "192.168.0.200"
                # Ping 1 time in Windows OS.
                check = subprocess.check_output(f"ping -n 1 {cam_server}") 
                break
            except:
                if count%10==0:
                    print(time.ctime(),"Can't reach camera server")
                    count=1
                else:
                    count+=1
                time.sleep(6)
        proc = subprocess.Popen(r"python D:\Thermometer\ML6A01\ml6a01_api.py")
        pid = proc.pid
        print(pid)
    except:
        print(time.ctime(),"Can't reach camera server")
        time.sleep(6)
        run()
        
#run()
count=0

while 1:
    try:
        # Process kill and restart when python crash.
        ps = subprocess.check_output(f"powershell Get-Process -id {pid}",shell=True)
        if count%100==0:print(time.ctime(),ps.split()[17])
        if int(ps.split()[17])>1000:
            proc.kill()
            run()
        time.sleep(6)
        count+=1
    except:
        run()
