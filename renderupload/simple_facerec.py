import cv2
import math
import os
import glob
import psycopg2
import numpy as np
import face_recognition
from datetime import datetime
from ultralytics import YOLO
import cvzone

# Configuration and model loading
confidence = 0.8
model = YOLO('n_version_1_3.pt')
classNames = ["fake", "real"]
frame_resizing = 0.25

# Initialize SimpleFacerec class for face recognition
class SimpleFacerec:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = [] 

    def connect_db(self):
        try:
            conn = psycopg2.connect(
                dbname="facetwahdb", 
                user="facetwahdb_user", 
                password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi", 
                host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
            )
            return conn
        except Exception as e:
            print(f"Error connecting to the database: {e}")
            return None

    def insert_face_encoding(self, name, encoding):
        conn = self.connect_db()
        person_id = None
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM face_encodings WHERE name = %s", (name,))
                existing_name = cursor.fetchone()
                if not existing_name:
                    query = "INSERT INTO face_encodings (name, encoding) VALUES (%s, %s) RETURNING id"
                    cursor.execute(query, (name, encoding.tobytes()))
                    person_id = cursor.fetchone()[0]  # Get the inserted person's id
                    conn.commit()
                else:
                    person_id = existing_name[0]  # Use existing person's id if the name already exists
            except Exception as e:
                print(f"Error inserting encoding: {e}")
            finally:
                cursor.close()
                conn.close()
        return person_id

    def load_encoding_images(self, images_path):
        images_path = glob.glob(os.path.join(images_path, "*.*"))
        print(f"{len(images_path)} encoding images found.")
        for img_path in images_path:
            img = cv2.imread(img_path)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            basename = os.path.basename(img_path)
            filename, ext = os.path.splitext(basename)
            img_encoding = face_recognition.face_encodings(rgb_img)[0]
            self.known_face_encodings.append(img_encoding)
            self.known_face_names.append(filename)
            person_id = self.insert_face_encoding(filename, img_encoding)  # Insert and get person ID
        print("Encoding images loaded")

    def detect_known_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=frame_resizing, fy=frame_resizing)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        face_names = []

        for face_encoding in face_encodings:
            # Compare the detected face encoding with known faces
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)

            # Find the best match and check the distance
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    # If the distance is within an acceptable threshold, it's considered a match
                    if face_distances[best_match_index] < 0.5:  # Lower the threshold
                        name = self.known_face_names[best_match_index]
            face_names.append(name)
        
        # Adjust face locations back to the original frame size
        face_locations = np.array(face_locations)
        face_locations = face_locations / frame_resizing
        return face_locations.astype(int), face_names

# Function to log attendance (directly in the attendance table)
def log_attendance(name):
    if name == "Unknown":
        return

    try:
        conn = psycopg2.connect(
            dbname="facetwahdb", 
            user="facetwahdb_user", 
            password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi", 
            host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
        )
        cursor = conn.cursor()

        today_date = datetime.now().date()
        cursor.execute(""" 
            SELECT id, in_time, out_time FROM attendance
            WHERE name = %s AND DATE(in_time) = %s
        """, (name, today_date))

        # Check if person already has an 'in_time' logged today
        existing_record = cursor.fetchone()

        if existing_record:
            # If a record exists, update the 'out_time'
            cursor.execute("""
                UPDATE attendance 
                SET out_time = %s 
                WHERE name = %s AND DATE(in_time) = %s
            """, (datetime.now(), name, today_date))
            conn.commit()
        else:
            # Get the person's id from the `employee` table based on the name
            cursor.execute("SELECT id FROM employee WHERE name = %s", (name,))
            person_id = cursor.fetchone()
            if person_id:
                person_id = person_id[0]
                # If no record exists, insert a new attendance entry with 'in_time'
                cursor.execute("""
                    INSERT INTO attendance (name, in_time, id) 
                    VALUES (%s, %s, %s)
                """, (name, datetime.now(), person_id))
                conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error logging attendance: {e}")

# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(3, 500)
cap.set(4, 480)

# Initialize SimpleFacerec and load face encodings
sfr = SimpleFacerec()
sfr.load_encoding_images("images/")  # Folder with encoding images

# Initialize list to track label positions to prevent overlap
label_positions = []

# Start main loop
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Perform object detection using YOLO
    results = model(frame, stream=True, verbose=False)
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # Fixed error here
            w, h = x2 - x1, y2 - y1
            conf = math.ceil((box.conf[0] * 100)) / 100
            cls = box.cls[0]
            name = classNames[int(cls)].upper()

            if conf > confidence:
                color = (0, 255, 0) if name == "REAL" else (0, 0, 255)
                # Position the cornerRect slightly above the bounding box to prevent overlap
                cvzone.cornerRect(frame, (x1, y1, w, h), colorC=color, colorR=color)

                # Increase y_offset to adjust the position higher above the bounding box
                label_y_position = max(35, y1 - 50)  # Moved 30 pixels above the bounding box
                label_text = f'{name} {int(conf*100)}%'
                cvzone.putTextRect(frame, label_text, (max(0, x1), label_y_position), scale=2, thickness=2, colorR=color, colorB=color)

                # Only log the face if it is "real"
                if name == "REAL":
                    # Detect known faces for recognition
                    face_locations, face_names = sfr.detect_known_faces(frame)
                    for face_loc, face_name in zip(face_locations, face_names):
                        # Adjust label_y_position to avoid overlapping with previous labels
                        while label_y_position in label_positions:
                            label_y_position -= 30  # Move the label 30 pixels up until it's free
                        label_positions.append(label_y_position)

                        # Log attendance if face is recognized
                        if face_name != "Unknown":
                            log_attendance(face_name)

    # Display the frame
    cv2.imshow("Attendance System", frame)

    # Break loop if the user presses 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
