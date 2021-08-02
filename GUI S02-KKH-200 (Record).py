import sys
import os
import datetime
import time
import serial
import serial.tools.list_ports as ports
import csv
import pandas as pd
import math
from pathlib import Path
from PyQt5.QtWidgets import * 
from PyQt5 import QtCore, QtGui 
from PyQt5.QtGui import * 
from PyQt5.QtCore import *
from skimage.transform import (hough_line, hough_line_peaks)
import PySpin
from pandas import DataFrame
import cv2
import numpy as np
from matplotlib import pyplot as plt

##################################################
## {Description}
##################################################
## {License_info}
##################################################

__author__ = "Kerwin Kwek Zeming"
__copyright__ = "SMART-CAMP"
__credits__ = "Kerwin Kwek Zeming, Goh Chin Ren and Quek Kai Yun"
__license__ = "S01-KKH-105"
__version__ = "1.05.00"
__maintainer__ = "Kerwin Kwek Zeming"
__email__ = "kerwin@smart.mit.edu"
__status__ = "Development"


### ************************************ ###
###              Functions               ###
### ************************************ ###
### FUNCTION ===> Startup Run 
def start_event():
    global arduino
    l = load_settings()
    arduino = check_connection(1)
    print('The arduino connection value is',arduino)
    for wait in range(1): ## 3 seconds wait
        print(wait+1, "/ 3 second...starting up")
        time.sleep(1)
    clear_signal()
    return l, arduino
    
### FUNCTION ===> Shutdown Run
def close_event():
    global cam, got_camera
    print('Application End Closing Sequence...')
    ## Disconnect camera
    got_camera = False
    ## Save last settings
    save_settings()
    ## Power down and Home
    try: arduino_system.close(); print('Serial connection disconnected')
    except: print('Serial connection unavailable') 

    ## home
    if arduino == 0: print('Arduino is nt connected')
    else: home_xy()
        
    ## Finally...
    print('The application has shutdown')
    sys.exit(0)
    return

### FUNCTION ===> Check connection to USB system
def check_connection(timeout, com_port = 'COM3'):
    length_timeout = 0
    while (length_timeout < timeout):
        myports = [tuple(p) for p in list(ports.comports())]
        arduino_port = [port for port in myports if com_port in port]
        if arduino_port:
            print("System is connected via USB!")
            try:
                arduino = serial.Serial(com_port, 115200, timeout=.1)
                print("Serial Communication is Online")
                return arduino
            except:
                print("Unable to proceed with Serial communication")
                return -1
        else:
            length_timeout += 1
            time.sleep(0.5)
            print('connecting...')
    print("System is NOT connected")
    return 0

### FUNCTION ===> send signal to arduino
def send_signal(char,start_char='<',end_char='>'):
    global arduino
    char_to_send = start_char+char+end_char
    if char == 's': char_to_send = char
    arduino.write(char_to_send.encode("utf-8"))
    print("Sent ->", char)
    time.sleep(0.1)
    return char

### FUNCTION ===> read signal to arduino
def read_signal():
    global arduino
    data =''
    data = arduino.readline()[:-2] ##readline() takes max 0.1 seconds to complete
    if data:
        print("Received ->", data.decode('UTF-8'))
        return data.decode('UTF-8')
##    print("Did Not Receive Data --- 0 ---")
    return False                    ##time out signal = 0

### FUNCTION ===> Clear Buffer
def clear_signal():
    global arduino
    if arduino == 0:
        return 0
    data = arduino.read(arduino.inWaiting()).decode('UTF-8')
    if data != '':
        print ("cleared data ==>",data)
    return data

### FUNCTION ===> run send and read signals    
def run_signal(signal):
    clear_signal()
    sent = send_signal(signal)
    read = read_signal()
    if sent == read:
        print("-------------signal = " + signal)
        return sent, read
    elif read == "Unknown command":
        print("no signal")
        return 0
    
### FUNCTION ===> Get Date Time
def date_time():
    now = datetime.datetime.now()
    now_str = now.strftime("%y %m %b %d %H %M")
    year, month, month_b , day, hour, minute = now_str.split(' ')
    return year, month, month_b , day, hour, minute

def clicked():
    print('aahahahah')

### FUNCTION ===> Reset Camera Settings
def reset_parameters():
    global FPS, exposure_time, num_frames, gain, width, height
    FPS = 25
    exposure_time = 100
    num_frames = 1000
    gain = 0
    width = 1440
    height = 1080
    return

### FUNCTION ===> Global CANCEL
def cancel():
    global no_cancel
    if no_cancel == True:
        print('FPS view = ',cam.AcquisitionFrameRate.GetValue())
        no_cancel = False
        camera_reset()
        try:
            if tab.currentIndex() == 1: a_view_label.setText("Camera Off")
        except:
            cprint("unable to change label text")
        cprint("Camera Off")
    else: return

### FUNCTION ===> Print in Console and Log events
def cprint(string):
    # dd/mm/YY H:M:S
    global console_num, console_log
    now = datetime.datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    log_input = (now, string)
    console_num += 1
    console_value = (str(console_num) + ' | ' + dt_string + ' |   ' + str(string))
    console_list.insertItem(0,console_value)
    console_log.append(log_input)
    return
    
### FUNCTION ===> RESET Camera
def camera_reset():
    cam.OffsetY.SetValue(0)
    cam.OffsetX.SetValue(0)
    return

### FUNCTION ===> CAMERA START
def camera_start():
    global got_camera, cam, cam_list

    if got_camera == True: return

    ## --- Setup Camera --- ##
    # [GET] system
    system = PySpin.System.GetInstance()

    try:
        # [GET] camera list
        cam_list = system.GetCameras()
        cam = cam_list.GetByIndex(0)
    except:
        got_camera = False
        print('Camera not connected')
        return

    # [Initialize] camera
    cam.Init()
    cam.BeginAcquisition()
    cam.EndAcquisition()
    num_cameras = cam_list.GetSize()
    
    # [LOAD] default configuration
    cam.UserSetSelector.SetValue(PySpin.UserSetSelector_Default)
    cam.UserSetLoad()
    got_camera = True
    print('[INFO] Number of cameras detected: %d' % num_cameras)
    return

### FUNCTION ===> SET camera Properties
def camera_properties(c_width, c_height, c_fps):
    global exposure_time, width, height, gain, cam
    
    width = c_width
    height = c_height

    # [SET] Image dimenstion width and height and center ROI
    max_width = cam.Width.GetMax()
    max_height = cam.Height.GetMax()
    if width <= max_width and width >= 100:
        if width%4 != 0:
            print(width, 'not divisible by 4')
            width=width-width%4
    elif width < 100 and width > 0:
        width = 100
    else: width = max_width

    if height <= max_height and height >= 100:
        if height%2 != 0:
            print(height, 'not divisible by 2')
            height=height+1
    elif height < 100 and height > 0:
        height = 100
    else: height = max_height
    
    cam.Width.SetValue(width)
    cam.Height.SetValue(height)
    cam.OffsetY.SetValue(round((max_height-height)/2)-round((max_height-height)/2)%2)
    cam.OffsetX.SetValue(round((max_width-width)/2)-round((max_width-width)/2)%4)
    print('[INFO] Frame Width =',width,'| Height =',height)

    # [SET] analog. Set Gain. Turn off Gamma.
    cam.GainAuto.SetValue(PySpin.GainAuto_Off)
    cam.Gain.SetValue(int(gain))
    cam.GammaEnable.SetValue(False)
    print('Cam Properties gain End')

    # [SET] acquisition. Continues acquisition. Auto exposure off. Set frame rate. 
    cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
    cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
    exposure_time = min(cam.ExposureTime.GetMax(), int(exposure_time))
    cam.ExposureMode.SetValue(PySpin.ExposureMode_Timed)
    cam.ExposureTime.SetValue(int(exposure_time))
    print('Cam Properties exposure time End')

    # [SET] Framerates
    cam.AcquisitionFrameRateEnable.SetValue(True)
    max_FPS = cam.AcquisitionFrameRate.GetMax()
    try:        ## if c_fps is not defined
        int(c_fps)
    except:
        c_fps = 25
    if int(c_fps) > (round(max_FPS)-1):
        c_fps = (round(max_FPS)-1)
    elif int(c_fps) >= 10 and int(c_fps)<= (round(max_FPS)-1):
        pass
    else: c_fps = 25
    cam.AcquisitionFrameRate.SetValue(int(c_fps))
    print('FPS =',int(c_fps))
    print('Cam Properties End')

    return
    
