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

__author__      = "Kerwin Kwek Zeming"
__copyright__   = "SMART-CAMP"
__credits__     = "Kerwin Kwek Zeming, Quek Kai Yun, Goh Chin Ren and Nicholas"
__license__     = "S01-KKH-200"
__version__     = "2.00.00"
__maintainer__  = "Kerwin Kwek Zeming"
__email__       = "kerwin@smart.mit.edu"
__status__      = "Development"
__serial__      = "VID:PID=1A86:7523"


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
    global cam, got_camera, no_cancel
    print('[END Sequence] Application End Closing Sequence...')
    
    if no_cancel == True:
        cancel()

    try:
        cam.EndAquisition()
        print("[END Sequence] CAM End Aquisition")
    except: pass
    
    ## Disconnect camera
    got_camera = False
    print("Camera closing sequence completed")
    ## Save last settings
    try: save_settings()
    except: print("[END SEQUENCE] Enable to Save settings")

    ## home
    
    if arduino == 0: print('Arduino is nt connected')
    else:
        release_pressure()
##        home_xy()

##    ## Power down and Home
##    try: arduino.close(); print('Serial connection disconnected')
##    except: print('Serial connection unavailable') 
        
    ## Finally...if all else fails
    try:
        w.close()
        print('The window has shutdown')
        sys.exit(0)
        print('The application has shutdown')
    except: return
    return

### FUNCTION ===> Find Arduino Port
##### ------- Change the port if serial number is not the correct one
def find_arduino(serial_number = __serial__):
    myports = list(ports.comports())
    for port in myports:
        p,des,ser_id = port
        print(p, des, ser_id)
        if port.serial_number == serial_number or __serial__ in ser_id:
            print("==> USB arduino serial port found")
            return p,des,ser_id
    ##### HERE ---> Change the port
    print("==> Arduino serial not identified, using default 'COM4' PORT")
    return ["COM3"]
    
### FUNCTION ===> Check connection to USB system
def check_connection(timeout, com_port = find_arduino()[0]):
    length_timeout = 0
    while (length_timeout < timeout):
        if com_port:
            print("==> System is connected via USB!")
            try:
                arduino = serial.Serial(com_port, 115200, timeout=.1)
                print("==> Serial Communication is Online")
                return arduino
            except:
                print("==> Unable to proceed with Serial communication")
                print("==> [System is NOT connected]")
                return 0
        else:
            length_timeout += 1
            time.sleep(0.5)
            print('connecting...')
    print("==> [System is NOT connected]")
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
    global no_cancel, got_camera
    if no_cancel == True:
        print('FPS view = ',cam.AcquisitionFrameRate.GetValue())
        no_cancel = False
        camera_reset()
        try:
            if tab.currentIndex() == 1: a_view_label.setText("Camera Off")
        except:
            cprint("unable to change label text")
        cprint("Camera Off")
        return
    else:
        return

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
    global cam
    cam.OffsetY.SetValue(0)
    cam.OffsetX.SetValue(0)
    return

### FUNCTION ===> CAMERA START
def camera_start():
    global got_camera, cam, cam_list, num_cameras

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
    exposure_time = cam_exp_value.text() #min(cam.ExposureTime.GetMax(), int(exposure_time))
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
    global feature_matching, current_step

    print('start cam1')
    no_cancel = True
    tab_index = tab.currentIndex()
    print("current tab is",tab_index)
    cam_list = system.GetCameras()
    num_cameras = cam_list.GetSize()
    print('start cam2')
    camera_start()
    font = cv2.FONT_HERSHEY_SIMPLEX

    print('start cam0')
    if got_camera == True and num_cameras == 0:
        print('trouble')
        got_camera = False
        return

    if got_camera == False:
        cprint('No Detectable Camera')
        return

##    if no_cancel == True:
##        cprint("Camera is already on")
##        return
    
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
    print('Initial FPS view1 = ',cam.AcquisitionFrameRate.GetValue())
    camera_properties(width, height, 25)
    cam.BeginAcquisition()

    while no_cancel:
        image_primary = cam.GetNextImage()
        frame = np.array(image_primary.GetNDArray())
            
        if angle !=0:
            frame = cv2.warpAffine(frame,M,(int(x2),int(y2)))
            ##frame_crop = frame[rot_y:(rot_y+rot_height) , rot_x:(rot_x+rot_width)]

        ## Draw Part of Auto Roi flow
        if current_step == 6:
            ## for Center Big Dot
            cv2.rectangle(frame,(width-1240,height-920),(width-200,height-120),(255,255,255),3)
            ## for 4 Dots
            cv2.rectangle(frame,(775,250),(775+detect_ybuffer,250+detect_xbuffer),(255,255,255),3)
            cv2.putText(frame, "Is Feature in Box", (150, 120), font, 2, (255, 255, 255), 3, cv2.LINE_AA)

        if current_step == 8:
            cv2.rectangle(frame,(405,200),(405+detect_ybuffer,350+detect_xbuffer),(255,255,255),3)
            cv2.putText(frame, "Is Feature in Box", (150, 120), font, 2, (255, 255, 255), 3, cv2.LINE_AA)

        img = QImage(frame, int(x2), int(y2), int(x2), qformat)
        if angle != 0:
            img = img.copy(rot_x, rot_y, rot_width, rot_height)    # copy(int x, int y, int width, int height)
        img = QPixmap.fromImage(img)
        img = img.scaledToHeight(720)
        if tab_index == 0:
            label_view2.setPixmap(img)
        elif tab_index == 1:
            a_view_label.setPixmap(img)
        cv2.waitKey(1)
    cam.EndAcquisition()
    print(tab_index)
    print('FPS view = ',cam.AcquisitionFrameRate.GetValue())
    camera_reset()
    no_cancel = False
    return

### FUNCTION ===> SAVE and PROCESS DATA
def save_data(fps = 150, file_preffix = "Test", video_format = 'MP4'):
    global no_cancel, got_camera, FPS, angle, num_cameras, cam
    global ROI_x, ROI_y, ROI_h, ROI_w, width, height, channels
    global ROT_x, ROT_y, ROT_h, ROT_w
    global cwDir, dataDir, run_assay1, run_assay2, data_path

    b_bar.setValue(0)
    ## 1: Check if Cam is functional and operartional
    try:
        camera_reset()
        camera_start()
    except:
        print("[ERROR CAM] Cannot reset for save data")

    if got_camera == True and num_cameras == 0:
        print('The camera was disconnected')
        got_camera = False
        return
    
    if got_camera == False:
        print('No Detectable Camera')
        return

    ##Start the session
    no_cancel = True
    ## Camera Properties
    FPS = int(fps)
    camera_properties(width , height, FPS)
    print('Initial FPS view3 = ',cam.AcquisitionFrameRate.GetValue())

    ## Data Processing Parameters, properties, variabes
    count = 0
    save_mode = 0
    process_data = 1
    qformat = QImage.Format_Indexed8
    mask = cv2.createBackgroundSubtractorMOG2(history = 3,
                                              varThreshold = 100,
                                              detectShadows = False)
    if FPS <= 15:
##        b_bar.setMaximum(75)
##        max_frame = 75
        b_bar.setMaximum(3000)
        max_frame = 3000
    elif FPS >= 150:
