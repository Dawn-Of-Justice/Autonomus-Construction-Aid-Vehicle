from server import VideoReceiver
from aruco import ArUcoDetector
from datacollector import Preprocessor
from gesture import ProtectionSystem
from obj_det import objDet
import cv2
import numpy as np
import threading
# from PathPlanner import PathPlanning
from PathPlanner2 import PathPlanning

receiver = VideoReceiver()
receiver.accept_connection()
detector = ArUcoDetector()
processor = Preprocessor()
protection_system = ProtectionSystem("code/server-pc/keras_Model.h5", "code/server-pc/labels.txt")
ObjectDetect = objDet()

pathplanner = PathPlanning((0,0))

lock = 0
delta = 0
prev_delta = 0
def get_command(command):
    receiver.send_command(command)


def find_nigga(last_action:str):
    global active
    if active:
        if last_action == 'l':
            get_command('hl')
            active = False
        if last_action == 'r':
            get_command('hr')
            active = False

# command_thread = threading.Thread(target=get_command)
# command_thread.daemon = True
# command_thread.start()

while True:

    frame = receiver.receive_frame()
    if frame is None:
        continue
    if not receiver.display_frame(frame):
        break
    result, ids_with_corners = detector.detect_markers(frame)
    
    if prev_delta == 1 and delta == 0:
        cv2.destroyAllWindows()
    if result is not None:
        # cv2.imshow('Frame', result)
        if lock == 1:
            get_command('f')   
 
        if ids_with_corners:
            try:
                delta = 1
                bboxes, classes, _ = ObjectDetect.detect(frame, return_bbox=True)
                aruco_id = ids_with_corners[0][1][0][0][0],ids_with_corners[0][1][0][0][1],ids_with_corners[0][1][0][2][0],ids_with_corners[0][1][0][2][1]
                
                ObjectDetect.draw_bbox(frame, bboxes, classes, _)
                # frame = pathplanner.draw_filled_rectangles(frame, bboxes, classes, _)
                if 'person' in classes:
                    
                    idx = classes.index('person')
                    bbox = bboxes[idx]
                    # print('aruco',aruco_id)
                    # print('person:',bbox)
                if objDet.is_bbox_inside(aruco_id, bbox):
                    # print('Aruco Inside')
                    try:
                        image = cv2.resize(frame,(640, 430))
                        masked_image = processor.process(image)
                        
                        if masked_image is not None:
                            cv2.imshow('Skelton', masked_image)
                        #     cv2.line(frame, (pathplanner.lane_1,200), (pathplanner.lane_1, 400), (0,255,0), 2)
                        #     cv2.line(frame, (pathplanner.lane_2,200), (pathplanner.lane_2, 400), (0,255,0), 2)
                        class_name, confidence_score = protection_system.predict(masked_image)
                        print("Class:", class_name[2:], end="")
                        print("Confidence Score:", str(np.round(confidence_score * 100))[:-2], "%")
                        if class_name[2:].strip() == "Go":
                            lock = 1

                        if lock:    
                            pathplanner.lane_1 = int(frame.shape[0]*0.5)
                            pathplanner.lane_2 = int(frame.shape[0]*0.9)
                            pathplanner.centre_of_tracking = (pathplanner.lane_1, pathplanner.lane_2)

                            # command = pathplanner.lane_assist(int((bbox[0]+bbox[2])/2), bbox[2])
                            command = pathplanner.lane_assist(int((bbox[0]+bbox[2])/2), bbox[2], classes, bboxes=bboxes, goal_pos = (int((bbox[0]+bbox[2])/2), int((bbox[1]+bbox[3])/2)))
                            # obstacle_mask = pathplanner.draw_filled_rectangles(frame, bboxes, classes, _)
                            # cv2.imshow('Mask', obstacle_mask)
                            cv2.line(frame, (pathplanner.lane_1,200), (pathplanner.lane_1, 400), (0,255,0), 2)
                            cv2.line(frame, (pathplanner.lane_2,200), (pathplanner.lane_2, 400), (0,255,0), 2)
                            # if masked_image is not None:
                            #     cv2.line(frame, (pathplanner.lane_1,200), (pathplanner.lane_1, 400), (0,255,0), 2)
                            #     cv2.line(frame, (pathplanner.lane_2,200), (pathplanner.lane_2, 400), (0,255,0), 2)
                            #     cv2.imshow('Skelton', masked_image)
                                
                            if command:
                                get_command(command)
                            if command is None:
                                get_command('n')
                        if class_name[2:].strip() == "Stop":
                            lock = 0
                            get_command('s')

            
                    except Exception as e:
                        pass
        
            except Exception as e:
                pass
    
        # cv2.imshow('Frame', frame)
    
    
    else:
        delta = 0
        get_command('s')
        prev_delta = delta            
        
    cv2.imshow('Frame', frame)
    


    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
receiver.close_connection()