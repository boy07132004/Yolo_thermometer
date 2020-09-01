import csv
import time
import tkinter as tk
import requests
from collections import Counter
url = "http://192.168.3.107:5000"
class App:
    def show_id_temper(self):
        self.ls.append(float(requests.get(url).text))
        if self.times >0 and len(self.ls)>5:
            counter = Counter(self.ls)
            for key,value in counter.items():
                if key<33 or key>42:continue
                if (value>3 and value!=self.last_time) or value>8:
                    if key>37.4: self.Status['text'] = f"體溫過高!!\n{self.ID_now} -- {key}℃\n重新量測"
                    else: self.Status['text'] = f'Welcome!!\n{self.ID_now} -- {key}℃\n下一位請刷卡'
                    with open('output.csv','a',newline='\n') as csv_file:
                            csv.writer(csv_file).writerow([self.ID_now,key])
                    self.ID['state']='normal'
                    self.ID.delete(0,'end')
                    return
            self.times-=1
            self.master.after(100,self.show_id_temper)    
        elif self.times>0:
            self.times-=1
            self.master.after(100,self.show_id_temper)
        else:
            self.Status['text'] = '請重新刷卡量測'
            self.ID['state']='normal'
            self.ID.delete(0,'end')    

    def detect(self,event=None):
        self.ls = []
        self.times = 100
        self.ID_now = self.ID.get()
        self.master.after(1000,self.show_id_temper)
        self.Status['text'] = '量測中請稍候'
        self.ID['state'] = 'disabled'
        

    def __init__(self,master):
        self.last_time = 0
        self.master = master
        self.master.geometry("1800x900")
        self.Frame = tk.Frame(self.master)
        self.Label = tk.Label(self.Frame,text='Made in ML6A01',font = ("Calibri",12))
        #self.Label.pack()
        self.ID = tk.Entry(self.Frame,font="Calibri 60",justify="center")
        self.ID.bind('<Return>',self.detect)
        self.ID.pack()
        self.Status = tk.Label(
            self.Frame,
            text = 'Welcome!!\n請刷卡',
            font = ("Calibri",100))
        self.Status.pack()
        self.Frame.pack()

def main():
    root = tk.Tk()
    app  = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    
    
            