##        b_bar.setMaximum(450)
##        max_frame = 450
        b_bar.setMaximum(8000)
        max_frame = 8000
    b_bar.setValue(0)

    
    sub_ch = []
    sum_ch1 = [0]*channels
    ch = channels
    ## assigning subchannels - sub_ch
    for x in range(channels+1):
        sub_ch_x = round(x*(1159/(channels)))
        sub_ch.append(sub_ch_x)
    print(sub_ch)
    print("ROI param ==> ",ROI_x, ROI_y, ROI_h, ROI_w)
    print("ROT param =====> ", ROT_x, ROT_y, ROT_h, ROT_w)
    
    ## get angle properties
    if angle == 0:
        x2 = width
        y2 = height
    elif angle !=0:
        w = width
        h = height
        (cX, cY) = (width // 2, height // 2)
        M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        # compute the new bounding dimensions of the image
        nW = int((h * sin) + (w * cos))
        nH = int((h * cos) + (w * sin))
        # adjust the rotation matrix to take into account translation
        M[0, 2] += (nW / 2) - cX
        M[1, 2] += (nH / 2) - cY

        
##        rad = math.radians(abs(angle))
##        cos = math.cos(rad)
##        sin = math.sin(rad)
##        y1 = height
##        x1 = width
##        image_center = (x1 / 2, y1 / 2)
##        y2 = (y1 * cos) + (x1 * sin)
##        x2 = (x1 * cos) + (y1 * sin)
##        rot_x = int(abs(x2-x1))
##        rot_y = int(abs(x1*sin))
##        rot_width = int(x1 - abs(x2-x1))
##        rot_height = int((y1 * cos) - (x1 * sin))
##        M = cv2.getRotationMatrix2D((image_center),angle,1)
##        M[0, 2] += ((x2 / 2) - image_center[0])
##        M[1, 2] += ((y2 / 2) - image_center[1])

        # center
##    (h, w) = image.shape[:2]
##    (y1, x1) = image.shape[:2]
##    # grab the rotation matrix (applying the negative of the
##    # angle to rotate clockwise), then grab the sine and cosine
##    # (i.e., the rotation components of the matrix)
##    M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
##    cos = np.abs(M[0, 0])
##    sin = np.abs(M[0, 1])
##    # compute the new bounding dimensions of the image
##    nW = int((h * sin) + (w * cos))
##    nH = int((h * cos) + (w * sin))
##    # adjust the rotation matrix to take into account translation
##    M[0, 2] += (nW / 2) - cX
##    M[1, 2] += (nH / 2) - cY
##    # perform the actual rotation and return the image
##    rotated = cv2.warpAffine(image, M, (nW, nH))
##    # crop image to the bounded image
##    x2 = (x1*cos) + (y1*sin)
##    rot_width = int(x1 - abs(x2-x1))
##    rot_height = int((y1 * cos) - (x1 * sin))
##    x = int(abs(x2-x1))
##    y = int(abs(x1*sin))
##    bound = rotated[y:y+rot_height, x:x+rot_width]

    
##    dots_coord = center_coord
##    ROI_w = int(pix_per_ch * channels)
##    ROI_h = int(ROI_w*110/840)
##    ROI_x = int(center_coord[0]-762)
##    ROI_y = int(center_coord[1]-50)
##    ROI_image = image[ROI_y:ROI_y+ROI_h, ROI_x:ROI_x+ROI_w]

    if ROI_w == 0 :
        print("[ERROR] on image identification. Record whole video")
        ROI_x, ROI_y, ROI_w, ROI_h = 0, 500, width, 500
        ROT_x, ROT_y , ROT_w, ROT_h = 0,0,width,height
        match_error = 1
        print("NEW  ROI param ==> ",ROI_x, ROI_y, ROI_h, ROI_w)
        print("NEW  ROT param =====> ", ROT_x, ROT_y, ROT_h, ROT_w)
    ##ROT_x, ROT_y , ROT_w, ROT_h = 0,0,width,height
    ##ROI_x, ROI_y , ROI_w, ROI_h = 0,0,0,0
        
    ## Save Data Path
    data_save = dataDir
##    ROI_h = 400
    ## NEED to set the height and width
    ## AVI, MJPG, MP4
    if video_format == 'AVI':
        suffix = '.avi'
        out = cv2.VideoWriter((data_save+"\\"+file_preffix+suffix), 0x00000000, 25.0, (ROI_w, ROI_h), isColor=False)
    elif video_format == 'MJPG':
        suffix = '.avi'
        out = cv2.VideoWriter((data_save+"\\"+file_preffix+suffix), cv2.VideoWriter_fourcc(*'MJPG'), 25.0, (ROI_w, ROI_h), isColor=False)
    elif video_format == 'MP4':
        suffix = '.mp4'
        out = cv2.VideoWriter((data_save+"\\"+file_preffix+suffix), 0x00000022, 25.0, (ROI_w, ROI_h), isColor=False)
    else:
        suffix = '.avi'
        out = cv2.VideoWriter((data_save+"\\"+file_preffix+suffix), cv2.VideoWriter_fourcc(*'MJPG'), 25.0, (ROI_w, ROI_h), isColor=False)
    #####

    
    cam.BeginAcquisition()
    start_time = time.time()
    while (no_cancel and count <= max_frame):
        count +=1
        image_primary = cam.GetNextImage()
        frame = np.array(image_primary.GetNDArray())

        if angle != 0:
            frame = cv2.warpAffine(frame,M,(nW,nH))
            frame = frame[ROT_y:ROT_y+ROT_h, ROT_x:ROT_x+ROT_w]
            frame_crop = frame[ROI_y:(ROI_y+ROI_h) , ROI_x:(ROI_x+ROI_w)]  #img[y:y+h, x:x+w]
        if angle == 0:
            frame_crop = frame[ROI_y:(ROI_y+ROI_h) , ROI_x:(ROI_x+ROI_w)]
        
        out.write(frame_crop)
        frame_mask = mask.apply(frame_crop)
        frame_mask = cv2.medianBlur(frame_mask,3)
        frame_mask = cv2.threshold(frame_mask, 125, 255, cv2.THRESH_BINARY)[1]
        
        if process_data == 1:
            # find contours
            contours, hierarcy = cv2.findContours(frame_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            # list of all the coordinates (tuples) of each cell
            coord_list = []
            # to find the coordinates of the cells
            for i in range(len(contours)):
                avg = np.mean(contours[i], axis = 0)
                coord = (int(avg[0][0]), int(avg[0][1])) ##Coord is (y,x)
##              if Show == 1:
##                  cv2.circle(frame_count, coord, 10, (255, 0, 255), 1)
                ch_pos = int(math.floor((coord[0])/sub_ch[1]))
                try:
                    sum_ch1[ch_pos] += 1
                except:
                    error += 1

        if FPS < 26 or (count%50 == 0):
            cv2.imshow("test",frame_crop)
            cv2.waitKey(1)
##        image_primary.Release()
        b_bar.setValue(count)

    #set an array of sub channel dimension
    print('[RESULTS] for RUN is ', sum_ch1)
    process_file = data_save+"\\"+file_preffix+".csv"
    print(data_save)
    ## Save Data to CSV
    df = pd.DataFrame(data=sum_ch1, columns = ["Expt 1"])
    print(df)
    try:
        df.to_csv(process_file, index=False)
        print('File Saved') 
    except:
        print('Failed to Save File')    


    end_time = time.time()
    out.release    
    cam.EndAcquisition()   
    cv2.destroyAllWindows()
    camera_reset()
    no_cancel = False
    print("Total processed FPS = ", count/(end_time - start_time))
    print(run_assay1, run_assay2)

    if run_assay1 == 1:
        run_assay1 = 2 ## execute next sequence of assay
        return
    if run_assay1 == 2:
        run_assay1 = 3 ## execute next sequence of assay
        return
    if run_assay1 == 3:
        run_assay1 = 0 ## Reset
        return

    if run_assay2 == 1:
        run_assay2 = 2 ## execute next sequence of assay
        return
    if run_assay2 == 2:
        run_assay2 = 3 ## execute next sequence of assay
        return
    if run_assay2 == 3:
        run_assay2 = 0 ## Reset
        return
    return

### FUNCTION ===> Record video
def record():
    global no_cancel, save_mode, cwDir
    global got_camera, FPS, angle, num_cameras, cam
    global ROI_x, ROI_y, ROI_h, ROI_w, width, height, channels
    global ROT_x, ROT_y, ROT_h, ROT_w
    global rot_x, rot_y, rot_width, rot_height
    global feature_matching, current_step


    local_angle = (angle+1)
    
    # [GET] camera list
    cam_list = system.GetCameras()
    print(cam_list)
    num_cameras = cam_list.GetSize()
    print('num cams',num_cameras)
    camera_start()
    if got_camera == True and num_cameras == 0:
        print('trouble')
        cprint('The camera was disconnected')
        got_camera = False
        return

    if got_camera == False:
        cprint('No Detectable Camera')
        return


    print(ROT_x, ROT_y, ROT_w, ROT_h)
    
    btn4.setEnabled(False)
    btn1.setEnabled(False)
    no_cancel = True
    FPS = int(cam_fps_value.text())
    print(FPS)    
    cprint('Camera View BEGIN')
    
##    if (capture_width + capture_height) > 0:
##        c_width = capture_width
##        c_height = capture_height
##    else:
    c_width = int(cam_w_value.text())
    c_height = int(cam_h_value.text())
    
    print(c_width,c_height)
    camera_properties(c_width , c_height, FPS)
    print('Initial FPS view = ',cam.AcquisitionFrameRate.GetValue())
    cam.BeginAcquisition()
    count = 0
    a_bar.setMaximum(int(cam_frame_value.text()))
    ch = int(cam_ch_value.text())
    sub_ch = []
    
    file_stem = file_value.text()
    cur_dir = Path(cwDir)
    cur_file = cur_dir/file_stem
##    suffix = '.avi'
##    out = cv2.VideoWriter(str(Path(str(cur_file)+suffix)), cv2.VideoWriter_fourcc(*'MJPG'), 25.0, (c_width, c_height), isColor=False)


    if (local_angle != angle):
        rad = math.radians(abs(angle))
        cos = math.cos(rad)
        sin = math.sin(rad)
        
        #original frame capture dimensions
##        y1,x1 = frame.shape
        y1 = c_height
        x1 = c_width
        image_center = (x1 / 2, y1 / 2)
        
        #rotated array dimensions
        y2 = (y1 * cos) + (x1 * sin)
        x2 = (x1 * cos) + (y1 * sin)
        ROT_x = int(abs(x2-x1))
        ROT_y = int(abs(x1*sin))
        ROT_w = int(x1 - abs(x2-x1))
        ROT_h = int((y1 * cos) - (x1 * sin))

        
        #Maxtrix transformation
        M = cv2.getRotationMatrix2D((image_center),angle,1)
        M[0, 2] += ((x2 / 2) - image_center[0])
        M[1, 2] += ((y2 / 2) - image_center[1])
        
                  
        print('angle has changed')
        local_angle = angle

    ## assigning subchannels - sub_ch
    for x in range(ch+1):
        sub_ch_x = round(x*(ROT_w/(ch)))
        sub_ch.append(sub_ch_x)
    
    if file_type_menu.currentText() == 'AVI':
        suffix = '.avi'
        out = cv2.VideoWriter(str(Path(str(cur_file)+suffix)), 0x00000000, 25.0, (ROT_w, ROT_h), isColor=False)

        ##cv2.VideoWriter(path of saved file location, fourcc codec(MJPG, DIVX ,H264), FPS, height and width of file, colour)
    elif file_type_menu.currentText() == 'MJPG':
        suffix = '.avi'
        out = cv2.VideoWriter(str(Path(str(cur_file)+suffix)), cv2.VideoWriter_fourcc(*'MJPG'), 25.0, (ROT_w, ROT_h), isColor=False)
    elif file_type_menu.currentText() == 'MP4':
        suffix = '.mp4'
        out = cv2.VideoWriter(str(Path(str(cur_file)+suffix)), 0x00000022, 25.0, (ROT_w, ROT_h), isColor=False)
    else:
        suffix = '.avi'
        out = cv2.VideoWriter(str(Path(str(cur_file)+suffix)), cv2.VideoWriter_fourcc(*'MJPG'), 25.0, (ROT_w, ROT_h), isColor=False)
    filename = Path(str(cur_file)+suffix)
    #cprint('The saved file name = '+str(filename))
    
    start_time = time.time()
    a_view_label.setText("Recording in progress...")
    
    while (no_cancel and count <= int(cam_frame_value.text())):
        count += 1
        image_primary = cam.GetNextImage()
        frame = np.array(image_primary.GetNDArray())

        if angle != 0:    
            frame = cv2.warpAffine(frame,M,(int(x2),int(y2)))  
            frame_crop = frame[ROT_y:(ROT_y+ROT_h) , ROT_x:(ROT_x+ROT_w)]  #img[y:y+h, x:x+w]

        if angle == 0:
            frame_crop = frame
        out.write(frame_crop)
            

        image_primary.Release()
        a_bar.setValue(count)

    end_time = time.time()
    out.release    
    cam.EndAcquisition()   
    cv2.destroyAllWindows()
    fps = count/(end_time - start_time) 
    print('FPS captured is =' , fps)
    a_view_label.setText("Recording done")
    view_mode = 0
    camera_reset()
    no_cancel = False
    btn1.setEnabled(True)
    btn4.setEnabled(True)     
    
    return

### FUNCTION ===> Start Dialog
def showdialog():
    global q_field5, q_field4, q_field3, q_field2, chip_x, chip_y
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
    q_label3b = Label('-  KKH1  -')
    q_label3c = Label('-')
    q_label4 = Label('User:')
    q_field1 = LineEdit(present); q_field1.setFixedSize(400,25)
    
    q_field2 = LineEdit(''); q_field2.setFixedSize(400,25)
    q_field3 = LineEdit(''); q_field3.setFixedSize(75,25); q_field3.setMaxLength(4)
    q_field3b = LineEdit(''); q_field3b.setFixedSize(75,25); q_field3b.setMaxLength(4)
    q_field3c = LineEdit(''); q_field3c.setFixedSize(75,25); q_field3c.setMaxLength(4)
    q_field4 = LineEdit(user); q_field4.setFixedSize(400,25)
    q_field5 = LineEdit(cwDir); q_field5.setFixedSize(400,25)
    
    ##Layouts
    d_layout =  QGridLayout()
    d_layout.addWidget(q_label1,    0,2,1,1)
    d_layout.addWidget(q_field1,    0,3,1,5)
    d_layout.addWidget(q_label2,    1,2,1,1)
    d_layout.addWidget(q_field2,    1,3,1,5)
    d_layout.addWidget(q_label3,    2,2,1,1)
    d_layout.addWidget(q_label3b,   2,4,1,1); q_label3b.setFixedSize(120,25); q_label3b.setAlignment(Qt.AlignCenter)
    d_layout.addWidget(q_label3c,   2,6,1,1); q_label3c.setFixedSize(30,25); q_label3c.setAlignment(Qt.AlignCenter)
    d_layout.addWidget(q_field3,    2,3,1,1)
    d_layout.addWidget(q_field3b,   2,5,1,1)
    d_layout.addWidget(q_field3c,   2,7,1,1)
    d_layout.addWidget(q_label4,    3,2,1,1)
    d_layout.addWidget(q_field4,    3,3,1,5)
    d_layout.addWidget(q_field5,    4,3,1,5)
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

    if d.exec() == d.Accepted:
        print('Save initiated')
        begin_b.setParent(None) ## to remove button from layout
        basicLayout.addWidget(basic_w_run) ## Initiate the basic run function
        try:
            chip_x = int(q_field3b.text())*10
            chip_y = int(q_field3c.text())
        except:
            print("Error keying chip x and y coordinates")
            chip_x = 0
            chip_y = 0
        save_settings()
##        basic_w.setLayout(basicLayout_run)
##        layout.setCurrentIndex(1)
        return q_field2.text(), q_field3.text(), q_field4.text()
    else: print('Cancelled Save')
    return 

### FUNCTION ===> Show Msg to confirm the entries
def showMsg(msg = ""):
    msgBox = QMessageBox()
    msgBox.setIcon(QMessageBox.Information)
    msgBox.setText(msg)
    msgBox.setWindowTitle("User Action Required")
    msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
##    msgBox.buttonClicked.connect(msgButtonClick) ## add function here
    returnValue = msgBox.exec()
    if returnValue == QMessageBox.Ok:
        print('OK clicked')
        return 1
    if returnValue == QMessageBox.Cancel:
        print('Cancel clicked')
        return 0
    
### FUNCTION ===> Save Settings
def save_settings():
    global dataDir, cwDir, q_field5, user, chip_x, chip_y, data_path
    global q_field4, q_field3, q_field2, multiple_run, sequence
##    print( q_field2.text(), q_field3.text(), q_field4.text())
    date = year + ' ' + month + ' ' + day
    now_time = hour + ' ' + minute
    ## set the directories for settings and Data
    sav_dir = os.path.realpath(q_field5.text())
    settings_dir = cwDir + '\\' + 'settings' + '\\'
##    data_dir = dataDir
##    folder_dir = year + month + day + '_'+q_field2.text()+'_'+str(multiple_run) + '\\'
    ## Data Saves
    dataDir = data_path + year+month+day+"_"+hour+minute + "_" + q_field2.text() + "\\"
    print(dataDir, q_field2.text())
    if not os.path.exists(settings_dir):
        os.makedirs(settings_dir)
    if not os.path.exists(dataDir):
        os.makedirs(dataDir)
        
    cwd = os.getcwd()
    user = q_field4.text()
    log_setting=[]
    log_setting_name = ['Date-Time', 'System', 'Sample', 'Chip', 'User', 'Data DIR']
    log_setting_value= [date + '-' + now_time,
                        __license__,
                        q_field2.text(),
                        (q_field3.text() + "-KKH1-"+str(int(chip_x/10))+"-"+str(chip_y)), #unique to KKH1       
                        user,
                        str(sav_dir)]

    log_setting.append(log_setting_name)
    log_setting.append(log_setting_value)
    print(log_setting)
    
    try:
        setting_df = pd.DataFrame(log_setting)
        setting_df.to_csv(str(cwd) + '\\' + 'settings' + '\\' + 'settings.csv')
        setting_df.to_csv(dataDir + year+month+day+"_settings.csv")
        print('Settings Saved')
    except:
        
        print('ERROR on saving settings')
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
    global run_step, current_step, step_instructions, count, no_cancel, count2, prime_count, wash_count, b_dim
    global p_count, run_assay1, run_assay2, cur_checkpoint, error_code
##    global ROT_x, ROT_y , ROT_w, ROT_h
##    global ROI_x, ROI_y , ROI_w, ROI_h
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
                return
            ### =======>> STEP2
            if current_step == 2:
                label_view1.setPixmap(QPixmap("Images/step2.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                resultMsg = showMsg("[Ready to Prime?] Please check the tubing caps")
                if resultMsg == 1:
                    count = prime_count
                    timer.start(1000)       ## refreshed 1000ms
                    timer.timeout.connect(primechip)
                return
            ### =======>> STEP3
            if current_step == 3:
                try:
                    timer.disconnect()
                    if count < (prime_count-1) and count > 0:
                        resultMsg = showMsg("Priming Step Not Complete! Release Pressure?")
                except:
                    primeStep = showMsg("Priming Step Not Complete!")
##                if abs(pressure()) > 30: release_pressure()
                label3.setText(step_instructions[x-1])
                label_view1.setPixmap(QPixmap("Images/step3.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                return        
            ### =======>> STEP4
            if current_step == 4:
                label_view1.setPixmap(QPixmap("Images/step4.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                resultMsg = showMsg("[Ready to Wash Chip?] Please load PBS Vials")
                if resultMsg == 1:
                    count2 = wash_count
                    timer2.start(1000)       ## refreshed 1000ms
                    timer2.timeout.connect(washchip)
                return    
            ### =======>> STEP5
            if current_step == 5:
                try:
                    timer2.disconnect()
                    if count2 < (wash_count-1) and count2 > 0:
                        resultMsg = showMsg("Wash Step Not Complete!")
                except:
                    washStep = showMsg("Wash Step Not Complete!")
                label3.setText(step_instructions[x-1])
##                if abs(pressure()) > 30: release_pressure()
                label_view1.setPixmap(QPixmap("Images/step5.jpg").scaled(1850, b_dim.height(),
                                                                         Qt.KeepAspectRatio, Qt.FastTransformation))
                btn_wash.show()
                ## USER input Button hide
                PBSwash_btn.show()
                ROIyes_btn.hide();ROIno_btn.hide()
                return    
            ### =======>> STEP6
            if current_step == 6:
                try:
                    timer3.disconnect()
                    if count3 < (PBS_count-1) and count3 > 0:
                        resultMsg = showMsg("Sample Flush Not Complete!")
                except:
                    resultMsg = showMsg("Sample Flush Not Complete!")
                label_view1.setPixmap(QPixmap("Images/step6.jpg").scaled(1850, b_dim.height(),
                                                                         Qt.KeepAspectRatio, Qt.FastTransformation))
                check_checkpoint(4)
                label_view2.show()
                ## Set Auto Roi Counter here
                button_w.show()  
                ## USER input Button hide
                PBSwash_btn.hide()
                ROIyes_btn.show()
                camera_view()
                
                return    
            ### =======>> STEP7
            if current_step == 7:
                print("current step ",current_step)
                label_focus.hide()
                label_view2.hide()
                button_w.hide()
                ROIyes_btn.hide()
                no_cancel = False
                try:
                    cancel()
                except: pass
                check_checkpoint(4)    
                resultMsg = showMsg("[Ready to Run L Assay?] GO!")
                if resultMsg == 1:
                    run_assay1 = 1
                    timer4.start(1000)       ## refreshed 1000ms
                    timer4.timeout.connect(run_DLD_assay)
                
                
                label_view1.setPixmap(QPixmap("Images/step7.jpg").scaled(1850, b_dim.height(),
                                                                         Qt.KeepAspectRatio, Qt.FastTransformation))
                return
            ### =======>> STEP8
            if current_step == 8:
                
                label_view1.setPixmap(QPixmap("Images/step6.jpg").scaled(1850, b_dim.height(),
                                                                         Qt.KeepAspectRatio, Qt.FastTransformation))
                label_view2.show()
                check_checkpoint(6)
                ## Set Auto Roi Counter here
                button_w.show()  
                ## USER input Button hide
                PBSwash_btn.hide()
                ROIyes_btn.show()
                camera_view()
                
                return    
                
            ### =======>> STEP9
            if current_step == 9:
                print("current step ",current_step)
                label_focus.hide()
                label_view2.hide()
                button_w.hide()
                ROIyes_btn.hide()
                no_cancel = False
                try:
                    cancel()
                except: pass
##                auto_roi(6)
                resultMsg = showMsg("[Ready to Run L Assay?] GO!")
                if resultMsg == 1:
                    run_assay2 = 1
                    p_count = 30
                    timer4.start(1000)       ## refreshed 1000ms
                    timer4.timeout.connect(run_DLD_assay2)
                
                
                label_view1.setPixmap(QPixmap("Images/step9.jpg").scaled(1850, b_dim.height(),
                                                                         Qt.KeepAspectRatio, Qt.FastTransformation))
                return
            ### =======>> STEP10
            if current_step == 10:
                label_view1.setPixmap(QPixmap("Images/step10.jpg").scaled(1850, b_dim.height(),
                                                                        Qt.KeepAspectRatio, Qt.FastTransformation))
                return
            if current_step > 10 or current_step < 1 :
##                label_view2.hide()
                button_w.hide()
                label_view1.setPixmap(QPixmap("Images/background.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                return
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
    global run_step, current_step, step_instructions, count, count2, prime_count, wash_count
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
##            if current_step == 1:
##                print("hello")
##                label3.setText(step_instructions[x-1])
##                label_view1.setPixmap(QPixmap("Images/step1.jpg").scaled(1850, b_dim.height(),
##                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
            ### =======>> STEP2
            if current_step == 2:
                label_view1.setPixmap(QPixmap("Images/step2.jpg").scaled(1850, b_dim.height(),
                                                                               Qt.KeepAspectRatio, Qt.FastTransformation))
                resultMsg = showMsg("[Ready to Prime?] Please check the tubing caps")
                if resultMsg == 1: ### start priming procedure
                    count = prime_count     ## 600 S
                    timer.start(1000)       ## refreshed 1000ms
                    timer.timeout.connect(primechip) ### start priming procedure "coundown"
                    
                ### =======>> STEP3
            if current_step == 3:
                try:
                    timer2.disconnect()
                except: pass
                label3.setText(step_instructions[x-1])
                label_view1.setPixmap(QPixmap("Images/step3.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                ### =======>> STEP4
            if current_step == 4:
                btn_wash.hide()
                label_view1.setPixmap(QPixmap("Images/step3.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                count2 = wash_count         ## 300 s
                timer2.start(1000)       ## refreshed 1000ms
                timer2.timeout.connect(washchip)
                
                ### =======>> STEP5
            if current_step == 5:
                button_w.hide()
##                cancel()
                label_view1.setPixmap(QPixmap("Images/step4.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))
                btn_wash.show()
                
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
            try:
                timer.disconnect()
            except: pass
            print(current_step, "here we begin")
            bar.setValue(current_step)
            bar.setFormat(str(bar.value())+'/'+'10'+' Complete')
            label3.setText(step_instructions[x-1])
            label_view1.setPixmap(QPixmap("Images/step1.jpg").scaled(1850, b_dim.height(),
                                                                           Qt.KeepAspectRatio, Qt.FastTransformation))

##            label_view1.setPixmap(QPixmap("Images/background2.jpg").scaled(1850,
##                                                                           b_dim.height()*3/4,
##                                                                           Qt.KeepAspectRatio,
##                                                                           Qt.FastTransformation))
            current_step = current_step - 0
    return 

def check_checkpoint(limit):
    global cur_checkpoint, error_code
    if cur_checkpoint == limit and error_code < limit+1 and error_code!= 0:
        auto_roi(limit)
    return

### FUNCTION ===> timer
def primechip():
    global count, prime_count
    prime_pressure = 850
            
    if count < 0:
        label3.setText("Chip Prime Complete")
        return
    
    if count == 0:
        release_pressure()
            
    if count == prime_count-1:
        pump2pressure(prime_pressure)
        
    if count%5 == 0 and count <= prime_count-20:
        try:
            clear_signal()
            cur_pressure = pressure()
            print(cur_pressure)
            if cur_pressure < int(0.95*prime_pressure):
                clear_signal()
                pump2pressure(prime_pressure)
        except: pass
    now = datetime.datetime.now()
    label3.setText( 'Time now: %s. End time: %s. Seconds left: %s'%(now.strftime("%H:%M:%S"), (now + datetime.timedelta(seconds=count)).strftime("%H:%M:%S"), count))
    count = count - 1
    return

def washchip():
    global count2, wash_count
    wash_pressure = 850
    if count2 < 0:
        label3.setText("Chip Wash Complete")
        return
    
    if count2 == 0:
        release_pressure()
        
    if count2 == wash_count-1:
        input_pressure(wash_pressure)
        
    if count2%5 == 0 and count2 <= wash_count-20:
        try:
            cur_pressure = pressure()
            print(cur_pressure)
            if cur_pressure < int(0.95*wash_pressure):
                input_pressure(wash_pressure)
        except: pass
        
    now = datetime.datetime.now()
    label3.setText( 'Time now: %s. End time: %s. Seconds left: %s'%(now.strftime("%H:%M:%S"), (now + datetime.timedelta(seconds=count2)).strftime("%H:%M:%S"), count2))
    count2 = count2 - 1
    return

def PBS_wash_clicked():
    global count3, PBS_count
    count3 = PBS_count
    led_pos = LED_in_position()
    timer3.start(1000)       ## refreshed 1000ms
    timer3.timeout.connect(PBS_wash)
    PBSwash_btn.setEnabled(False)


def PBS_wash():
    global count3, PBS_count, cur_checkpoint

    PBS_pressure = -350 ## has to be negative
    
    if count3 < 0:
        label3.setText("PBS Sample Flush Complete")
        return
    
    if count3 == 0:
        release_pressure()
        PBSwash_btn.setEnabled(True)
        
    if count3 == PBS_count-1:
        pump2pressure(PBS_pressure)
        count3 = 12

    ### {START AUTO ROI] ==> during PBS wash
    if count3 == 9:
        try:auto_roi(cur_checkpoint)
        except: pass
        print("Cur Check Point ==> ",cur_checkpoint)
    if count3 == 8:
        try:auto_roi(cur_checkpoint)
        except: pass
        print("Cur Check Point ==> ",cur_checkpoint)
    if count3 == 7:
        try:auto_roi(cur_checkpoint)
        except: pass
        print("Cur Check Point ==> ",cur_checkpoint)
    if count3 == 6:
        try:auto_roi(cur_checkpoint)
        except: pass
        print("Cur Check Point ==> ",cur_checkpoint)
    if count3 == 5:
        try:auto_roi(cur_checkpoint)
        except: pass
        print("Cur Check Point ==> ",cur_checkpoint)
    if count3 == 3:
        try:
            if cur_checkpoint <5:
                auto_roi(cur_checkpoint)
        except: pass
        print("Cur Check Point ==> ",cur_checkpoint)

    if PBS_count > 100 and count3%5 == 0 and count3 <= PBS_count-20:
        try:
            cur_pressure = pressure()
            print(cur_pressure)
            if cur_pressure > int(0.97*PBS_pressure):
                pump2pressure(PBS_pressure)
        except: pass

    now = datetime.datetime.now()
    label3.setText( 'Time now: %s. End time: %s. Seconds left: %s'%(now.strftime("%H:%M:%S"), (now + datetime.timedelta(seconds=count2)).strftime("%H:%M:%S"), count3))
    count3 = count3 - 1
    return 

##def check_sample():
##    move_xy(-11000,0)
##
##def check_O1():
##    move_xy(-8800,0)
##
##def check_O2():
##    move_xy(-4000,0)


def user_input_button():
##    global cur_checkpoint, current_step, error_code, run_assay1, run_assay2
##    global p_count, no_cancel
##
####    print("cur_checkpoint =",cur_checkpoint, "current_step =", current_step, "error_code =",error_code)
####    
######    if cur_checkpoint == 4 and error_code == 4:
######        print("starting test again")
######        error_code = auto_roi(4)
######        print("check the location again")
######        print("cur_checkpoint =",cur_checkpoint, "current_step =", current_step, "error_code =",error_code)
######        return
####    if cur_checkpoint == 5 and error_code == 0:
####        print("starting test2 again")
####        p_count = 50
####        run_assay1 = 1
####        timer.start(1000)
####        timer.timeout.connect(run_DLD_assay)
####        print("run timer")
####        print(p_count)
####        return
    return


def run_DLD_assay():
    global run_assay1, run_assay2, no_cancel, width,height
    global dataDir, p_count, ROT_x, ROT_y , ROT_w, ROT_h, ROI_x, ROI_y , ROI_w, ROI_h
##    cur_pressure = pressure()
    print("p_count = ",p_count)

    ### ===== RUN DLD ASSAY 1 L Shape ===== ###
    # SLOW -50mBar run, wait for 15 secs to equilibrate the flow
    if run_assay1 == 1 and p_count == 30:
        pump2pressure(-50)
        label3.setText("Pump to -50mBar")

    # Once Cells reach outlet, run 15 FPS slow test
    # When complete, will update run_assay1 to 2
    if run_assay1 == 1 and p_count == 24:
        label3.setText("Assay 1 Flow 1")
        save_data(15,"L shape -50mBar 15fps")
        
    # FAST -500mBar run, wait for 20 secs to reach pressure
    if run_assay1 == 2 and p_count == 22:
        pump2pressure(-505)
        label3.setText("Pump to -500mBar")
        
    if run_assay1 == 2 and p_count == 5:
        print("starting new fast test L pillar")
        label3.setText("Assay 1 Flow 2")
        save_data(150,"L shape -500mBar 150fps")
        ROT_x, ROT_y , ROT_w, ROT_h = 0,0,width,height
        ROI_x, ROI_y , ROI_w, ROI_h = 0,0,0,0

    if run_assay1 == 3 and p_count == 4:
        print("AUTO_ROI(5)")
        label3.setText("AutoROI (5)")
        auto_roi(5)

    if run_assay1 == 3 and p_count == 3:
        print("AUTO_ROI(6)")
        label3.setText("AutoROI (6)")
        auto_roi(6)
        
    if run_assay1 == 3 and p_count == 2:
        if cur_checkpoint and error_code ==6:
            print("AUTOFOCUS for nex round")
            label3.setText("AutoROI-Auto focus")
            autofocus()
        
    if run_assay1 == 3 and p_count == 1:
        if cur_checkpoint and error_code ==6:
            print("AUTO_ROI(6)")
            auto_roi(6)
        
    if run_assay1 == 3 and p_count == 0:
        release_pressure()
        timer4.disconnect()
        print("timer4 disconnected")

    p_count = p_count - 1
    return

def run_DLD_assay2():
    global run_assay1, run_assay2, no_cancel
    global dataDir, p_count
##    cur_pressure = pressure()
    print("p_count = ",p_count)
    
    ### ===== RUN DLD ASSAY 2 INV-L shape ===== ###
    # SLOW -50mBar run, wait for 15 secs to equilibrate the flow
    if run_assay2 == 1 and p_count == 30:
        pump2pressure(-50)
        label3.setText("Pump to -50mBar")
        
    # Once Cells reach outlet, run 15 FPS slow test
    # When complete, will update run_assay1 to 2
    if run_assay2 == 1 and p_count == 24:
        label3.setText("Assay 2 Flow 1")
        save_data(15,"INV-L shape -50mBar 15fps")
        run_assay2 = 2
        
    # FAST -500mBar run, wait for 20 secs to reach pressure
    if run_assay2 == 2 and p_count == 22:
        pump2pressure(-505)
        label3.setText("Pump to -500mBar")
        
    if run_assay2 == 2 and p_count == 5:
        print("starting new fast test L pillar")
        label3.setText("Assay 2 Flow 2")
        save_data(150,"INV-L shape -500mBar 150fps")
        
    if run_assay2 == 3 and p_count == 0:
        release_pressure()
        timer4.disconnect()
        print("timer4 disconnected")

    if p_count < 0:
        try:
            timer4.disconnect()
        except: pass
            

    p_count = p_count - 1
    return


    
### FUNCTION ===> Pressure run signals to arduino
def pressure():
    clear_signal()
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
        return True
    else:
        print("Arduino signal read error")
        return False
##    for x in range(int(abs(mbar)/2)):
##        p = read_signal()
##        if p != False:
##            print(p)
##            return p
##    return p

def input_pressure(mbar):
    sent, read = run_signal("input_pressure")
    p = False
    if sent == read:
        send_signal(str(mbar))
        return True
    else:
        print("Arduino signal read error")
        return False
##    for x in range(int(abs(mbar)/2)):
##        p = read_signal()
##        if p != False:
##            print(p)
##            return p
##    return p

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
##    if int(r) == 1:
##        return True

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

def move_xy_pix(xpix,ypix):
    global ystep_per_pix, xstep_per_pix, y_freeplay, x_freeplay
    x = int(xstep_per_pix*xpix)
    y = int(ystep_per_pix*ypix)
    sent, read = run_signal("move_xy")
    if sent == read:
        send_signal(str(x)+","+str(y))
        for x in range(50):
            time.sleep(0.1)
            m = read_signal()
            if m != False:
                return 1
    else: return 0
    
### IMAGE FUNCTION ===> Autofocus
def autofocus():
    global cam, no_cancel, got_camera
##    if got_camera == False:
##        cprint('No Detectable Camera')
##        return

    if no_cancel == True: no_cancel = False
    
    count_f = 0       #count the frames
    font = cv2.FONT_HERSHEY_SIMPLEX
    focus_values = []
    focus = 0
    f_thresh = 0.97
    f_value = 0
    show_coord = 1
    z_reach = 0
    z_range = 1000
    move_z(-int(z_range/2))
    clear_signal()
    cam.AcquisitionFrameRateEnable.SetValue(True)
    cam.AcquisitionFrameRate.SetValue(25)
    cam.BeginAcquisition()
    send_signal("move_z")
    send_signal(str(z_range))
    ##clear_signal()
    start = time.time()
    print("start")
    while(z_reach != 'end' and not(cv2.waitKey(1) & 0xFF == ord('q'))):
        
        image = cam.GetNextImage()
        pic = np.array(image.GetNDArray())
##        pic = pic[y1:y2, x1:x2]

        # Laplacian Edge Detection
        laplacian = cv2.Laplacian(pic,2,ksize = 5)
        lap_sum = round(np.sum(laplacian),-5)

        #cv2.putText(pic, str(lap_sum), (100, 50), font, 1, (0, 255, 0), 1, cv2.LINE_AA)
        if show_coord == 1 and count_f%25 == 0:
            try:
                z_reach = arduino.readline()[:-2]
                z_reach = z_reach.decode('UTF-8')
                if z_reach == "end":
                    print("z scan ended")
                    cam.EndAcquisition()
                    break
            except:
                cprint("error here")
                pass

        count_f += 1
        focus_values.append(lap_sum)
##        cv2.imshow('pic',pic)
    
    ## Analyse the plots
    f_max = max(focus_values)
    print("max focus value ==> ", f_max)
    count_f = 0
    focus_values2 = []

##    print(lap_sum + "2")
    ## run thru the setup
    clear_signal()
    run_signal("z_down")
    cam.BeginAcquisition()
    while(not(cv2.waitKey(1) & 0xFF == ord('q'))):
        image = cam.GetNextImage()
        pic = np.array(image.GetNDArray())

        # Laplacian Edge Detection
        laplacian = cv2.Laplacian(pic,2,ksize = 5)
        lap_sum = round(np.sum(laplacian),-5)

        cv2.putText(pic, str(lap_sum), (100, 50), font, 1, (0, 255, 0), 1, cv2.LINE_AA)

        if count_f > 250 or lap_sum >= f_thresh*f_max:
            send_signal("s") ##Stop Signal
            print(lap_sum)
            break
        count_f += 1
        focus_values2.append(lap_sum)
##        cv2.imshow('pic',pic)
    end = time.time()
    cprint("Focus Max = " + str(f_max) + " Focus Value = " + str(lap_sum))
    cprint("Autofocus time taken = " + str(end-start)) 
      
    image.Release()
##    cv2.destroyAllWindows()
    cam.EndAcquisition()
    clear_signal()
    z_pos = int(z_position())
    if z_pos < -1800:
        move_z(-z_pos)
        cprint("---->Autofocus Fail")
    deactivate()
    cancel()
##    camera_view()
    return

### IMAGE FUNCTION ===> Check if LED light is in position
def LED_in_position():
    img = grab_image()
    if np.sum(img) < 20000000:
        cprint("LED Cover Not Closed or LED light blocked")
        print("[ERROR 90] LED Cover Not Closed or LED light blocked")
        return 0
    elif np.sum(img)> 20000000:
        print("LED Cover is closed")
        return 1
    else: return 0

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

### IMAGE FUNCTION ===> find angle Version 2
def find_angles(image, roi):
    ### ==> Find Angle to Rotate in Video
    dup_img = image.copy()
    angle_img = dup_img
    # ML for histogram object
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    ##angle_img = clahe.apply(angle_img)
    # Select ROI
    sel = roi
    x1 = int(sel[0])
    x2 = int(sel[0] + sel[2])
    y1 = int(sel[1])
    y2 = int(sel[1] + sel[3])
    angle_crop = angle_img[y1:y2, x1:x2]
    show(angle_crop)
    # Threshold
    ret,angle_thresh = cv2.threshold(angle_crop,120,255,cv2.THRESH_BINARY_INV)
    show(angle_thresh)
    ## Apply edge detection method on the image 
    ##edges = cv2.Canny(angle_thresh,50,150,apertureSize = 5)
    ##show(edges)
    minLineLength = 10
    maxLineGap = 10
    # detect lines in the image using hough lines technique
    lines = cv2.HoughLinesP(angle_thresh,1,np.pi/180*180,10,minLineLength,maxLineGap)
    # Perform Hough Transformation to detect lines
    tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 360, endpoint=False)
    hspace, angles, distances = hough_line(angle_thresh, theta=tested_angles)
    # Find angle
    coord, angle,dist=[],[],[]
    for space, a , distance in zip(*hough_line_peaks(hspace, angles, distances)):
        coord.append(space)
        angle.append(a)
        dist.append(distance)
    # Obtain ANGLES for each line
    ave_angle = sum(angle)/len(angle)
    ave_angle = ave_angle*180/np.pi
    angles = [a*180/np.pi for a in angle]
    # Compute difference between the two lines
    angle_difference = np.max(angles) - np.min(angles)
    print(ave_angle, angle_difference)

    show_img = dup_img[y1:y2, x1:x2]
    # iterate over the output lines and draw them
    for line in lines:
        for x1, y1, x2, y2 in line:
            cv2.line(show_img, (x1, y1), (x2, y2), (20, 220, 20), 1)
    cv2.destroyAllWindows()
    show(show_img)
    return angles, angle_difference

### IMAGE FUNCTION ===> Rotate Image
def rotate_bound(image, angle):
    global ROT_x, ROT_y, ROT_w, ROT_h
    # grab the dimensions of the image and then determine the
    # center
    (h, w) = image.shape[:2]
    (y1, x1) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # grab the rotation matrix (applying the negative of the
    # angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    M = cv2.getRotationMatrix2D((cX, cY), angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))
    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY
    # perform the actual rotation and return the image
    rotated = cv2.warpAffine(image, M, (nW, nH))
    # crop image to the bounded image
    x2 = (x1*cos) + (y1*sin)
    ROT_w = int(x1 - abs(x2-x1))
    ROT_h = int((y1 * cos) - (x1 * sin))
    ROT_x = int(abs(x2-x1))
    ROT_y = int(abs(x1*sin))
    bound = rotated[ROT_y:ROT_y+ROT_h, ROT_x:ROT_x+ROT_w]    # copy(int x, int y, int width, int height)   
    return bound

def center_image(current_y, current_x, factor = 1.5):
    global ystep_per_pix, xstep_per_pix, y_add_freeplay, x_add_freeplay, y_freeplay, x_freeplay
    global width, height
    print("Factor = ",factor)
##    ystep_per_pix      #ysteps per FULL pix res
##    xstep_per_pix      #xsteps per FULL pix res
    move_y = 0
    move_x = 0
##    y_freeplay = 50
##    x_freeplay = 30

    ##IF label is on
##    center = [int(a_view_label.geometry().width()/2),
##              int(a_view_label.geometry().height()/2)]

    ## for grabbed image
    center = [int(width/2), int(height/2)]
    
    offset_y = -current_y + center[0]
    offset_x = current_x - center[1]
    cprint(str(offset_y)+","+str(offset_x)+" == offset")

    # 1 = no free play, -1 = add free play
    if y_add_freeplay == 1 and offset_y < 0:
        y_add_freeplay = -1
        move_y = move_y - y_freeplay
        cprint("y free play added")
    elif y_add_freeplay == -1 and offset_y > 0:
        y_add_freeplay = 1
        move_y = move_y + y_freeplay
        cprint("y free play added")
    if x_add_freeplay == 1 and offset_x < 0:
        x_add_freeplay = -1
        move_x = move_x - x_freeplay
        cprint("x free play added")
    elif x_add_freeplay == -1 and offset_x > 0:
        x_add_freeplay = 1
        move_x = move_x + x_freeplay
        cprint("x free play added")

    move_y = move_y + int(offset_y*ystep_per_pix*factor)
    move_x = move_x + int(offset_x*xstep_per_pix*factor)

    cprint("move motor by steps : " + str(move_x)+","+str(move_y))
    print("move motor by steps : " + str(move_x)+","+str(move_y))
    ##move motor
    activate()
    move_xy(move_x, move_y)
    return

### IMAGE FUNCTION ===> Histogram
def feature_match(template_file = "4 dots.png", image_in = 0): #center big dot
    global cwDir, cam, no_cancel, feature_matching
    global width, height, angle

##    if feature_matching == 1:
##        feature_matching = 0
##        cprint("feature match = 0")
##        cam.AcquisitionFrameRate.SetValue(25)
##    else:
##        feature_matching = 1
##        cprint("feature match = 1")
##        cam.AcquisitionFrameRate.SetValue(4)
    
    print(cwDir)
    try:
        marker_file = cwDir + "\\Images\\template\\" + template_file
        print(marker_file)
    except:
##        marker_file = cwDir + "\\Images\\template\\" + "4 dots.png"
        print("Error for marker_file")
        return
    if no_cancel == True:
        cprint("camera in use")
        return

    count=0
    template = cv2.imread(marker_file, cv2.IMREAD_GRAYSCALE)
    try:
        w, h = template.shape[::-1]
    except:
        print("[ERROR in Template File]")
        return 0,0,0
    ret,template = cv2.threshold(template,125,255,cv2.THRESH_BINARY_INV)
    ## ADD ==> 'cv2.TM_CCORR',
    methods = ['cv2.TM_CCOEFF','cv2.TM_CCOEFF_NORMED','cv2.TM_CCORR',
               'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']

    
    start = time.time()
    print("start")
    ##Start feature Match
    if not isinstance(image_in, int):
        img_original = image_in
        print("rotated image used")
    else:
        try:
            cam.EndAcquisition()
        except: pass
        cam.BeginAcquisition()
        img_original = cam.GetNextImage()
        img_original = np.array(img_original.GetNDArray())

    ret,thresh2 = cv2.threshold(img_original,120,255,cv2.THRESH_BINARY_INV)
    average_loc = []
        
    for i,meth in enumerate(methods):
        method = eval(meth)
        res = cv2.matchTemplate(thresh2,template,method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
        if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
            top_left = min_loc
        else:
            top_left = max_loc
        average_loc.append(top_left)

    loc = {i:average_loc.count(i) for i in average_loc}
    coord = list(loc.keys())
    
    coord_count = list(loc.values())
    print(coord, coord_count)
    if len(coord) <= 3 and ((0,0) not in coord):
        bottom_right = (coord[0][0] + w, coord[0][1] + h)
        cv2.rectangle(img_original,coord[0], bottom_right, 255, 2)
        coord_mid = (round(coord[0][0]+w/2), round(coord[0][1]+h/2))
    else:
        coord_mid = (0,0)
        pass
##            print("There are no matches")
        ## get angle properties
##    if angle !=0:
##        rad = math.radians(abs(angle))
##        cos = math.cos(rad)
##        sin = math.sin(rad)
##        y1 = height
##        x1 = width
##        image_center = (x1 / 2, y1 / 2)
##        y2 = (y1 * cos) + (x1 * sin)
##        x2 = (x1 * cos) + (y1 * sin)
##        rot_x = int(abs(x2-x1))
##        rot_y = int(abs(x1*sin))
##        rot_width = int(x1 - abs(x2-x1))
##        rot_height = int((y1 * cos) - (x1 * sin))
##        M = cv2.getRotationMatrix2D((image_center),angle,1)
##        M[0, 2] += ((x2 / 2) - image_center[0])
##        M[1, 2] += ((y2 / 2) - image_center[1])      
        
    qformat = QImage.Format_Indexed8
    if angle !=0:
        if not isinstance(image_in, int):
            x2 = len(image_in[0])
            y2 = len(image_in)
        x2 = width
        y2 = height
    else:
        x2 = width
        y2 = height
    print(x2,y2)
##        img_original = cv2.warpAffine(img_original,M,(int(x2),int(y2)))
##    img = QImage(img_original, int(x2), int(y2), int(x2), qformat)
    ##img = img.copy(rot_x, rot_y, rot_width, rot_height)    # copy(int x, int y, int width, int height)
##    img = QPixmap.fromImage(img)
##    img = img.scaledToHeight(720) ## scaled smaller by 1.5x
##    a_view_label.setPixmap(img).
    
#### [SET] camera properties (width, height,fps)
##    camera_properties(1440, 1080, 8)
##    cam.AcquisitionFrameRateEnable.SetValue(True)
##    cam.AcquisitionFrameRate.SetValue(4)
##    cam.BeginAcquisition()
##    start = time.time()
##    
##    while(not(cv2.waitKey(1) & 0xFF == ord('q'))):    
##        img_original = cam.GetNextImage()
##        img_original = np.array(img_original.GetNDArray())
##        ret,thresh2 = cv2.threshold(img_original,120,255,cv2.THRESH_BINARY_INV)
##        average_loc = []
##        
##        for i,meth in enumerate(methods):
##            method = eval(meth)
##            res = cv2.matchTemplate(thresh2,template,method)
##            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
##            # If the method is TM_SQDIFF or TM_SQDIFF_NORMED, take minimum
##            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
##                top_left = min_loc
##            else:
##                top_left = max_loc
##            average_loc.append(top_left)
##
##        loc = {i:average_loc.count(i) for i in average_loc}
##        coord = list(loc.keys())
##        coord_count = list(loc.values())
##        if len(coord) <= 2 and ((0,0) not in coord):
##            bottom_right = (coord[0][0] + w, coord[0][1] + h)
##            cv2.rectangle(img_original,coord[0], bottom_right, 255, 2)
##            coord_mid = (round(coord[0][0]+w/2), round(coord[0][1]+h/2))
##        else:
##            coord_mid = (0,0)
####            print("There are no matches")
##        cv2.imshow("Match", img_original)
##        count += 1
    end = time.time()

    
    if isinstance(image_in, int): 
        cv2.destroyAllWindows()
        cam.AcquisitionFrameRateEnable.SetValue(True)
        cam.AcquisitionFrameRate.SetValue(25)
        cam.EndAcquisition()

    print("total time taken to process =", (end - start))
    cprint("The Coordinate of Template => " + str(coord_mid[0])+","+str(coord_mid[1]))
    cancel()
    return img_original, coord_mid, max(coord_count)

### IMAGE FUNCTION ===> Auto Roi
def show(image):
    cv2.namedWindow(str(image),cv2.WINDOW_NORMAL)
    cv2.resizeWindow(str(image), int(image.shape[1]), int(image.shape[0]))
    cv2.imshow(str(image), image)
    return

def chip_position():
    global chip_x, chip_y
    coord = input("what is the coord of chip (x,y): ")
    coord = coord.split(",")
    chip_x, chip_y = int(coord[0]),int(coord[1])
    return chip_x, chip_y

### IMAGE FUNCTION ===> Show
def auto_roi(checkpoint = 0):
    global cam, angle, chip_x, chip_y
    global cur_checkpoint, error_code
    global detect_ybuffer, detect_xbuffer, pix_per_ch, channels
    global ROI_w, ROI_h, ROI_x, ROI_y, dots_coord, no_cancel
    ## [CHECK 0] -> Check if Cam is working
    
    if checkpoint == 0:
        if chip_x == 0 or chip_y == 0:
            print("[ERROR 91] Chip XY Coord Error: 0 or non-integer")
##            chip_x, chip_y = chip_position()
            return
##        if not isinstance(chip_x, int) or not isinstance(chip_y, int):
##            print("[ERROR 91] Chip XY Coord Error not integer")
            
        print("The chip coordinates are ", chip_x,",", chip_y)
        activate()
        move_xy(1000,1000)
        home_xy()
        
##        angle = 0 ### impt for the ROI to work
        try:
            camera_start()
            camera_properties(1440, 1080, 25)
            print("[CHECKPOINT 0] Camera functional")
        except:
            try:
                cam.EndAcquisition()
                print("[CHECKPOINT 0] Camera Reset")
            except:
                print("[ERROR 1] Camera unable to connect/stream")
        cur_checkpoint += 1
        return 0

    ## [CHECK 1] -> Goto position (Center Big Dot)
    elif checkpoint == 1:
        # go to the respective coordinates
        # x = define here, y = define here
##        chip_x, chip_y = 10550, 2200
        activate()
        move_xy(chip_x, chip_y)
        try:
            autofocus()
        except:
            print("[ERROR 2] Autofocus error")
            error_code = 2
            time.sleep(1)
            send_signal("s")
            time.sleep(1)
            clear_signal()
            move_z(-int(z_position()))
            showMsg("[Autofocus Error] => Manual Focus in next Step")
            show(grab_image())
            return 2
        
        cur_checkpoint += 1    
        # feature matching
        show(grab_image())
        return 0
        
    ## [CHECK 2] -> Moving to 1st ROI region
    elif checkpoint == 2:
        activate()
        try:
            image,center_coord,center_coord_no = feature_match("center big dot.png")
            print("the center coord and number is",center_coord, center_coord_no)
            if center_coord_no < 5:
                print("[ERROR 3] Center Feature Match Error")
                error_code = 3
                showMsg("[Center Feature Detection Error1] => Check Manual Matching")
                return 3
            else:
                print("Success identifying 'Center Big Dot'")
            show(image)
        except:
            print("[ERROR 3] Exception Center Feature Match Error")
            showMsg("[Center Feature Detection Error2] => Check Manual Matching")
            error_code = 3
            return 3
        
        ## moving to ROI region
        center_image(center_coord[1], center_coord[0], 0.8)
        ## check if image is center        
        move_xy(0,300)
        cur_checkpoint += 1
        show(grab_image())
        return 0
        
    ## [CHECK 3] -> Angle Setting for 1st ROI
    elif checkpoint == 3:
        image = grab_image()
        roi = (500, 500, 350, 500)
        angle_list, angle_diff = find_angles(image, roi)
        angle = np.median(angle_list)
        print("angle is ",angle)
        if abs(angle) > 3:
            print("ERROR of Angle")
            angle = 0            
##        rot_img = rotate_bound(image, angle)
####        while(not(cv2.waitKey(1) & 0xFF == ord('q'))):
##        show(rot_img)
##        cv2.destroyAllWindows()
        cur_checkpoint += 1
        return 0

    ## [CHECK 4] -> Drawing 1st ROI region
    elif checkpoint == 4:
        
        if angle == 0.0:
            image,center_coord,center_coord_no = feature_match("4 dots.png")
        else:
            image = grab_image()
            print("image grabbed")
            rot_img = rotate_bound(image, angle)
            print("image rotated")
            image,center_coord,center_coord_no = feature_match("4 dots.png", rot_img)
        
        print("Center Coord and Number =",center_coord,center_coord_no)
        if center_coord_no >= 5:
            ## Check if the 4 dots or template is within the detection tolerance
            if (center_coord[0] > 775 and center_coord[0] < (775 + detect_ybuffer)) and (center_coord[1] > 250 and center_coord[1] < (250 + detect_xbuffer)):
                print("4 dots have hit on the spot")
                ## draw ROI here
    ##                cv2.rectangle(image,(center_coord[0], bottom_right, 255, 2)
                dots_coord = center_coord
                ROI_w = int(pix_per_ch * channels)
                ROI_h = int(ROI_w*110/840)
                ROI_x = int(center_coord[0]-762)
                ROI_y = int(center_coord[1]-50)
                ROI_image = image[ROI_y:ROI_y+ROI_h, ROI_x:ROI_x+ROI_w]
                show(ROI_image)
    ##        ROI_img = img2[ROI_y:ROI_y+ROI_h, ROI_x:ROI_x+ROI_w]
            
            else:
                print("there is room to shift 4 dots")
                if (center_coord[0] != 0):
                    shift_ycoord = 775 + int(detect_ybuffer/2)
                    move_xy_pix(0, shift_ycoord-center_coord[0])
                if (center_coord[1] != 0) and (center_coord[1] < 300 or center_coord[1] > (250 + detect_xbuffer)):
                    shift_xcoord = 300 + int(detect_xbuffer/2)
                    move_xy_pix(center_coord[1]-shift_xcoord, 0)
                print("[ERROR 4] Unable to move to 4 dots position")
                error_code = 4
                return 4   
        else:
            print("[ERROR 5] Unable to identify 4 dots")
            error_code = 5
            return 5

        cur_checkpoint += 1
        error_code = 0
        return 0
    
    ## [CHECK 5] -> Move to 2nd ROI region
    elif checkpoint == 5:
        #move to right device
        try:
            move_xy_pix(0,-1850)
        except:
            error_code = 5
            return 5
        return 0

    ## [CHECK 6] -> Draw 2nd ROI region
    elif checkpoint == 6:
        #identify the 4 dots
        if angle == 0.0:
            image,center_coord,center_coord_no = feature_match("4 dots.png")
            print("angle =",angle)
        else:
            image = grab_image()
            rot_img = rotate_bound(image, angle)
            print("Rotating image Angle of 2nd ROI")
            image,center_coord,center_coord_no = feature_match("4 dots.png", rot_img)
        print("Center Coord and Number =",center_coord,center_coord_no)
        if center_coord_no >= 5:
            ## Check if the 4 dots or template is within the detection tolerance
            if center_coord[0] > 398 and center_coord[0] < (398 + detect_ybuffer):
                print("4 dots have hit on the spot")
                dots_coord = center_coord
                ## draw ROI here
    ##            cv2.rectangle(image,(center_coord[0], bottom_right, 255, 2)
                ROI_w = int(pix_per_ch * channels)
                ROI_h = int(ROI_w*110/840)
                ROI_x = int(center_coord[0]-397)
                ROI_y = int(center_coord[1]-50)
                ROI_image = image[ROI_y:ROI_y+ROI_h, ROI_x:ROI_x+ROI_w]
                show(ROI_image)
            else:
                print("there is room to shift 4 dots")
                if (center_coord[0] != 0):
                    shift_ycoord = 400 + int(detect_ybuffer/2)
                    move_xy_pix(0, shift_ycoord-center_coord[0])
                print("[ERROR 6] Unable to move to 4 dots position")
                error_code = 6
                return 6 
        else:
            print("[ERROR 7] Insufficient center_coord_no <5 to identify")
            error_code = 7
            return 7
        show(image)
        cur_checkpoint += 1
        error_code = 0
        print("[AUTO_ROI 6] Found")
        return 0
    return 0


### IMAGE FUNCTION ===> Grab image
def grab_image():
    global no_cancel, got_camera, num_cameras, cam
    global width, height

##    no_cancel = True
##    cam_list = system.GetCameras()
##    num_cameras = cam_list.GetSize()
    camera_start()
    camera_reset()
    try:
        cam.EndAcquisition()
    except: pass
    if got_camera == True and num_cameras == 0:
        print('trouble')
        got_camera = False
        return
    
    if got_camera == False:
        cprint('No Detectable Camera')    
    print('Initial FPS view2 = ',cam.AcquisitionFrameRate.GetValue())
    try:
        camera_properties(width, height, 25)
    except:
        pass
    cam.BeginAcquisition()
    print("Initial")
    image_primary = cam.GetNextImage()
    frame = np.array(image_primary.GetNDArray())
    cam.EndAcquisition()
    cancel()
    camera_reset()
    no_cancel = False
    
    return frame   

    
### ************************************ ###
###            Widgets Class             ###
### ************************************ ###
class myLabel(QLabel):
    clicked = QtCore.pyqtSignal()
    global ystep_per_pix, xstep_per_pix
    
    #ystep_per_pix = 0.33939     #ysteps per FULL pix res
    #xstep_per_pix = 0.53579     #xsteps per FULL pix res
    def mouseMoveEvent(self, event):
##        self.setText('coords: ( % d : % d )' % (event.x(), event.y()))
        return
    def mousePressEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            width_y = QMouseEvent.x()
            height_x = QMouseEvent.y()
            center_image(width_y, height_x)
            cprint(str(width_y)+","+str(height_x))
##            center = [int(self.geometry().width()/2), int(self.geometry().height()/2)]
##            
##            offset_y = -width_y + center[0]
##            offset_x = height_x - center[1]
##            cprint(str(offset_y)+","+str(offset_x)+" == offset")
##
##            ##move motor
##            activate()
##            move_xy(int(offset_x*xstep_per_pix*1.2),
##                    int(offset_y*xstep_per_pix*1.2))
##            self.setText('coords: ( % d : % d )' % (QMouseEvent.x(), QMouseEvent.y()))
            self.clicked.emit()
    def mouseReleaseEvent(self, QMouseEvent):
        if QMouseEvent.button() == Qt.LeftButton:
            #print(QMouseEvent.x(), QMouseEvent.y())
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
            
class mainwindow(QWidget):
    def __init__(self):
        super(mainwindow, self).__init__()
##        self.setText(content)
##        self.setFont(QFont('Times', 11))
##        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
##        self.setFixedSize(150,22)
        
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
close_btn = ("QPushButton { background-color: rgb(25,185,75); font: bold 12px;}"
            "QPushButton { border-color: rgb(40,40,15); border-width: 2px; }"
            "QPushButton { border-style: inset; border-radius: 4px; padding: 10px; }"
            "QPushButton:pressed { background-color: rgb(50,165,75) }")

cancel_btn = ("QPushButton { background-color: rgb(185,25,75); font: bold 12px;}"
            "QPushButton { border-color: rgb(40,40,15); border-width: 2px; }"
            "QPushButton { border-style: inset; border-radius: 4px; padding: 10px; }"
            "QPushButton:pressed { background-color: rgb(165,50,75) }")

save_btn = ("QPushButton { background-color: rgb(25,120,250); font: bold 12px;}"
            "QPushButton { border-color: rgb(40,40,15); border-width: 2px; }"
            "QPushButton { border-style: inset; border-radius: 4px; padding: 10px; }"
            "QPushButton:pressed { background-color: rgb(25,120,200) }")

cam_btn = ("QPushButton { background-color: rgb(200,200,200); font: bold 12px;}"
            "QPushButton { border-color: rgb(40,40,15); border-width: 2px; }"
            "QPushButton { border-style: inset; border-radius: 4px; padding: 10px; }"
            "QPushButton:pressed { background-color: rgb(180,180,180) }")

class_btn_1 = ("background-color: rgb(200,100,120); font: bold 15px; border-style: inset; border-radius: 45px; padding: 2px;border-color: rgb(40,40,15); border-width: 2px;")
class_btn_2 = ("background-color: rgb(230,150,150); font: bold 15px; border-style: inset; border-radius: 45px; padding: 2px;border-color: rgb(40,40,15); border-width: 2px;")


### ************************************ ###
###           Global Variables           ###
### ************************************ ###
### =====> GUI 
run_step = [i+1 for i in range(11)]
current_step = 0
cur_checkpoint = 0
error_code = 0
sequence = 0
step_instructions = ['Step 1: Load the chip, tubings and vials in order',
                     'Step 2: Priming the chip',
                     'Step 3: Change to PBS Vial',
                     'Step 4: Wash the chip with PBS buffer',
                     'Step 5: Wash the Sample loading reservoir',
                     'Step 6: Loading Sample',
                     'Step 7: Run the test',
                     'Step 8: Confirm the next outlet',
                     'Step 9: Run the test',
                     'Step 10: Discard your sample',
                     'Shutdown sequence']
cwDir = os.getcwd()
data_path = cwDir + "\\Data\\"
dataDir = cwDir + "\\Data\\"
multiple_run = 0
user = ' '
year, month, month_b , day, hour, minute = date_time()
present = day + ' ' + month_b + ' ' + year + ' ' + '('+ hour + ':' + minute + ')'
file_stem = 'Name Your File'
filename = 'file.save'
console_log = []
console_num = 0
count,count2,count3   = 0,0,0
chip_x = 0
chip_y = 0

### =====> Camera Settings
exposure_time = 50000        #micro seconds min=10us
FPS = 25                    #Frame rate to capture
gain = 0                    #Sensor gain
image_format = 'Mono8'      #image pixel format. 'Mono8' or 'Bayer' for BGR
width = 1440                #image width in pixels
height = 1080               #image height in pixels
Show = 1                    #Show = show the video while loop
num_frames = 1000           #number of frames to view
video_record = 0            #1: to record the video, 0: No Record
video_mode = 'AVI'          #AVI or MJPG 
video_name = 'a.avi'        #Filename to save as
got_camera = False
no_cancel = False
feature_matching = 0

capture_x,capture_y, capture_w, capture_h = 0,0,0,0
ROT_x, ROT_y , ROT_w, ROT_h = 0,0,width,height
ROI_x, ROI_y , ROI_w, ROI_h = 0,0,0,0
ROI = [ROI_x, ROI_y , ROI_w, ROI_h]
dots_coord = (0,0)

#process variables/constants
pix_um_full = 0.735778      #microns per pixel full 1440(y) - 1080(x) res
pix_um_scaled = 0.490519    #microns per pixel scaled 960(y - 720(x) res
um_per_ystep = 4.01786      #y microns per motor step
um_per_xstep = 2.54464      #x microns per motor step
y_add_freeplay = 1          # 1 = no free play, -1 = add free play
x_add_freeplay = 1          # 1 = no free play, -1 = add free play
# [Critical] Process Constants
ystep_per_pix = 0.33827     #ysteps per FULL pix res
xstep_per_pix = 0.53410526  #xsteps per FULL pix res
y_freeplay = 50             #20 steps per y direction change free play
x_freeplay = 30             #35 steps per x direction change free play

#Chip operation parameters
prime_count = 400           # Seconds number for Pluronic Prime
wash_count = 230            # Seconds number for PBS wash
PBS_count = 40              # Seconds number for PBS wash
p_count = 40
run_assay1 = 0              # Run L-shape Pillars
run_assay2 = 0              # Run INV-L-shape Pillars

#ROI parameters
pix_per_ch = 33.114         #number of pixels in one channel (45 micron)
channels = 35               #number of channels
detect_ybuffer = 260        #pixels for the y-axis positioning (width)
detect_xbuffer = 500        #pixels for the x-axis positioning (height)


#angle variables
angle = 0                   #rotational angle
rot_x = 0                   #x pos value of final rotated and cropped image
rot_y = 0                   #y pos value of final rotated and cropped image
rot_width = width               #width of final rotated and cropped image
rot_height = height              #height of final rotated and cropped image

### ---- Qt Initialize --- ###
## Always start by initializing Qt (only once per application)
app = QApplication([])
app.setStyle('Fusion')
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
w = mainwindow()
w.setStyleSheet("background-color: rgb(240,240,240)")
w.setWindowTitle("SMART DLD Assay GUI " + __version__)
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
file_type_menu.addItem('MP4')
file_type_menu.addItem('AVI')
file_type_menu.addItem('MJPG')


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

label3 = QLabel('Check List of Consumables')
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

a_view_label = myLabel()
a_view_label.setText('OpenCV Image')
a_view_label.setAlignment(Qt.AlignCenter)
a_view_label.setFixedSize(1000,780)
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
PBSwash_btn = QPushButton('Begin PBS Wash'); PBSwash_btn.setStyleSheet(btn1); PBSwash_btn.setFixedSize(200,50)

ROIyes_btn = QPushButton('YES!');ROIyes_btn.setStyleSheet("background-color: rgb(75,225,20); border-width: 1px") ; ROIyes_btn.setFixedSize(100,50)
ROIno_btn = QPushButton('NO...'); ROIno_btn.setStyleSheet("background-color: rgb(225,0,75); border-width: 1px"); ROIno_btn.setFixedSize(100,50)

Sample_btn = QPushButton('Sample'); Sample_btn.setStyleSheet("background-color: rgb(220,220,220); border-width: 1px"); Sample_btn.setFixedSize(100,40)
O1_btn = QPushButton('Buffer1'); O1_btn.setStyleSheet("background-color: rgb(220,220,220); border-width: 1px"); O1_btn.setFixedSize(100,40)
O2_btn = QPushButton('Buffer2'); O2_btn.setStyleSheet("background-color: rgb(220,220,220); border-width: 1px"); O2_btn.setFixedSize(100,40)

##new_btn = QPushButton('Back',basic_w)
##new_btn.move(500,100)

# -----Advance Tab Buttons----- #
btn1 = QPushButton('Camera'); btn1.setFixedSize(80,25)
btn2 = QPushButton('Cancel'); btn2.setFixedSize(80,25)
btn3 = QPushButton('Save'); btn3.setFixedSize(80,25)
btn4 = QPushButton('Close'); btn4.setFixedSize(80,25)
btn5 = QPushButton('Record'); btn5.setFixedSize(80,25)
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
metrics_btn = QPushButton('Metrics Update')
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
b_bar = QProgressBar()

# ==== Timer Object ==== #
timer = QTimer()
timer2 = QTimer()
timer3 = QTimer()
timer4 = QTimer()
# ==== CONSOLE LIST ==== #
console_list = QListWidget()
console_list.setFixedSize(w_dim.width()*0.8,100)

### ---- Main window layout ---- ###
bigLayout =  QGridLayout()
##bigLayout.addWidget(menubar,0,0)
bigLayout.addWidget(tab,1,0)

### ---- ADVANCE Tab layout LVL 1 ---- ###
box_button = QGroupBox('Buttons')
box_button.setStyleSheet("QGroupBox{ border: 0.5px solid; border-color: rgba(0, 0, 0, 75%);}")
box_camera = QGroupBox('Camera Settings') # note: box_camera will be set in box_button
box_camera.setFixedSize(win_length*0.203,win_width*0.43)
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
box_button_Layout.addWidget(btn1, 0, 1,1,1)
box_button_Layout.addWidget(btn2, 0, 2,1,1)
box_button_Layout.addWidget(btn3, 0, 3,1,1)
#box_button_Layout.addWidget(btn4, 0, 4,1,1)
box_button_Layout.addWidget(btn5, 0, 4,1,1)
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
box_motor_Layout.addWidget(metrics_btn,         1,4,1,2)
box_motor_Layout.addWidget(move_xy_btn,         2,0,1,2)
box_motor_Layout.addWidget(move_x_value,        2,2,1,2)
box_motor_Layout.addWidget(move_y_value,        2,4,1,2)
box_motor_Layout.addWidget(move_z_btn,          3,0,1,2)
box_motor_Layout.addWidget(move_z_value,        3,2,1,4)
box_motor_Layout.addWidget(out_Pa_btn,          4,0,1,2)
box_motor_Layout.addWidget(out_Pa_value,        4,2,1,2)
box_motor_Layout.addWidget(in_Pa_btn,           5,0,1,2)
box_motor_Layout.addWidget(in_Pa_value,         5,2,1,2)
box_motor_Layout.addWidget(release_Pa_btn,      4,4,2,2)
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
label_view1.setPixmap(QPixmap("Images/instructions.jpg").scaled(1850, b_dim.height(),
                                                               Qt.KeepAspectRatio, Qt.FastTransformation))
label_view1.move(0,0) ## Move(x,y with y = middle and x = left)
##label_view1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

label_view2 = QLabel('Image2',steps_view)
label_view2.setFixedSize(b_dim.width(),b_dim.height())
##label_view2.setPixmap(QPixmap("Images/background2.jpg").scaled(1850, 200,
##                                                               Qt.KeepAspectRatio, Qt.FastTransformation))
label_view2.setStyleSheet("background-color: rgba(225,225,225,0)")
label_view2.move(0,0) ## Move(x,y with y = middle and x = left)
label_view2.hide()
##label_view2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

##-->Buttons
button_dim = 300
button_w = QWidget(steps_view)
button_w.setGeometry(b_dim.width()-button_dim,
                     (0),
                     button_dim,
                     button_dim)
print(b_dim.width()-button_dim,(b_dim.height()-button_dim)/2,button_dim,button_dim)
label_up = motor_move_up('UP');label_up.setFixedSize(80, 80) ; label_up.setStyleSheet(dir_btn)
label_down = motor_move_down('DOWN');label_down.setFixedSize(80, 80); label_down.setStyleSheet(dir_btn)
label_left = motor_move_left('LEFT');label_left.setFixedSize(80, 80); label_left.setStyleSheet(dir_btn)
label_right = motor_move_right('RIGHT');label_right.setFixedSize(80, 80); label_right.setStyleSheet(dir_btn)
label_focus = QPushButton('Focus');label_focus.setFixedSize(80, 80); label_focus.setStyleSheet(dir_btn)
move_z_up = zaxis_move_up('Z-Axis Up'); move_z_up.setFixedSize(90, 30); ##move_z_up.setStyleSheet(dir_btn)
move_z_down = zaxis_move_down('Z-Axis Down'); move_z_down.setFixedSize(90, 30); ##move_z_down.setStyleSheet(dir_btn)

button_view = QGridLayout(button_w)
button_view.addWidget(label_up, 0,1)
button_view.addWidget(label_down, 2,1)
button_view.addWidget(label_left, 1,0)
button_view.addWidget(label_right, 1,2)
button_view.addWidget(label_focus, 1,1)
button_view.addWidget(move_z_up, 3,1)
button_view.addWidget(move_z_down, 4,1)
button_w.setStyleSheet("background-color: rgba(225,225,225,0)")
button_w.hide()

btn_wash = QWidget(steps_view)
btn_wash.setGeometry(b_dim.width()-button_dim,(b_dim.height()-button_dim)/2,
                     button_dim,button_dim)
btn_wash.setStyleSheet("background-color: rgba(225,225,225,0)")
btn_washLayout = QGridLayout(btn_wash)
btn_washLayout.addWidget(PBSwash_btn    ,0,0,1,6,alignment=Qt.AlignCenter)
##btn_washLayout.addWidget(Sample_btn     ,2,0,1,2,alignment=Qt.AlignCenter)
##btn_washLayout.addWidget(O1_btn         ,2,2,1,2,alignment=Qt.AlignCenter)
##btn_washLayout.addWidget(O2_btn         ,2,4,1,2,alignment=Qt.AlignCenter)
btn_washLayout.addWidget(ROIyes_btn     ,3,2,1,2,alignment=Qt.AlignCenter)
##btn_washLayout.addWidget(ROIno_btn      ,3,3,1,3,alignment=Qt.AlignCenter)
btn_wash.hide()

basicLayout_run =  QVBoxLayout()
basicLayout_run.addWidget(label3,1)
basicLayout_run.addWidget(steps_view,12)
basicLayout_run.addWidget(b_bar,1)
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
btn3.clicked.connect(save_data)
#btn4.clicked.connect(close_event)
btn5.clicked.connect(record)
home_btn.clicked.connect(home_xy)
release_Pa_btn.clicked.connect(release_pressure)
metrics_btn.clicked.connect(metrics)
focus_btn.clicked.connect(autofocus)
PBSwash_btn.clicked.connect(PBS_wash_clicked)

##Sample_btn.clicked.connect(check_sample);Sample_btn.setCheckable(True)
##O1_btn.clicked.connect(check_O1);O1_btn.setCheckable(True)
##O2_btn.clicked.connect(check_O2);O2_btn.setCheckable(True)

ROIyes_btn.clicked.connect(user_input_button)
##label_focus.clicked.connect(autofocus)

## execute the widget layouts
w.setLayout(bigLayout)
basic_w.setLayout(basicLayout)
advance_w.setLayout(advanceLayout)

camera_start()
### ---- Display the widget as a new window ---- ###

##app.setQuitOnLastWindowClosed(False)
app.lastWindowClosed.connect(close_event)

w.show()
ret=app.exec_()
print(ret)
### ---- Close event function run ---- ###
##w.closeEvent(close_event())
##close_event()

## Finally...
print('The application has shutdown')
sys.exit(0)

