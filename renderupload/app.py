from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import os
import signal
import psycopg2

app = Flask(__name__)
CORS(app)

current_processes = []

# Define the valid API key directly in the code
VALID_API_KEY = "U6sZ7EsPyJAcaOAgSVpT4mAZeNKOJOc7"

def is_valid_api_key(api_key):
    return api_key == VALID_API_KEY

def connect_db():
    try:
        # PostgreSQL connection
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

def insert_employee(name, age, department, position, address, employee_id):
    """Insert employee data into the PostgreSQL database."""
    try:
        conn = connect_db()
        if conn is None:
            return False, "Database connection failed"

        # Ensure 'age' is an integer before inserting
        try:
            age = int(age)  # This will raise a ValueError if age is not a valid integer
        except ValueError:
            return False, f"Invalid age value: {age}. Age must be an integer."

        cursor = conn.cursor()
        
        # SQL query to insert employee data (without specifying the serial id)
        query = """
            INSERT INTO employee (name, age, department, position, address, employee_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;  -- Get the id of the newly inserted employee
        """
        cursor.execute(query, (name, age, department, position, address, employee_id))
        employee_id_db = cursor.fetchone()[0]  # Get the newly inserted employee's id
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"Employee registered successfully with ID: {employee_id_db}"
    except Exception as e:
        print(f"Error inserting employee: {e}")
        return False, str(e)


@app.before_request
def require_api_key():
    protected_endpoints = ['/run-script', '/stop-script', '/register-face']
    
    if request.path in protected_endpoints:
        api_key = request.headers.get('X-API-Key')
        if not api_key or not is_valid_api_key(api_key):
            return jsonify({'status': 'error', 'message': 'Invalid or missing API key'}), 403

def run_python_script(script_name, args=None):
    """Helper function to run a Python script and return its output."""
    try:
        if args is None:
            args = []
        process = subprocess.Popen(
            ['python3', script_name] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        current_processes.append(process)
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            return {'status': 'success', 'output': stdout.decode()}
        else:
            return {'status': 'error', 'output': stderr.decode()}
    
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/run-script', methods=['POST'])
def run_script():
    """Endpoint to run the main Python script."""
    result = run_python_script('main.py')
    if result['status'] == 'success':
        return jsonify(result)
    else:
        return jsonify(result), 400

@app.route('/stop-script', methods=['POST'])
def stop_script():
    """Endpoint to stop all running scripts."""
    try:
        if current_processes:
            for process in current_processes:
                try:
                    os.kill(process.pid, signal.SIGTERM)  # Terminate the process
                    print(f"Terminated process PID: {process.pid}")
                except ProcessLookupError:
                    print(f"Process {process.pid} already terminated.")
            current_processes.clear()
            return jsonify({'status': 'success', 'message': 'All scripts terminated successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'No scripts are running'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/register', methods=['POST'])
def register_face():
    """Endpoint to register a face, save user data, and run two Python scripts in sequence."""
    try:
        data = request.json
        name = data.get('name', '')
        age = data.get('age', '')
        department = data.get('department', '')
        position = data.get('position', '')
        address = data.get('address', '')
        employee_id = data.get('employee_id', '')

        if not name or not employee_id:
            return jsonify({'status': 'error', 'message': 'Name and Employee ID are required'}), 400

        # Insert employee data into the database
        insert_success, insert_message = insert_employee(name, age, department, position, address, employee_id)
        if not insert_success:
            return jsonify({'status': 'error', 'message': insert_message}), 500

        # Run the first face registration script
        result1 = run_python_script('simple_facereg.py', [name])

        if result1['status'] == 'success':
            # Run the second face registration script
            result2 = run_python_script('simple_facereg.py')  # Adjust if you need different script parameters

            if result2['status'] == 'success':
                return jsonify({
                    'status': 'success',
                    'output': f"First script output: {result1['output']}\nSecond script output: {result2['output']}"
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'First script succeeded but second script failed',
                    'output': result2['output']
                }), 400
        else:
            return jsonify({
                'status': 'error',
                'message': 'First script failed',
                'output': result1['output']
            }), 400

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
