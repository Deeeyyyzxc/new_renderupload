import os
import cv2
import numpy as np
import psycopg2
import face_recognition
import sys
from ultralytics import YOLO
import math

class SimpleFacerec:
    def __init__(self):
        self.frame_resizing = 0.25
        self.images_folder = "images"  # Folder to store captured face images

        # Create folder if it doesn't exist
        if not os.path.exists(self.images_folder):
            os.makedirs(self.images_folder)

        # Initialize YOLO model for anti-spoofing
        self.model = YOLO('n_version_1_3.pt')  # Replace with your model's path
        self.classNames = ["fake", "real"]

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
        
    def get_employee_id(self, name):
        # Get the employee's ID from the database based on the name
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM employee WHERE name = %s", (name,))
                person_id = cursor.fetchone()
                conn.close()
                if person_id:
                    return person_id[0]
                else:
                    print(f"Employee with name {name} not found in the database.")
                    return None
            except Exception as e:
                print(f"Error fetching employee ID from the database: {e}")
                conn.close()
                return None

    def check_existing_face(self, name):
        # Check if the name already exists in the images folder (based on name)
        img_path = os.path.join(self.images_folder, f"{name}.jpg")
        if os.path.exists(img_path):
            print(f"Face image for {name} already exists in the images folder. Skipping capture.")
            return True

        # Check if the face encoding already exists in the database
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT encoding FROM face_encodings WHERE name = %s", (name,))
                existing_encoding = cursor.fetchone()
                if existing_encoding:
                    print(f"Face encoding for {name} already exists in the database. Skipping registration.")
                    conn.close()
                    return True
            except Exception as e:
                print(f"Error checking face encoding in the database: {e}")
                conn.close()
                return False
        return False

    def insert_face_encoding(self, name, encoding):
        conn = self.connect_db()
        if conn:
            try:
                cursor = conn.cursor()
            # Get the employee's ID from the employee table
                cursor.execute("SELECT id FROM employee WHERE name = %s", (name,))
                person_id = cursor.fetchone()

                if person_id:
                    person_id = person_id[0]  # Get the employee's ID
                # Insert encoding into the face_encodings table
                    query = """
                        INSERT INTO face_encodings (name, encoding) 
                        VALUES (%s, %s) 
                        RETURNING id;
                        """
                    cursor.execute(query, (name, encoding.tobytes()))
                    encoding_id = cursor.fetchone()[0]  # Retrieve the auto-generated encoding ID
                    conn.commit()
                    print(f"Face encoding for {name} added to the database with encoding ID {encoding_id}.")
                else:
                    print(f"Employee with name {name} not found in the database.")
            except Exception as e:
                print(f"Error inserting encoding: {e}")
            finally:
                cursor.close()
                conn.close()


    def capture_and_register_face(self, name):
        # Check if the face image or encoding already exists
        if self.check_existing_face(name):
            return

        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Set a lower resolution for better performance
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        captured = False
        frame_count = 0
        real_face_count = 0  # To track consistency of real face detection

        while not captured:
            ret, frame = cap.read()
            if not ret:
                break

            # Resize the frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=self.frame_resizing, fy=self.frame_resizing)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Detect face in the resized frame
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            # Perform anti-spoofing detection with YOLO
            results = self.model(frame, stream=True, verbose=False)
            is_real_face = False
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    conf = math.ceil((box.conf[0] * 100)) / 100
                    cls = box.cls[0]
                    name_detected = self.classNames[int(cls)].upper()

                    if conf > 0.8:  # Confidence threshold for detection
                        if name_detected == "FAKE":
                            print("Fake face detected. Skipping registration.")
                            cap.release()
                            cv2.destroyAllWindows()
                            return  # Skip registration if fake face is detected
                        elif name_detected == "REAL":
                            real_face_count += 1  # Count how many frames show a "real" face
                            is_real_face = True
                            print(f"Real face detected with confidence {conf}. Frame count: {real_face_count}")

            # If we detect multiple consecutive frames with real faces, proceed with registration
            if is_real_face and real_face_count > 5:  # 5 consecutive frames of real faces
                if face_encodings:
                    # Assume first detected face is the intended face
                    encoding = face_encodings[0]
                    # Scale back face locations to full size
                    y1, x2, y2, x1 = [int(coord / self.frame_resizing) for coord in face_locations[0]]

                    # Save image to /images folder
                    img_path = os.path.join(self.images_folder, f"{name}.jpg")
                    cv2.imwrite(img_path, frame[y1:y2, x1:x2])
                    print(f"Face image saved at {img_path}")

                    # Store encoding in the database
                    self.insert_face_encoding(name, encoding)
                    print(f"Face registered for {name}.")
                    captured = True

                    # Display confirmation on screen
                    cv2.putText(frame, "Face Registered", (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("Frame", frame)
                    cv2.waitKey(1000)  # Pause for confirmation display

            # Display the live feed
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) == 27:  # Press ESC to exit capture
                break

            frame_count += 1
            if frame_count > 50:  # After 50 frames, exit if registration is not completed
                print("No valid real face detected after multiple frames. Exiting.")
                break

        cap.release()
        cv2.destroyAllWindows()

# Main registration process
if __name__ == "__main__":
    if len(sys.argv) > 1:
        name = sys.argv[1]  # Get the name from command-line argument
        sfr = SimpleFacerec()
        sfr.capture_and_register_face(name)
    else:
        print("Please provide a name as a command-line argument.")
