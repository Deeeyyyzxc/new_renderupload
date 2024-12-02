from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

app = Flask(__name__)
CORS(app)

DB_HOST = 'dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com' 
DB_PORT = '5432'
DB_NAME = 'facetwahdb'
DB_USER = 'facetwahdb_user'
DB_PASS = 'FDmm3mM50lE91i0WFlXr4VFtyKRexoFi' 

ph = PasswordHasher()

def get_db_connection():
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return connection

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password are required'}), 400
    
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('SELECT pass FROM creds WHERE username = %s', (username,))
        result = cursor.fetchone()

        if not result:
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

        hashed_password = result[0]

        try:
            ph.verify(hashed_password, password)
            return jsonify({'status': 'success', 'message': 'Login successful', 'user': username}), 200
        except VerifyMismatchError:
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
    finally:
        cursor.close()
        connection.close()

@app.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    position = data.get('position')

    if not username or not password or not position:
        return jsonify({'status': 'error', 'message': 'Username, password, and position are required'}), 400

    hashed_password = ph.hash(password)

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('INSERT INTO creds (username, pass, position) VALUES (%s, %s, %s)', 
                       (username, hashed_password, position))
        connection.commit()
        return jsonify({'status': 'success', 'message': 'User registered successfully'}), 200
    except psycopg2.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Username already exists'}), 400
    finally:
        cursor.close()
        connection.close()

@app.route('/get_creds', methods=['GET'])
def get_creds():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute('SELECT username, position, pass FROM creds')
        results = cursor.fetchall()

        creds = []
        for row in results:
            
            creds.append({
                'null': "null"
            })
        
        return jsonify({'status': 'success', 'creds': creds}), 200
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)