### FUNCTION ===> CAMERA_VIEW
def camera_view():
    global no_cancel, got_camera, num_cameras, cam
    global width, height, angle
    global rot_x, rot_y, rot_width, rot_height

    tab_index = tab.currentIndex()
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    camera_start()

    if got_camera == True and num_cameras == 0:
        print('trouble')
        got_camera = False
        return

    if got_camera == False:
        cprint('No Detectable Camera')
        return

    if no_cancel == True:
        cprint("Camera is already on")
        return
    
    no_cancel = True
    
    
    if angle == 0:
            x2 = width
            y2 = height

    ## get angle properties
    if angle !=0:
        print(angle)
        rad = math.radians(abs(angle))
        cos = math.cos(rad)
        sin = math.sin(rad)
        y1 = height
        x1 = width
        image_center = (x1 / 2, y1 / 2)
        y2 = (y1 * cos) + (x1 * sin)
        x2 = (x1 * cos) + (y1 * sin)
        rot_x = int(abs(x2-x1))
        rot_y = int(abs(x1*sin))
        rot_width = int(x1 - abs(x2-x1))
        rot_height = int((y1 * cos) - (x1 * sin))
        M = cv2.getRotationMatrix2D((image_center),angle,1)
        M[0, 2] += ((x2 / 2) - image_center[0])
        M[1, 2] += ((y2 / 2) - image_center[1])
    
    qformat = QImage.Format_Indexed8
    
    print('Initial FPS view = ',cam.AcquisitionFrameRate.GetValue())
    camera_properties(width, height, 25)
    cam.BeginAcquisition()

    while no_cancel:
        image_primary = cam.GetNextImage()
        frame = np.array(image_primary.GetNDArray())
        
        if angle !=0:
            frame = cv2.warpAffine(frame,M,(int(x2),int(y2)))
            ##frame_crop = frame[rot_y:(rot_y+rot_height) , rot_x:(rot_x+rot_width)]
        
        img = QImage(frame, int(x2), int(y2), int(x2), qformat)
        img = img.copy(rot_x, rot_y, rot_width, rot_height)    # copy(int x, int y, int width, int height)
        img = QPixmap.fromImage(img)
        img = img.scaledToHeight(800)
        if tab_index == 0: label_view1.setPixmap(img)
        else: a_view_label.setPixmap(img)
        cv2.waitKey(1)
    print(tab_index)
    cam.EndAcquisition()
    print('FPS view = ',cam.AcquisitionFrameRate.GetValue())
    camera_reset()
    no_cancel = False
    
    return

### FUNCTION ===> CAMERA_VIEW
def find_ROI():
    global no_cancel, got_camera, num_cameras, cam
    global width, height, angle, cwDir
    global rot_x, rot_y, rot_width, rot_height

    cwDir = os.getcwd()
    ## Set Directory Paths
    directory = cwDir + '\\Images' + '\\template\\'
    dir_files = os.listdir(directory)
    ##os.chdir(os.path.dirname(os.getcwd()))                #Change directory parent
##    templates = [file for file in dir_files if file.endswith(".tif")]
    templates = [directory + '6 dots.tif',directory + '4 dots.tif', directory + 'start dots.tif']

    ### Variables to set ###
    ########################
