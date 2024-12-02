import psycopg2
import cv2
from simple_facerec import SimpleFacerec 
from datetime import datetime # Adjust the import according to where SimpleFacerec is located

def main():
    sfr = SimpleFacerec()
    
    # Load face encodings (make sure the 'images/' directory exists with images to register)
    sfr.load_encoding_images("images/")

    # Start video capture
    cap = cv2.VideoCapture(0)
    
    logged_faces_today = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error reading from camera.")
            break

        try:
            # Detect known faces
            face_locations, face_names = sfr.detect_known_faces(frame)
            for face_loc, name in zip(face_locations, face_names):
                y1, x2, y2, x1 = face_loc
                width = x2 - x1
                height = y2 - y1
                if 0.75 <= width / height <= 1.3:
                    # Log recognized face
                    log_recognized_face(name, logged_faces_today)
                    cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 200), 2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 200), 4)
        except Exception as e:
            print(f"Error during face recognition loop: {e}")
            cv2.putText(frame, "Unknown", (10, 30), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 2)

        # Show the video frame
        cv2.imshow("Frame", frame)
        
        # Exit on pressing 'ESC'
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

def log_recognized_face(name, logged_faces_today):
    if name in logged_faces_today or name == "Unknown":
        return
    conn = psycopg2.connect(
        dbname="facetwahdb", 
        user="facetwahdb_user", 
        password="FDmm3mM50lE91i0WFlXr4VFtyKRexoFi", 
        host="dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com"
    )
    cursor = conn.cursor()
    today_date = datetime.now().date()
    cursor.execute("""
        SELECT name FROM recognized_faces
        WHERE name = %s AND DATE(recognized_at) = %s
    """, (name, today_date))
    if not cursor.fetchone():
        query = "INSERT INTO recognized_faces (name, recognized_at) VALUES (%s, %s)"
        cursor.execute(query, (name, datetime.now()))
        conn.commit()
        logged_faces_today.add(name)
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
