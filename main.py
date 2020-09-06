import subprocess
import time
pid = 0
proc = None
def run():
    global pid
    global proc
    proc = subprocess.Popen("python ml6a01_api.py",)
    pid = proc.pid
run()
while 1:
    ps = subprocess.run(f"powershell Get-Process -id {pid}",shell=True,capture_output=True)
    print(ps.stdout.split()[17])
    if int(ps.stdout.split()[17])>1000:
        proc.kill()
        run()
    time.sleep(5)