##    templates = [file for file in dir_files if file.endswith(".tif")]
    templates_loc = (250, 540, 1250)   ## dependent on camera
    video_loc = [0,0,0]
    loc_fail = [0,0,0]
    templates_ch = [30,20,0]
    max_ch = 35
    ave_ch = 30

    marker_file = cwDir + '\\template\\' + '4 dots.tif'
    ## histogram normalized
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        
##    template = cv2.imread(marker_file, cv2.IMREAD_GRAYSCALE)
####    template = clahe.apply(template)
##    w, h = template.shape[::-1]
##    template = cv2.Canny(template, 100, 100)
##    show(template)

    print('before')
    no_cancel = True
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    camera_start()
    print('before2')
    if got_camera == True and num_cameras == 0:
        print('trouble')
        got_camera = False
        return
    
    if got_camera == False:
        cprint('No Detectable Camera')

    if angle == 0:
        x2 = width
        y2 = height
            
    print('Initial FPS view = ',cam.AcquisitionFrameRate.GetValue())
    camera_properties(width, height, 25)
    cam.BeginAcquisition()

    
    ## get angle properties
    if angle !=0:
        print(angle)
        rad = math.radians(abs(angle))
        cos = math.cos(rad)
        sin = math.sin(rad)
        y1 = height
        x1 = width
        image_center = (x1 / 2, y1 / 2)
        y2 = (y1 * cos) + (x1 * sin)
        x2 = (x1 * cos) + (y1 * sin)
        rot_x = int(abs(x2-x1))
        rot_y = int(abs(x1*sin))
        rot_width = int(x1 - abs(x2-x1))
        rot_height = int((y1 * cos) - (x1 * sin))
        M = cv2.getRotationMatrix2D((image_center),angle,1)
        M[0, 2] += ((x2 / 2) - image_center[0])
        M[1, 2] += ((y2 / 2) - image_center[1])


    qformat = QImage.Format_Indexed8
    image_primary = cam.GetNextImage()
    frame = np.array(image_primary.GetNDArray())
    
    if angle !=0:
        frame = cv2.warpAffine(frame,M,(int(x2),int(y2)))
        frame = frame[rot_y:(rot_y+rot_height) , rot_x:(rot_x+rot_width)]
        ##frame_crop = frame[rot_y:(rot_y+rot_height) , rot_x:(rot_x+rot_width)]

    print('before4')
    img2 = frame.copy()
    show(img2)
    print('before')

    # cycle true all the 6 templates
    for i, temp in enumerate(templates):
        average_loc = []
        print(templates[i])
        template = cv2.imread(templates[i], cv2.IMREAD_GRAYSCALE)
        w, h = template.shape[::-1]
        template = cv2.Canny(template, 100, 100)
        show(template)
        img = img2.copy()

        # All the 6 methods for comparison in a list
        methods = ['cv2.TM_CCOEFF', 'cv2.TM_CCOEFF_NORMED', 'cv2.TM_CCORR',
                    'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']

        for j,meth in enumerate(methods):
            test_img = img.copy()
            test_img = cv2.Canny(test_img, 100, 100)
            method = eval(meth)
            res = cv2.matchTemplate(img,template,method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                top_left = min_loc
            else:
                top_left = max_loc
            average_loc.append(top_left)
            print(average_loc)
        ## calculate the number of repeats
        loc = {k:average_loc.count(k) for k in average_loc}
        ## find the highest repeat coord
        max_coord = max(loc, key=loc.get)
        print(max_coord)
        if abs(max_coord[0] - (templates_loc[i]))<70:
            print(abs(max_coord[0] - (templates_loc[i])))
            video_loc[i]=[i,max_coord[0]+w/2,max_coord[1]]
        else:
            for j, loc in enumerate(average_loc):
                if abs(loc[0]-templates_loc[i])<40 :
                    loc_fail[i]=[i,loc]
        print(video_loc)
        print(loc_fail)

    ROI_loc = [a for a in video_loc if a != 0]
    print(ROI_loc)
    if video_loc.count(0) != 6:
        if len(ROI_loc) == 1:
            ch_w = ave_ch
            print('Auto ROI use single point reference')
        ROI_w = int(ch_w * max_ch)
        ROI_h = int(ROI_w*110/840)
        ROI_x = int(ROI_loc[0][1]) - int(ch_w * (templates_ch[ROI_loc[0][0]]+3))
        ROI_y = ROI_loc[0][2] - 20
        ROI_img = img2[ROI_y:ROI_y+ROI_h, ROI_x:ROI_x+ROI_w]

        show(ROI_img)
    elif video_loc.count(0) == 0: return
            
    cam.EndAcquisition()
    print('FPS view = ',cam.AcquisitionFrameRate.GetValue())
    camera_reset()
    no_cancel = False
    
    return

### FUNCTION ===> Start Dialog
def showdialog():
    global q_field5, q_field4, q_field3, q_field2
    global present, cwDir, user
    d = QDialog()
    
    year, month, month_b , day, hour, minute = date_time()
    present = day + ' ' + month_b + ' ' + year + ' ' + '('+ hour + ':' + minute + ')'
    
    b1 = QPushButton("Save")
    b2 = QPushButton("Cancel")
    b3 = QPushButton("Select Folder"); b3.setFixedSize(150,25)
    
    q_label1 = Label('Date: '); 
    q_label2 = Label('Sample ID: KKH-');
    q_label3 = Label('Chip No.:')
    q_label4 = Label('User:')
    q_field1 = LineEdit(present)
    q_field2 = LineEdit('')
    q_field3 = LineEdit('')
    q_field4 = LineEdit(user)
    q_field5 = LineEdit(cwDir)
    
    ##Layouts
    d_layout =  QGridLayout()
    d_layout.addWidget(q_label1,0,2,1,1)
    d_layout.addWidget(q_field1,0,3,1,1)
    d_layout.addWidget(q_label2,1,2,1,1)
    d_layout.addWidget(q_field2,1,3,1,1)
    d_layout.addWidget(q_label3,2,2,1,1)
    d_layout.addWidget(q_field3,2,3,1,1)
    d_layout.addWidget(q_label4,3,2,1,1)
    d_layout.addWidget(q_field4,3,3,1,1)
    d_layout.addWidget(q_field5,4,3,1,1)
    d_layout.addWidget(b3,4,2)

    d_save =  QGridLayout()
    d_save.addWidget(b1,0,1)
    d_save.addWidget(b2,1,1)
    
    d_box = QGroupBox('Experiment Settings')
    d_box2 = QGroupBox('Save')
    d_box.setLayout(d_layout)
    d_box2.setLayout(d_save)
    
    dialog_box =  QGridLayout()
    dialog_box.addWidget(d_box,0,1)
    dialog_box.addWidget(d_box2,0,2)

    d.setLayout(dialog_box)
    d.setWindowTitle("Experiment Logging")
    d.setWindowModality(Qt.ApplicationModal)
    b1.clicked.connect(d.accept)
    b2.clicked.connect(d.done)
    b3.clicked.connect(select_folder)
    showMsg() ## to test the popup
    if d.exec() == d.Accepted:
        print('Save initiated')
        begin_b.setParent(None) ## to remove button from layout
        basicLayout.addWidget(basic_w_run) ## Initiate the basic run function
        save_settings()
##        basic_w.setLayout(basicLayout_run)
##        layout.setCurrentIndex(1)
        return q_field2.text(), q_field3.text(), q_field4.text()
    else: print('Cancelled Save')
    return 

### FUNCTION ===> Show Msg to confirm the entries
def showMsg():
    msgBox = QMessageBox()
    msgBox.setIcon(QMessageBox.Information)
    msgBox.setText("Message box pop up window")
    msgBox.setWindowTitle("QMessageBox Example")
    msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
##    msgBox.buttonClicked.connect(msgButtonClick) ## add function here
    returnValue = msgBox.exec()
    if returnValue == QMessageBox.Ok:
        print('OK clicked')
    if returnValue == QMessageBox.Cancel:
        print('Cancel clicked')
    
      
### FUNCTION ===> Select Data Save Folder
def select_folder():
    global cwDir
    try:
        cwDir = QFileDialog.getExistingDirectory(None,'Open working directory', os.getcwd(), QFileDialog.ShowDirsOnly)
    except:
        print('Error loading Folder')
##    cam_field1.setText(cwDir)
    q_field5.setText(cwDir)
    return

### FUNCTION ===> Run Experiment Steps
def run_expt():
    global run_step, current_step, step_instructions, count, no_cancel, count2
    current_step = current_step + 1
    for x in run_step:
        if current_step == x:
            print(current_step)
            bar.setValue(current_step)
            bar.setFormat(str(bar.value())+'/'+'10'+' Complete')
            label3.setText(step_instructions[x-1])

            ### ==== This is where we run all the steps ==== ###
            ### ============================================ ###
            ### =======>> STEP1
            if current_step == 1:
                label3.setText(step_instructions[x-1])
                label_view1.setPixmap(QPixmap("Images/step1.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            ### =======>> STEP2
            if current_step == 2:
                label_view1.setPixmap(QPixmap("Images/step2.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                count = 600
                timer.start(1000)       ## refreshed 1000ms
                timer.timeout.connect(countdown)
            ### =======>> STEP3
            if current_step == 3:
                timer.disconnect()
                label_view1.setPixmap(QPixmap("Images/step3.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                count2 = 200
                timer2.start(1000)       ## refreshed 1000ms
                timer2.timeout.connect(countdown2)
            ### =======>> STEP4
            if current_step == 4:
                timer2.disconnect()
                label_view1.setPixmap(QPixmap("Images/step4.jpg").scaled(1850, b_dim.height(),
                                                                         Qt.KeepAspectRatio, Qt.FastTransformation))
                
            ### =======>> STEP5
            if current_step == 5:
                label_view1.setPixmap(QPixmap("Images/step5.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                
            ### =======>> STEP6
            if current_step == 6:
##                label_view1.setPixmap(QPixmap("Images/step6.jpg").scaled(1850, b_dim.height()*3/4,
##                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                button_w.show()
                camera_view()
                
            ### =======>> STEP7
            if current_step == 7:
                button_w.hide()
                cancel()
##                camera_reset()
                no_cancel = False
                
                label_view1.setPixmap(QPixmap("Images/step7.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            ### =======>> STEP8
            if current_step == 8:
##                find_ROI()
                label_view1.setPixmap(QPixmap("Images/step8.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            ### =======>> STEP9
            if current_step == 9:
                label_view1.setPixmap(QPixmap("Images/step9.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            ### =======>> STEP10
            if current_step == 10:
                label_view1.setPixmap(QPixmap("Images/step10.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            if current_step > 10 or current_step < 1 :
##                label_view2.hide()
                button_w.hide()
                label_view1.setPixmap(QPixmap("Images/background.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
    if current_step > 10:
        showdialog()
        current_step = 0
        bar.setValue(current_step)
        bar.setFormat(str(bar.value())+'/'+'10'+' Complete')
        label3.setText('Protocol Overview')
        label_view1.setPixmap(QPixmap("Images/step8.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
        return
    
    return

### FUNCTION ===> Back Track Experiment Steps
def back_expt():
    global run_step, current_step, step_instructions, count, count2
    if current_step == 0:
        bar.setValue(current_step)
        bar.setFormat(str(bar.value())+'/'+'10'+' Complete')
        label3.setText('Protocol Overview')
        label_view1.setPixmap(QPixmap("Images/step8.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
        
        return
    current_step = current_step - 1
    for x in run_step:
        if current_step == x and current_step != 1:
            print(current_step)
            bar.setValue(current_step)
            bar.setFormat(str(bar.value())+'/'+'10'+' Complete')
            label3.setText(step_instructions[x-1])
            ### =======>> STEP1
            if current_step == 1:
                timer.disconnect()
                label3.setText(step_instructions[x-1])
                label_view1.setPixmap(QPixmap("Images/step1.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            ### =======>> STEP2
            if current_step == 2:
                timer2.disconnect()
                label_view1.setPixmap(QPixmap("Images/step2.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                count = 600
                timer.start(1000)       ## refreshed 1000ms
                timer.timeout.connect(countdown)
                ### =======>> STEP3
            if current_step == 3:
                label_view1.setPixmap(QPixmap("Images/step3.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                count2 = 200
                timer2.start(1000)       ## refreshed 1000ms
                timer2.timeout.connect(countdown2)
                ### =======>> STEP4
            if current_step == 4:
                label_view1.setPixmap(QPixmap("Images/step4.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                ### =======>> STEP5
            if current_step == 5:
                button_w.hide()
##                cancel()
                label_view1.setPixmap(QPixmap("Images/step5.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                
                
                ### =======>> STEP6
            if current_step == 6:
##                find_angle()
                label_view1.setPixmap(QPixmap("Images/step6.jpg").scaled(1850, b_dim.height()*3/4,
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                button_w.show()
##                camera_view()
                
                ### =======>> STEP7
            if current_step == 7:
                label_view1.setPixmap(QPixmap("Images/step7.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                ### =======>> STEP8
            if current_step == 8:
                label_view1.setPixmap(QPixmap("Images/step8.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                ### =======>> STEP9
            if current_step == 9:
                label_view1.setPixmap(QPixmap("Images/step9.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                ### =======>> STEP10
            if current_step == 10:
                label_view1.setPixmap(QPixmap("Images/step10.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            if current_step > 10 or current_step < 1 :
##                label_view2.hide()
                button_w.hide()
                label_view1.setPixmap(QPixmap("Images/background.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
        if current_step == 1:
            timer.disconnect()
            print(current_step)
            bar.setValue(current_step)
            bar.setFormat(str(bar.value())+'/'+'10'+' Complete')
            label3.setText(step_instructions[x-1])
            label_view1.setPixmap(QPixmap("Images/background2.jpg").scaled(1850,
                                                                           b_dim.height()*3/4,
                                                                           Qt.KeepAspectRatio,
                                                                           Qt.FastTransformation))
            current_step = current_step - 1
    return 

### FUNCTION ===> Save Settings
def save_settings():
    global cwDir, q_field5, user
    global q_field4, q_field3, q_field2
##    print( q_field2.text(), q_field3.text(), q_field4.text())
    date = year + ' ' + month + ' ' + day
    now_time = hour + ' ' + minute
    sav_dir = os.path.realpath(q_field5.text())
    cwd = os.getcwd()
    user = q_field4.text()
    log_setting=[]
    log_setting_name = ['Date-Time', 'System', 'Sample', 'Chip', 'User', 'Data DIR']
    log_setting_value= [date + '-' + now_time,
                        __license__,
                        q_field2.text(),
                        q_field3.text(),
                        user,
                        str(sav_dir)]

    log_setting.append(log_setting_name)
    log_setting.append(log_setting_value)
    print(log_setting)
    try:
        setting_df = pd.DataFrame(log_setting)
        setting_df.to_csv(str(cwd) + '\\' + 'settings' + '\\' + 'settings.csv')
        print('Settings Saved')
    except: print('ERROR on saving settings')
    return

### FUNCTION ===> Load Last save Settings
def load_settings():
    global cwDir, q_field5
    cwd = os.getcwd()
    try:
        load_setting_df = pd.read_csv(cwd+"/settings/settings.csv")
        load_setting_df = load_setting_df.fillna(value=' ')
        previous_setting = load_setting_df[1:].values[0][1:7]
        print(load_setting_df)
        print('Setting Loaded')
        return previous_setting
    except:
        print('loading of settings failed')
    return []

### FUNCTION ===> timer
def countdown():
    global count
##    pump2pressure(740)
##    if count == 250:
##        input_pressure(700)
    now = datetime.datetime.now()
    label3.setText( 'Time now: %s. End time: %s. Seconds left: %s'%(now.strftime("%H:%M:%S"), (now + datetime.timedelta(seconds=count)).strftime("%H:%M:%S"), count))
    count = count - 1
    return

def countdown2():
    global count2
##    pump2pressure(-300)
    now = datetime.datetime.now()
    label3.setText( 'Time now: %s. End time: %s. Seconds left: %s'%(now.strftime("%H:%M:%S"), (now + datetime.timedelta(seconds=count2)).strftime("%H:%M:%S"), count2))
    count2 = count2 - 1
    return 
    
### FUNCTION ===> Pressure run signals to arduino
def pressure():
    sent, read = run_signal("pressure")
    if sent == read:
        try:
            pressure = float(read_signal())    
            print("Pressure ==> ", pressure, "mBar")
            return pressure
        except:
            print("Error reading pressure")
            return 0
    elif read == "Unknown command":
        print("no signal")
    return 0

def pump2pressure(mbar):
    sent, read = run_signal("pump2pressure")
    p = False
    if sent == read:
        send_signal(str(mbar))
    else: return
    for x in range(int(abs(mbar)/2)):
        p = read_signal()
        if p != False:
            print(p)
            return p
    return p

def input_pressure(mbar):
    sent, read = run_signal("input_pressure")
    p = False
    if sent == read:
        send_signal(str(mbar))
    for x in range(int(abs(mbar)/2)):
        p = read_signal()
        if p != False:
            print(p)
            return p
    return p

def xy_position():
    sent, read = run_signal("xy_pos")
    if sent == read:
        try:
            xy_coord = read_signal()
            xy_pos = [int(i) for i in xy_coord.split(",")]
            print(xy_pos)
            return xy_pos[0],xy_pos[1]
        except:
            return -999,-999
    return -999,-999

def fast_pos():
    global arduino
    arduino.write("<fast_pos>".encode("utf-8"))
    data = arduino.readline()[:-2] ##readline() takes max 0.1 seconds to complete
    if data:
        xy_coord = data.decode('UTF-8')
        xy_pos = [int(i) for i in xy_coord.split(",")]
        return xy_pos[0],xy_pos[1]
    return -999,-999

def fast_z():
    global arduino
    char_to_send = "<fast_z>"
    arduino.write(char_to_send.encode("utf-8"))
    data = arduino.readline()[:-2] ##readline() takes max 0.1 seconds to complete
    if data:
        z_coord = data.decode('UTF-8')
        return z_coord
    return -9999

## tolerance is (90,50)
def move_xy(x,y):
    sent, read = run_signal("move_xy")
    if sent == read:
        send_signal(str(x)+","+str(y))
        for x in range(50):
            time.sleep(0.1)
            m = read_signal()
            if m != False:
                return 1
    else: return 0

def fast_xy(x,y):
    send_signal("fast_xy")
    send_signal(str(x)+","+str(y))

def home_xy():
    run_signal("home_xy")

def release_pressure():
    run_signal("release_pressure")

def motor_activate():
    run_signal("motor_activate")
    r = read_signal()
    if int(r) == 0:
        return True
    if int(r) == 1:
        return False
    
def activate():
    run_signal("activate")
    r = read_signal()
    if int(r) == 0:
        return True

def deactivate():
    run_signal("deactivate")
    r = read_signal()
    if int(r) == 1:
        return True

def move_z(z_val):
    run_signal("activate")
    sent, read = run_signal("move_z")
    if sent == read:
        send_signal(str(z_val))
        for x in range(50):
            time.sleep(0.05)
            m = read_signal()
            if m != False:
                return 1
    else: return 0

def z_position():
    sent, read = run_signal("z_pos")
    if sent == read:
        try:
            z_coord = read_signal()
            print(z_coord)
            return z_coord
        except:
            return -9999
    return -9999

def metrics():
    clear_signal()
    send_signal("metrics")
    try:
        metrics_read = read_signal()
        metrics_read = metrics_read.split(",")
        pressure_read = read_signal()
        sys_Pa_value.setText(str(pressure_read) + ' mBar')
        sys_x_pos.setText(metrics_read[1])
        sys_y_pos.setText(metrics_read[2])
        sys_z_pos.setText(metrics_read[3])

        if metrics_read[3] == 0: sys_act_value.setText("True")
        else: sys_act_value.setText("False")
        
        return metrics_read, pressure_read
    except:
        return -999,-999

### IMAGE FUNCTION ===> Autofocus
def autofocus():
    if got_camera == False:
        cprint('No Detectable Camera')
        return
    
    count = 0       #count the frames
    font = cv2.FONT_HERSHEY_SIMPLEX
    focus_values = []
    focus = 0
    f_thresh = 0.97
    f_value = 0
    show_coord = 1
    z_reach = 0
    z_range = 1000
    move_z(-int(z_range/2))
    cam.BeginAcquisition()
    send_signal("move_z")
    send_signal(str(z_range))
    clear_signal()
    start = time.time()
    while(z_reach != 'end' and not(cv2.waitKey(1) & 0xFF == ord('q'))):
        image = cam.GetNextImage()
        pic = np.array(image.GetNDArray())
##        pic = pic[y1:y2, x1:x2]

        # Laplacian Edge Detection
        laplacian = cv2.Laplacian(pic,2,ksize = 5)
        lap_sum = round(np.sum(laplacian),-5)

        cv2.putText(pic, str(lap_sum), (100, 50), font, 1, (0, 255, 0), 1, cv2.LINE_AA)
        if show_coord == 1 and count%25 == 0:
            try:
                z_reach = arduino.readline()[:-2]
                z_reach = z_reach.decode('UTF-8')
                if z_reach == "end": break
            except: pass

        count += 1
        focus_values.append(lap_sum)
##        cv2.imshow('pic',pic)

    ## Analyse the plots
    f_max = max(focus_values)
    count = 0
    focus_values2 = []

    ## run thru the setup
    clear_signal()
    run_signal("z_down")
    while(not(cv2.waitKey(1) & 0xFF == ord('q'))):
        image = cam.GetNextImage()
        pic = np.array(image.GetNDArray())

        # Laplacian Edge Detection
        laplacian = cv2.Laplacian(pic,2,ksize = 5)
        lap_sum = round(np.sum(laplacian),-5)

        cv2.putText(pic, str(lap_sum), (100, 50), font, 1, (0, 255, 0), 1, cv2.LINE_AA)

        if count > 250 or lap_sum >= f_thresh*f_max:
            send_signal("s") ##Stop Signal
            print(lap_sum)
            break
        count += 1
        focus_values2.append(lap_sum)
##        cv2.imshow('pic',pic)
    end = time.time()
    cprint("Focus Max = " + str(f_max) + " Focus Value = " + str(lap_sum))
    cprint("Autofocus time taken = " + str(end-start)) 
      
    image.Release()
##    cv2.destroyAllWindows()
    cam.EndAcquisition()

    clear_signal()
    deactivate()
    z_pos = z_position()
    if z_pos < -1000:
        move_z(-z_pos)
    cprint("---->Autofocus Fail")
    return
    
        
### IMAGE FUNCTION ===> Histogram
def histogram(img):
    ##Histogram show
    hist,bins = np.histogram(img.flatten(),256,[0,256])
    cdf = hist.cumsum()
    cdf_normalized = cdf * float(hist.max()) / cdf.max()
    return cdf, cdf_normalized


### IMAGE FUNCTION ===> find angle
def find_angle():
    global angle
    angle = 0

    pic = grab_image()
    
    ## ROI
    y=500
    h=300
    x = 600
    w = 300
    pic = pic[y:y+h, x:x+w]
    
    print(angle)
    img = pic.copy()
    show(img)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    cl1 = clahe.apply(img)
        
    ret,thresh2 = cv2.threshold(img,150,255,cv2.THRESH_BINARY_INV)
    edges = cv2.Canny(thresh2,50,150,apertureSize = 5)
    minLineLength = 10
    maxLineGap = 10
    lines = cv2.HoughLinesP(thresh2,1,np.pi/180*180,10,minLineLength,maxLineGap)
    tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 360, endpoint=False)    

    try:
        ## Create a CLAHE object (Arguments are optional).
        hspace, angles, distances = hough_line(thresh2, theta=tested_angles)

        coord, angle,dist=[],[],[]
        for space, a , distances in zip(*hough_line_peaks(hspace, angles, distances)):
            coord.append(space)
            angle.append(a)
            dist.append(distances)
        # Obtain angle for each line
        ave_angle = sum(angle)/len(angle)
        ave_angle = ave_angle*180/np.pi
        angles = [a*180/np.pi for a in angle]

        # Compute difference between the two lines
        angle_difference = np.max(angles) - np.min(angles)
##        print(angle_difference)

        angle_list =[]
        
        # iterate over the output lines and draw them
        for line in lines:
            for x1, y1, x2, y2 in line:
                cv2.line(pic, (x1, y1), (x2, y2), (20, 220, 20), 1)
                try:
                    angle_list.append(math.degrees(math.atan((x2-x1)/(y2-y1))))
                except:
                    angle_list.append(90)

        average_angle = sum(angle_list)/len(angle_list)
        print(ave_angle)
##        show(pic)

        angle = ave_angle
    except: print('error')
    return angle


### IMAGE FUNCTION ===> Show
def show(image):
    cv2.namedWindow(str(image),cv2.WINDOW_NORMAL)
    cv2.resizeWindow(str(image), int(image.shape[1]), int(image.shape[0]))
    cv2.imshow(str(image), image)
    return

### IMAGE FUNCTION ===> Grab image
def grab_image():
    global no_cancel, got_camera, num_cameras, cam
    global width, height

    no_cancel = True
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    camera_start()
    if got_camera == True and num_cameras == 0:
        print('trouble')
        got_camera = False
        return
    
    if got_camera == False:
        cprint('No Detectable Camera')
    
    print('Initial FPS view = ',cam.AcquisitionFrameRate.GetValue())
    camera_properties(width, height, 25)
    cam.BeginAcquisition()
    image_primary = cam.GetNextImage()
    frame = np.array(image_primary.GetNDArray())
    cam.EndAcquisition()
    camera_reset()
    no_cancel = False
    
    return frame   

    
### ************************************ ###
###            Widgets Class             ###
### ************************************ ###
class myLabel(QLabel):
    clicked = QtCore.pyqtSignal()
    def mouseMoveEvent(self, event):
##        self.setText('coords: ( % d : % d )' % (event.x(), event.y()))
        return
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            print(QMouseEvent.x(), QMouseEvent.y())
##            self.setText('coords: ( % d : % d )' % (QMouseEvent.x(), QMouseEvent.y()))
            self.clicked.emit()
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            print(QMouseEvent.x(), QMouseEvent.y())
            self.clicked.emit()

class motor_move_down(QPushButton):
    def __init__(self, content):
        super(motor_move_down, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            send_signal("down")
            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
            self.setStyleSheet(class_btn_1)

class motor_move_up(QPushButton):
    def __init__(self, content):
        super(motor_move_up, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            send_signal("up")
            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
            self.setStyleSheet(class_btn_1)
            

class motor_move_left(QPushButton):
    def __init__(self, content):
        super(motor_move_left, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            send_signal("right")
            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
            self.setStyleSheet(class_btn_1)
            

class motor_move_right(QPushButton):
    def __init__(self, content):
        super(motor_move_right, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            send_signal("left")
            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
            self.setStyleSheet(class_btn_1)

class zaxis_move_up(QPushButton):
    def __init__(self, content):
        super(zaxis_move_up, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            send_signal("z_up")
##            cprint("send signal z up")
##            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
##            cprint("send signal s")
##            self.setStyleSheet(class_btn_1)

class zaxis_move_down(QPushButton):
    def __init__(self, content):
        super(zaxis_move_down, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            ##clear_signal()
            send_signal("z_down")
##            cprint("send signal z down")
##            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
##            cprint("send signal s")
##            self.setStyleSheet(class_btn_1)

class motor_activation(QPushButton):
    def __init__(self, content):
        super(motor_activation, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            self.setText("Activate")
            sys_act_value.setText("False")
            if motor_activate() == True:
                self.setText("Deactivate")
                sys_act_value.setText("True")
##                self.setText("Deactivate")
            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
            self.setStyleSheet(class_btn_1)


class motor_move_xy(QPushButton):
    def __init__(self, content):
        super(motor_move_xy, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            x = move_x_value.text()
            y = move_y_value.text()
            activate()
            fast_xy(int(x),int(y))
##            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            move_x_value.setText("0")
            move_y_value.setText("0")
            send_signal("s")
##            self.setStyleSheet(class_btn_1)

class motor_move_z(QPushButton):
    def __init__(self, content):
        super(motor_move_z, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            z = move_z_value.text()
            move_z(int(z))
##            self.setStyleSheet(class_btn_2)
##            timer3.start(1000)
##            timer3.timeout.connect(metrics)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
            move_z_value.setText("0")
##            self.setStyleSheet(class_btn_1)

class set_outlet_pressure(QPushButton):
    def __init__(self, content):
        super(set_outlet_pressure, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            Pa = out_Pa_value.text()
            print(Pa)
            try: pump2pressure(int(Pa))
            except: pass
##            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
##            self.setStyleSheet(class_btn_1)

class set_inlet_pressure(QPushButton):
    def __init__(self, content):
        super(set_inlet_pressure, self).__init__()
        self.setText(content)
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            clear_signal()
            Pa = in_Pa_value.text()
            input_pressure(int(Pa))
##            self.setStyleSheet(class_btn_2)
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            send_signal("s")
##            self.setStyleSheet(class_btn_1)

class Label(QLabel):
    def __init__(self, content):
        super(Label, self).__init__()
        self.setText(content)
        self.setFont(QFont('Times', 11))
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setFixedSize(150,22)

class LineEdit(QLineEdit):
    def __init__(self, content):
        super(LineEdit, self).__init__()
        self.setText(content)
        self.setStyleSheet("background-color: rgb(255,255,255)")
        self.setFont(QFont('Times', 9))
        self.setFixedSize(400,22)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
class CustomDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(CustomDialog, self).__init__(*args, **kwargs)

        self.setWindowTitle("HELLO!")

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

class Color(QWidget):
    def __init__(self, color, *args, **kwargs):
        super(Color, self).__init__(*args, **kwargs)
        self.setAutoFillBackground(True)

        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(color))
        self.setPalette(palette)
        
### ---- Button Settings --- ###
btn1 = ("QPushButton { background-color: rgb(25,185,75); font: bold 12px;}"
        "QPushButton { border-color: rgb(40,40,15); border-width: 2px; }"
        "QPushButton { border-style: inset; border-radius: 4px; padding: 2px; }"
        "QPushButton:pressed { background-color: rgb(50,165,75) }")
dir_btn = ("QPushButton { background-color: rgb(200,100,120); font: bold 15px;}"
           "QPushButton { border-style: inset; border-radius: 45px; padding: 2px; }"
           "QPushButton { border-color: rgb(40,40,15); border-width: 2px; }"
           "QPushButton:pressed { background-color: rgb(230,150,150) }")

class_btn_1 = ("background-color: rgb(200,100,120); font: bold 15px; border-style: inset; border-radius: 45px; padding: 2px;border-color: rgb(40,40,15); border-width: 2px;")
class_btn_2 = ("background-color: rgb(230,150,150); font: bold 15px; border-style: inset; border-radius: 45px; padding: 2px;border-color: rgb(40,40,15); border-width: 2px;")


### ************************************ ###
###           Global Variables           ###
### ************************************ ###
### =====> GUI 
run_step = [i+1 for i in range(11)]
current_step = 0
step_instructions = ['Step 1: Assemble the chip and tubings',
                     'Step 2: Priming the chip',
                     'Step 3: Change the PBS',
                     'Step 4: Wash the sample inlet',
                     'Step 5: Wash the chip',
                     'Step 6: Catch the outlet',
                     'Step 7: Run the test',
                     'Step 8: Confirm the next outlet',
                     'Step 9: Run the test',
                     'Step 10: Discard your sample',
                     'Shutdown sequence']
cwDir = os.getcwd()
user = ' '
year, month, month_b , day, hour, minute = date_time()
present = day + ' ' + month_b + ' ' + year + ' ' + '('+ hour + ':' + minute + ')'
file_stem = 'Name Your File'
filename = 'file.save'
console_log = []
console_num = 0
count = 0
count2 = 0

roi_x, roi_y , roi_width, roi_height = 0,0,0,0
capture_x,capture_y, capture_width, capture_height = 0,0,0,0

### =====> Camera Settings
exposure_time = 100         #micro seconds min=10us
FPS = 25                    #Frame rate to capture
gain = 0                    #Sensor gain
image_format = 'Mono8'      #image pixel format. 'Mono8' or 'Bayer' for BGR
width = 1440                #image width in pixels
height = 1080                #image height in pixels
Show = 1                    #Show = show the video while loop
num_frames = 1000           #number of frames to view
video_record = 0            #1: to record the video, 0: No Record
video_mode = 'AVI'         #AVI or MJPG 
video_name = 'a.avi'        #Filename to save as
got_camera = False
no_cancel = False

#angle variables
angle = 0                   #rotational angle
rot_x = 0                   #x pos value of final rotated and cropped image
rot_y = 0                   #y pos value of final rotated and cropped image
rot_width = width               #width of final rotated and cropped image
rot_height = height              #height of final rotated and cropped image

### ---- Qt Initialize --- ###
## Always start by initializing Qt (only once per application)
app = QApplication([])
settingload, arduino = start_event()
if len(settingload) != 0:
    cwDir = settingload[5]
    user = settingload[4]


### ************************************ ###
###            Camera  Start             ###
### ************************************ ###
# [GET] system
system = PySpin.System.GetInstance()
    
### ************************************ ###
###            Widgets Start             ###
### ************************************ ###
## Define a top-level widget to hold everything
w = QWidget()
w.setWindowTitle('The window for testing')
w.setStyleSheet("background-color: rgb(240,240,240)")
w.setWindowTitle("Color")
# To maximise view in screen, optimised for p1080
screen_dim = QDesktopWidget().availableGeometry() # geometry (x,y,width,height)
if screen_dim.width() <= 1920 and screen_dim.height() <= 1080:
    w.setWindowState(Qt.WindowMaximized)
else:
    w.setGeometry(0,0,1920,1080)  ##(x,y (downsward), lenght, height)
w_dim = w.geometry()

## Define "Basic" Tab widget
basic_w = QWidget()

## Define "Basic" Tab widget
basic_w_run = QWidget()

## Define "Advanced" Tab widget
advance_w = QWidget()
advance_view = QWidget()                ##set widget in advance tab
advance_view.setGeometry(11,58,1854,802)

### ---- Create some widgets to be placed inside ---- ###
# =====  Menu  ===== #
menubar = QMenuBar()
actionFile = menubar.addMenu("File")
actionFile.addAction("New")
actionFile.addAction("Open")
actionFile.addAction("Save")
actionFile.addSeparator()
actionFile.addAction("Quit")
menubar.addMenu("Edit")
menubar.addMenu("View")
menubar.addMenu("Help")


# ==== Advance Dropdown Menu ===== #
file_type_menu = QComboBox()
file_type_menu.addItem('AVI')
file_type_menu.addItem('MJPG')
file_type_menu.addItem('MP4')

menu2 = QComboBox()
menu2.addItem('Min/Max - Blob Detection')
menu2.addItem('BLUR - Median blur MTD')

# ==== Checkbox ===== #
chk_box1 = QCheckBox('Show Video');
        
# ===== Labels ===== #
label1 = QLabel()
##img = QImage('Images/background.jpg')
##img = QPixmap.fromImage(img)
label1.setPixmap(QPixmap("Images/background.jpg"))
label1.setAlignment(Qt.AlignCenter)
##label1.clicked.connect(clicked)   ## to run a function

label2 = myLabel()
label2.setPixmap(QPixmap("Images/background2.jpg"))
label2.setAlignment(Qt.AlignCenter)
label2.resize(100, 40)

label3 = QLabel('Here we go')
label3.setFont(QFont('Calibri', 20))
label3.setFixedSize(1850, 40)
label3.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
# -----Advance Tab Labels----- #
sys_x = QLabel('X:');sys_x.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
sys_x_pos = QLabel('10000')
sys_y = QLabel('Y:');sys_y.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
sys_y_pos = QLabel('4000')
sys_z = QLabel('Z:');sys_z.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
sys_z_pos = QLabel('-2000')
sys_Pa = QLabel('Pressure :');sys_Pa.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
sys_Pa_value = QLabel('-440' + ' mBar')
sys_act = QLabel('Activation :');sys_act.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
sys_act_value = QLabel('FALSE') ## motor_move_up('UP');
sys_cam = QLabel('Camera :');sys_cam.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
sys_cam_on = QLabel('OFFLINE')
sys_valves = QLabel('Valves :');sys_valves.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
sys_valves_on = QLabel('OFF')
file_name = QLabel('Name File:')
file_type = QLabel('File Type:')
cam_fps = QLabel('FPS:')
cam_exp = QLabel('Exposure Time (us):')
cam_frame = QLabel('No. of Frames:')
cam_gain = QLabel('Gain:')
cam_wh = QLabel('Camera Width:')
cam_rotate = QLabel('Rotation:')
cam_roi = QLabel('Show ROI')
cam_scale = QLabel('Window Scale')
cam_ch = QLabel('Channels:')
cam_delay = QLabel('Delay (ms):')
cam_skip = QLabel('No. of Frame Skip:')

a_view_label = QLabel()
a_view_label.setText('OpenCV Image')
a_view_label.setAlignment(Qt.AlignCenter)
a_view_label.setFixedSize(1200,800)
##!!!!! IMPORTANT !!!!!##
## --> NEED to set label fixed size for setpiximage to be fast and little lag


# ==== Entries ==== #
b_field4 = LineEdit(present)
b_field4.setFixedSize(400,25)
q_field1 = LineEdit(present)
q_field2 = LineEdit('')
q_field3 = LineEdit('')
q_field4 = LineEdit(user)
q_field5 = LineEdit(cwDir)
# -----Advance Line Entries----- #
move_x_value = QLineEdit('0')
move_y_value = QLineEdit('0')
move_z_value = QLineEdit('0')
out_Pa_value = QLineEdit('mBar')
release_Pa_value = QLineEdit('Yes')
in_Pa_value = QLineEdit('mBar')
file_value = QLineEdit('Name Your File')
folder_value = QLineEdit(str(cwDir))
cam_fps_value = QLineEdit(str(FPS))
cam_exp_value = QLineEdit(str(exposure_time))
cam_frame_value = QLineEdit(str(num_frames))
cam_gain_value = QLineEdit(str(gain))
cam_w_value = QLineEdit(str(width))
cam_h_value = QLineEdit(str(height))
cam_ch_value = QLineEdit('35')
cam_delay_value = QLineEdit('1')
cam_skip_value = QLineEdit('25')

# ===== Tabs   ===== #
tab = QTabWidget()
tab.addTab(basic_w, "Basic")
tab.addTab(advance_w, "Advanced Options") #tab.setTabEnabled(0,False) -> to endable/disable
##tab.setTabText(0,"Contact Details")
##tab.setTabText(1,"Advanced Details")
tab.setTabShape(0)      #0 = rounded 1 = Triangular
tab.setStyleSheet("background-color: rgb(225,225,225); border-width: 1px")

# ==== Buttons ==== #
begin_b = QPushButton('Begin Assay'); begin_b.setStyleSheet(btn1); begin_b.setFixedSize(200,50)
next_b = QPushButton('Next'); next_b.setStyleSheet(btn1); next_b.setFixedSize(80,40)
back_b = QPushButton('Back'); back_b.setStyleSheet(btn1); back_b.setFixedSize(80,40)
advance_b = QPushButton('Advance Button'); advance_b.setFixedSize(200,50)
##new_btn = QPushButton('Back',basic_w)
##new_btn.move(500,100)

# -----Advance Tab Buttons----- #
btn1 = QPushButton('BTN1'); btn1.setFixedSize(80,25)
btn2 = QPushButton('BTN2'); btn2.setFixedSize(80,25)
btn3 = QPushButton('BTN3'); btn3.setFixedSize(80,25)
btn4 = QPushButton('BTN4'); btn4.setFixedSize(80,25)
up_btn = motor_move_up('U'); up_btn.setFixedSize(45,45); up_btn.setStyleSheet(class_btn_1) 
down_btn = motor_move_down('D'); down_btn.setFixedSize(45,45); down_btn.setStyleSheet(class_btn_1)
left_btn = motor_move_left('L'); left_btn.setFixedSize(45,45); left_btn.setStyleSheet(class_btn_1)
right_btn = motor_move_right('R'); right_btn.setFixedSize(45,45); right_btn.setStyleSheet(class_btn_1)
focus_btn = QPushButton('AF'); focus_btn.setFixedSize(45,45) 
z_up_btn = zaxis_move_up('U_F'); z_up_btn.setFixedSize(45,45)
z_down_btn = zaxis_move_down('D_F'); z_down_btn.setFixedSize(45,45)
move_xy_btn = motor_move_xy('Move_xy [ x , y ]:')
move_z_btn = motor_move_z('Move_Z')
out_Pa_btn = set_outlet_pressure('Set Outlet Pressure (mBar)')
release_Pa_btn = QPushButton('Release Pressure')
home_btn = QPushButton('XY Home')
activation_btn = motor_activation('Motor Activation')
in_Pa_btn = set_inlet_pressure('Set Inlet Pressure (mBar)')
folder_btn = QPushButton('Select Folder(s):')


# ==== Checkbox ===== #
chk_box1 = QCheckBox('Show Video'); chk_box1.setCheckState(True); chk_box1.setTristate(False)
chk_box2 = QCheckBox('Flip Video'); chk_box2.setCheckState(False)
chk_box3 = QCheckBox('Window Scale'); chk_box3.setCheckState(True); chk_box3.setTristate(False)
cam_roi_box = QCheckBox('Show ROI'); cam_roi_box.setCheckState(False);cam_roi_box.setTristate(False)
cam_scale_box = QCheckBox('Window Scale'); cam_scale_box.setCheckState(False);cam_scale_box.setTristate(False)

# ==== Sliders ===== #
cam_rotate_slide = QSlider(Qt.Horizontal)
cam_rotate_slide.setMinimum(-40)
cam_rotate_slide.setMaximum(40)
cam_rotate_slide.setValue(0)
cam_rotate_slide.setTickPosition(QSlider.TicksBelow) #TicksBothSides, TicksBelow
cam_rotate_slide.setSingleStep(1)
cam_rotate_slide.setTickInterval(4)
##slide1.valueChanged.connect(rotation_value)

# ==== Progress Bar ==== #
bar = QProgressBar()
bar.setMaximum(10)
bar.setValue(0)
bar.setGeometry(200, 100, 200, 110)
##bar.setFormat('%p%'+' Complete')
bar.setFormat(str(bar.value())+'/'+'10'+' Complete')
bar.setFont(QFont('Calibri', 14))
bar.setAlignment(Qt.AlignVCenter)

a_bar = QProgressBar()

# ==== Timer Object ==== #
timer = QTimer()
timer2 = QTimer()
timer3 = QTimer()

# ==== CONSOLE LIST ==== #
console_list = QListWidget()
console_list.setFixedSize(w_dim.width()*0.8,100)

### ---- Main window layout ---- ###
bigLayout =  QGridLayout()
bigLayout.addWidget(menubar,0,0)
bigLayout.addWidget(tab,1,0)

### ---- ADVANCE Tab layout LVL 1 ---- ###
box_button = QGroupBox('Buttons')
box_button.setStyleSheet("QGroupBox{ border: 0.5px solid; border-color: rgba(0, 0, 0, 75%);}")
box_camera = QGroupBox('Camera Settings') # note: box_camera will be set in box_button
box_system = QGroupBox('System Settings') # note: box_system will be set in box_button
box_motor = QGroupBox('System Controls') # note: box_motor will be set in box_button
box_motor_control = QGroupBox('Motor Controls') # note: box_motor_control will be set in box_motor
box_view = QGroupBox('View Video')
advanceLayout =  QGridLayout()
advanceLayout.addWidget(box_view,0,0,1,5)
advanceLayout.addWidget(box_button,0,5,0,1)
advanceLayout.addWidget(a_bar,1,0,1,5)
advanceLayout.addWidget(console_list,2,0,1,5)
### ---- ADVANCE Tab layout LVL 2 ---- ###
### ----------box_view-------------- ###
box_view_Layout = QGridLayout() ##define layout for camera view
box_view_Layout.addWidget(a_view_label,0,0)
box_view.setLayout(box_view_Layout)
### ----------box_Button-------------- ###
box_button_Layout = QGridLayout() ##define layout - Box type
box_button_Layout.addWidget(btn1, 0, 2,1,1)
box_button_Layout.addWidget(btn2, 0, 3,1,1)
box_button_Layout.addWidget(btn3, 0, 4,1,1)
box_button_Layout.addWidget(btn4, 0, 1,1,1)
box_button_Layout.addWidget(box_system,1,0,1,5)
box_button_Layout.addWidget(box_motor,2,0,4,5)
box_button_Layout.addWidget(box_camera,6,0,5,5)
box_button.setLayout(box_button_Layout)
### ---- ADVANCE Tab layout LVL 3 ---- ###
### ----------box_system-LVL 3-------- ###
box_system_Layout = QGridLayout() ## grid is split into 12 grid size 0-11 columns
## (widget, row, column, row length, column length)
box_system_Layout.addWidget(sys_act,        2, 0, 1, 3)
box_system_Layout.addWidget(sys_act_value,  2, 3, 1, 1)
box_system_Layout.addWidget(sys_x,          2, 5, 1, 1)
box_system_Layout.addWidget(sys_x_pos,      2, 6, 1, 1)
box_system_Layout.addWidget(sys_y,          2, 7, 1, 1)
box_system_Layout.addWidget(sys_y_pos,      2, 8, 1, 1)
box_system_Layout.addWidget(sys_z,          2, 10, 1, 1)
box_system_Layout.addWidget(sys_z_pos,      2, 11, 1, 1)
box_system_Layout.addWidget(sys_Pa,         3, 0, 1, 3)
box_system_Layout.addWidget(sys_Pa_value,   3, 3, 1, 1)
box_system_Layout.addWidget(sys_cam,        3, 4, 1, 3)
box_system_Layout.addWidget(sys_cam_on,     3, 7, 1, 1)
box_system_Layout.addWidget(sys_valves,     3, 8, 1, 3)
box_system_Layout.addWidget(sys_valves_on,  3, 11, 1, 1)
##box_system_Layout.addWidget(sys_btn_0, 0, 0, 1, 4)
##box_system_Layout.addWidget(sys_field_0, 0, 4, 1, 8)
##box_system_Layout.addWidget(sys_label_1, 1, 0, 1, 2)
##box_system_Layout.addWidget(sys_field_1, 1, 4, 1, 8)
##box_system_Layout.addWidget(sys_label_2, 2, 0, 1, 2)
##box_system_Layout.addWidget(sys_menu_2, 2, 4, 1, 8)
##box_system_Layout.addWidget(sys_label_9, 9, 0, 1, 4)    ## show ROI
##box_system_Layout.addWidget(sys_box_9, 9, 4, 1, 8)
##box_system_Layout.addWidget(sys_label_10, 10, 0, 1, 4)
##box_system_Layout.addWidget(sys_slide_10, 10, 4, 1, 8)
box_system.setLayout(box_system_Layout)
### ----------box_motor-LVL 3--------- ###
box_motor_Layout = QGridLayout()
box_motor_Layout.addWidget(activation_btn,      1,0,1,2)
box_motor_Layout.addWidget(home_btn,            1,2,1,2)
box_motor_Layout.addWidget(release_Pa_btn,      1,4,1,2)
box_motor_Layout.addWidget(move_xy_btn,         2,0,1,2)
box_motor_Layout.addWidget(move_x_value,        2,2,1,2)
box_motor_Layout.addWidget(move_y_value,        2,4,1,2)
box_motor_Layout.addWidget(move_z_btn,          3,0,1,2)
box_motor_Layout.addWidget(move_z_value,        3,2,1,4)
box_motor_Layout.addWidget(out_Pa_btn,          4,0,1,2)
box_motor_Layout.addWidget(out_Pa_value,        4,2,1,4)
box_motor_Layout.addWidget(in_Pa_btn,           5,0,1,2)
box_motor_Layout.addWidget(in_Pa_value,         5,2,1,4)
### ------ Motor Control - LVL 4 ----- ###
box_motor_ctrl_Layout = QGridLayout()
box_motor_ctrl_Layout.addWidget(up_btn,     0,4,1,1)
box_motor_ctrl_Layout.addWidget(down_btn,   2,4,1,1)
box_motor_ctrl_Layout.addWidget(left_btn,   1,3,1,1)
box_motor_ctrl_Layout.addWidget(right_btn,  1,5,1,2)
box_motor_ctrl_Layout.addWidget(focus_btn,  1,1,1,2)
box_motor_ctrl_Layout.addWidget(z_up_btn,   0,1,1,2)
box_motor_ctrl_Layout.addWidget(z_down_btn, 2,1,1,2)
box_motor_control.setLayout(box_motor_ctrl_Layout)
### ---------------------------------- ###
box_motor_Layout.addWidget(box_motor_control,   0,0,1,6)
box_motor.setLayout(box_motor_Layout)
### ----------box_camera-LVL 3-------- ###
box_camera_Layout = QGridLayout()
box_camera_Layout.addWidget(folder_btn,         0,0,1,1)
box_camera_Layout.addWidget(folder_value,       0,1,1,2)
box_camera_Layout.addWidget(file_name,          1,0,1,1)
box_camera_Layout.addWidget(file_value,         1,1,1,2)
box_camera_Layout.addWidget(file_type,          2,0,1,1)
box_camera_Layout.addWidget(file_type_menu,     2,1,1,2)
box_camera_Layout.addWidget(cam_fps,            3,0,1,1)
box_camera_Layout.addWidget(cam_fps_value,      3,1,1,2)
box_camera_Layout.addWidget(cam_exp,            4,0,1,1)
box_camera_Layout.addWidget(cam_exp_value,      4,1,1,2)
box_camera_Layout.addWidget(cam_frame,          5,0,1,1)
box_camera_Layout.addWidget(cam_frame_value,    5,1,1,2)
box_camera_Layout.addWidget(cam_gain,           6,0,1,1)
box_camera_Layout.addWidget(cam_gain_value,     6,1,1,2)
box_camera_Layout.addWidget(cam_wh,             7,0,1,1)
box_camera_Layout.addWidget(cam_w_value,        7,1,1,1)
box_camera_Layout.addWidget(cam_h_value,        7,2,1,1)
box_camera_Layout.addWidget(cam_rotate,         8,0,1,1)
box_camera_Layout.addWidget(cam_rotate_slide,   8,1,1,2)
box_camera_Layout.addWidget(cam_roi,            9,0,1,1)    ## show ROI
box_camera_Layout.addWidget(cam_roi_box,        9,1,1,1)
box_camera_Layout.addWidget(cam_scale,          10,0,1,1)    ## show ROI
box_camera_Layout.addWidget(cam_scale_box,      10,1,1,1)
box_camera_Layout.addWidget(cam_ch,             11,0,1,1)
box_camera_Layout.addWidget(cam_ch_value,       11,1,1,2)
box_camera_Layout.addWidget(cam_delay,          12,0,1,1)
box_camera_Layout.addWidget(cam_delay_value,    12,1,1,2)
box_camera_Layout.addWidget(cam_skip,           13,0,1,1)
box_camera_Layout.addWidget(cam_skip_value,     13,1,1,2)
box_camera.setLayout(box_camera_Layout)

### ---- Basic Tab layout ---- ###
basicLayout =  QGridLayout()
basicLayout.addWidget(begin_b)
### ---- Basic Tab Expt layout ---- ###
action_bar = QWidget()
basicLayout_action = QHBoxLayout()
basicLayout_action.addWidget(back_b)
basicLayout_action.addWidget(bar)
basicLayout_action.addWidget(next_b)
action_bar.setLayout(basicLayout_action)

steps_view = QWidget()
steps_view.setGeometry(11,58,1854,802)
b_dim = steps_view.geometry()
label_view1 = QLabel('Image1',steps_view)
label_view1.setFixedSize(b_dim.width(),b_dim.height())
label_view1.setPixmap(QPixmap("Images/background.jpg").scaled(1850, 200,
                                                               Qt.KeepAspectRatio, Qt.FastTransformation))
label_view1.move(0,0) ## Move(x,y with y = middle and x = left)
##label_view1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

label_view2 = QLabel('Image2',steps_view)

label_view2.setFixedSize(b_dim.width(),b_dim.height())
label_view2.setPixmap(QPixmap("Images/background2.jpg").scaled(1850, 200,
                                                               Qt.KeepAspectRatio, Qt.FastTransformation))
label_view2.move(600,0) ## Move(x,y with y = middle and x = left)
label_view2.hide()
##label_view2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

##-->Buttons
button_dim = 300
button_w = QWidget(steps_view)
button_w.setGeometry(b_dim.width()-button_dim,(b_dim.height()-button_dim)/2,
                     button_dim,button_dim)
label_up = motor_move_up('UP');label_up.setFixedSize(80, 80) ##; label_up.setStyleSheet(dir_btn)
label_down = motor_move_down('DOWN');label_down.setFixedSize(80, 80)##; label_down.setStyleSheet(dir_btn)
label_left = motor_move_left('LEFT');label_left.setFixedSize(80, 80)##; label_left.setStyleSheet(dir_btn)
label_right = motor_move_right('RIGHT');label_right.setFixedSize(80, 80)##; label_right.setStyleSheet(dir_btn)
label_focus = QPushButton('Focus');label_focus.setFixedSize(80, 80)##; label_focus.setStyleSheet(dir_btn)
move_z_up = zaxis_move_up('Z-Axis Up')##; move_z_up.setFixedSize(90, 90); move_z_up.setStyleSheet(dir_btn)
move_z_down = zaxis_move_down('Z-Axis Down')##; move_z_down.setFixedSize(90, 90); move_z_down.setStyleSheet(dir_btn)

button_view = QGridLayout(button_w)
button_view.addWidget(label_up, 0,1)
button_view.addWidget(label_down, 2,1)
button_view.addWidget(label_left, 1,0)
button_view.addWidget(label_right, 1,2)
button_view.addWidget(label_focus, 1,1)
button_view.addWidget(move_z_up, 3,1)
button_view.addWidget(move_z_down, 4,1)
button_w.hide()

basicLayout_run =  QVBoxLayout()
basicLayout_run.addWidget(label3,1)
basicLayout_run.addWidget(steps_view,12)
basicLayout_run.addWidget(action_bar,1)

#set the layout for the basic_w_run QWidget
basic_w_run.setLayout(basicLayout_run)

##for n, color in enumerate(['red','green','blue','yellow']):
####   btn = QPushButton( str(color) )
####   btn.pressed.connect( lambda n=n: layout.setCurrentIndex(n) )
####   button_layout.addWidget(btn)
##   layout.addWidget(Color(color))

## Action Mouse clicks ##
begin_b.clicked.connect(showdialog)
next_b.clicked.connect(run_expt)
back_b.clicked.connect(back_expt)
# Advance Tab Buttons ##
btn1.clicked.connect(camera_view)
btn2.clicked.connect(cancel)
home_btn.clicked.connect(home_xy)
release_Pa_btn.clicked.connect(release_pressure)
focus_btn.clicked.connect(autofocus)
##label_focus.clicked.connect(autofocus)

## execute the widget layouts
w.setLayout(bigLayout)
basic_w.setLayout(basicLayout)
advance_w.setLayout(advanceLayout)

camera_start()
### ---- Display the widget as a new window ---- ###
w.show()
app.exec_()

### ---- Close event function run ---- ###
##w.closeEvent(close_event())
close_event()
