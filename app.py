#!/usr/bin/python3


#standard python lib
import RPi.GPIO as GPIO
import os
import time
import subprocess
import sys  #use sys.exit()

#threading lib
from threading import Thread,Lock

#import iic lib
import smbus

# Graphics libraries
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# Adafruit library for I2C OLED screen
import Adafruit_SSD1306



#Global values
# sys_halt_reboot_flag:
# 0 meanings system normal running.
# 1 meanings system need execute reboot 
# 2 meanings system need execute halt or power off
sys_halt_reboot_flag = 0

oled_display = True
fan_enable   = True

reboot_show_flag = False
halt_show_flag   = False

#oled_need_update = True

cpu_percentage_str = ""
IP_str = ""
MemUsage_str = ""
Disk_str = ""
CPUTemp_str = ""


### calc cpu info start
class GetCpuLoad:
    def __init__(self, sleeptime = 1):
        self.cpustat = '/proc/stat'
        self.sep = ' ' 
        self.sleeptime = sleeptime

    def getcputime(self):
        cpu_infos = {} #collect here the information
        with open(self.cpustat,'r') as f_stat:
            lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line.startswith('cpu')]

            #compute for every cpu
            for cpu_line in lines:
                if '' in cpu_line: cpu_line.remove('')#remove empty elements
                cpu_line = [cpu_line[0]]+[float(i) for i in cpu_line[1:]]#type casting
                cpu_id,user,nice,system,idle,iowait,irq,softrig,steal,guest,guest_nice = cpu_line

                Idle=idle+iowait
                NonIdle=user+nice+system+irq+softrig+steal

                Total=Idle+NonIdle
                #update dictionionary
                cpu_infos.update({cpu_id:{'total':Total,'idle':Idle}})
            return cpu_infos

    def getcpuload(self):
        start = self.getcputime()
        #wait a second
        time.sleep(self.sleeptime)
        stop = self.getcputime()

        cpu_load = {}

        for cpu in start:
            Total = stop[cpu]['total']
            PrevTotal = start[cpu]['total']

            Idle = stop[cpu]['idle']
            PrevIdle = start[cpu]['idle']
            CPU_Percentage=int(((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)*100)
            cpu_load.update({cpu: CPU_Percentage})
            
        return cpu_load

###### end of calc cpu info ##########


#### GPIO triger init #################

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
shutdown_pin = 4

GPIO.setup(shutdown_pin, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)


########end of gpio shutdown pin init######################

def shutdown_check():
    global reboot_show_flag,halt_show_flag
    global oled_display,fan_enable
    
    while True:
        pulsetime = 1
        GPIO.wait_for_edge(shutdown_pin, GPIO.RISING)
        time.sleep(0.01)
        
        while GPIO.input(shutdown_pin) == GPIO.HIGH:
            time.sleep(0.01)
            pulsetime += 1
            
        if pulsetime >= 2 and pulsetime <= 3:
            #os.system("echo reboot111")
            reboot_show_flag = True
            
        elif pulsetime >= 4 and pulsetime <= 5:
            #os.system("echo halt2222")
            halt_show_flag = True
        
        elif pulsetime >= 7 and pulsetime <= 8:
            print("oled button act!")
            oled_display = not oled_display
        
        elif pulsetime >= 9 and pulsetime <= 10:
            print("fan button act!")
            fan_enable = not fan_enable
            
            
            
def oled_show():
    global oled_display,reboot_show_flag,halt_show_flag
    global cpu_percentage_str, IP_str, MemUsage_str, Disk_str, CPUTemp_str
    
    while True:    
  
        if oled_display :    
            draw.rectangle((0,0,width,height), outline=0, fill=0) 
            
            if halt_show_flag :
                draw.text((5, 20), "Shutdown",  font=big_font, fill=255)
            elif reboot_show_flag:
                draw.text((15, 20), "Reboot",  font=big_font, fill=255)
            
            else:
                if cpu_percentage_str != "":
                    draw.text((x, top), IP_str, font=default_font, fill=255)
                    draw.text((x, top+16), "CPU: "+ cpu_percentage_str + "%" +" " + CPUTemp_str , font=default_font, fill=255)
                    draw.text((x, top+32), MemUsage_str, font=default_font, fill=255)
                    draw.text((x, top+48), Disk_str, font=default_font, fill=255)

            disp.image(image)
            disp.display()
            time.sleep(0.1)
        else:
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            disp.image(image)
            disp.display()
            time.sleep(0.1)
        
        if halt_show_flag :
            os.system("echo halt2222")
        elif reboot_show_flag:
            os.system("echo reboot111")
            
        
def cpu_info_timer():
    global cpu_percentage_str, IP_str, MemUsage_str, Disk_str, CPUTemp_str
    
    while True:
        cpu_info = GetCpuLoad()
        data = cpu_info.getcpuload()
        cpu_percentage_str = str(data['cpu'])
        
        cmd = "hostname -I | cut -d\' \' -f1"
        IP = subprocess.check_output(cmd, shell = True )
        IP_str = str(IP,'utf-8')
                   
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB\", $3,$2 }'"
        MemUsage = subprocess.check_output(cmd, shell = True )
        MemUsage_str = str(MemUsage,'utf-8')
            
        cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
        Disk = subprocess.check_output(cmd, shell = True )
        Disk_str = str(Disk,'utf-8')
            
        cmd = "vcgencmd measure_temp |cut -f 2 -d '='"
        temp = subprocess.check_output(cmd, shell = True )
        CPUTemp_str = str(temp,'utf-8')    

##### main code ######

# 128x64 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_64(rst=None)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = 0
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load Truetype font from https://www.dafont.com/bitmap.php
# VCR OSD Mono by Riciery Leal
default_font = ImageFont.truetype('PixelOperatorMono-Bold.ttf', 16)
big_font = ImageFont.truetype('PixelOperatorMono-Bold.ttf', 30)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)
# Show Start Script text
draw.text((x, top), "Booting Finish...",  font=default_font, fill=255)
disp.image(image)
disp.display()
time.sleep(0.5)

## init iic ######
rev = GPIO.RPI_REVISION
if rev == 2 or rev == 3:
    bus = smbus.SMBus(1)
else:
    bus = smbus.SMBus(0)

try:
    bus.write_byte(0x15, 0xAA); ##tell mcu , pi boot has been finished!
except:
    print("iic write 0xAA is fail.")
    sys.exit()

lock = Lock()


try:
    t1 = Thread(target = shutdown_check)
    t2 = Thread(target = oled_show)
    t3 = Thread(target = cpu_info_timer)
    
    
    t1.start()
    t2.start()
    t3.start()
    
except:
    t1.stop()
    t2.stop()
    t3.stop()
    GPIO.cleanup()
