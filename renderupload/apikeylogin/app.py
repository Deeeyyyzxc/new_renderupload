from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2 import sql
from passlib.hash import sha256_crypt

app = Flask(__name__)
CORS(app)

DB_HOST = 'dpg-ct2naf3tq21c73b4s8lg-a.singapore-postgres.render.com'
DB_PORT = '5432'
DB_NAME = 'facetwahdb'
DB_USER = 'facetwahdb_user'
DB_PASS = 'FDmm3mM50lE91i0WFlXr4VFtyKRexoFi'

API_KEYS = [
   "U6sZ7EsPyJAcaOAgSVpT4mAZeNKOJOc7",  # API Key
]

def get_db_connection():
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return connection

def check_api_key():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return False

    token = auth_header.split(" ")[1] if " " in auth_header else ""

    if token in API_KEYS:
        return True
    return False

@app.route('/login', methods=['POST'])
def login():
    if not check_api_key():
        return jsonify({"status": "error", "message": "Invalid API Key"}), 403

    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password are required'}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT password_hash FROM users WHERE username = %s", (username,)
        )
        result = cursor.fetchone()
        if not result:
            return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 400
        
        password_hash = result[0]
        
        # Verify the password
        if not sha256_crypt.verify(password, password_hash):
            return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 400
        
        return jsonify({'status': 'success', 'message': 'Login successful'}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        cursor.close()
        connection.close()

@app.route('/register', methods=['POST'])
def register():
    if not check_api_key():
        return jsonify({"status": "error", "message": "Invalid API Key"}), 403

    data = request.json
    name = data.get('name')
    age = data.get('age')
    department = data.get('department')
    position = data.get('position')
    address = data.get('address')
    employee_id = data.get('employee_id')

    # Field validations
    if not name or not age or not department or not position or not address or not employee_id:
        return jsonify({'status': 'error', 'message': 'All fields are required'}), 400

    try:
        age = int(age)
        employee_id = int(employee_id)
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Age and Employee ID must be integers'}), 400

    valid_departments = ['BRM and Creative Media','Project Management Unit','Quality Assurance','Technical Support','Development']
    if department.strip().upper() not in [dept.upper() for dept in valid_departments]:
        return jsonify({'status': 'error', 'message': 'Invalid department'}), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            '''
            INSERT INTO employee (name, age, department, position, address, employee_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ''',
            (name, age, department, position, address, employee_id)
        )
        connection.commit()

        return jsonify({'status': 'success', 'message': 'Employee registered successfully'}), 200

    except psycopg2.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Employee ID already exists'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
