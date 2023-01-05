import cv2
import face_recognition
import numpy as np
import os

import face_files

known_face_encodings = []
known_face_names = []

def load_features():
    print("loading features...")
    global known_face_encodings
    global known_face_names    
    for fname in face_files.filenames:
        path = os.path.join("../data/face_images", fname)
        im = face_recognition.load_image_file(path) 
        locations = face_recognition.face_locations(im) 
        encodings = face_recognition.face_encodings(im, locations)
        name = fname[0:3]
        #print(encodings, name)
        known_face_encodings.extend(encodings)
        known_face_names.append(name)
        print("loading features...", len(known_face_encodings), "/", len(known_face_names), "/", len(face_files.filenames))

load_features()
print(known_face_encodings)
print(known_face_names)


def find_face(fpath:str):
    global known_face_encodings
    global known_face_names
    bgrim = cv2.imread(fpath)
    bgrim = cv2.transpose(bgrim)
    bgrim = cv2.flip(bgrim, flipCode=1)
    
    rgbim = bgrim[:, :, ::-1]

    face_locations = face_recognition.face_locations(rgbim)
    face_encodings = face_recognition.face_encodings(rgbim, face_locations)
    
    face_names = []
    for face_encoding in face_encodings:
        print("face_encoding", face_encoding)
        print("known_face_encodings, face_encoding", [len(x) for x in known_face_encodings], len(face_encoding))
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"
        
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]

        face_names.append(name)
        
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        cv2.rectangle(bgrim, (left, top), (right, bottom), (0, 0, 255), 2)

        cv2.rectangle(bgrim, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(bgrim, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)        
    
    cv2.imwrite(fpath, bgrim)
    
    return face_names
