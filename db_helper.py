import mysql.connector
from mysql.connector import Error
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def init_db():
    """Initialize the database and create user_login_info table if it doesn't exist"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE user_login_info (
            username VARCHAR(50) NOT NULL PRIMARY KEY, 
            password_hash VARCHAR(65) NOT NULL, 
            Age INTEGER, 
            Height DECIMAL(5, 2), 
            Gender VARCHAR(25), 
            Blood_Group VARCHAR(5), 
            Weight DECIMAL(5, 2), 
            Medical_Conditions TEXT, 
            Allergies TEXT, 
            Medications TEXT,
            Medical_History TEXT);
        """)
        connection.commit()
        cursor.close()
        connection.close()
        return True
    except Error as e:
        print(f"Error initializing database: {e}")
        return False

def user_exists(username):
    """Check if a user exists in the database"""
    connection = get_db_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT username FROM user_login_info WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result is not None
    except Error as e:
        print(f"Error checking user: {e}")
        return False

def create_user(username, password, patient_data=None):
    """Create a new user with hashed password and optional patient data"""
    if user_exists(username):
        return False, "Username already exists"
    
    connection = get_db_connection()
    if connection is None:
        return False, "Database connection failed"
    
    try:
        # Hash the password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        cursor = connection.cursor()
        
        if patient_data:
            cursor.execute("""
                INSERT INTO user_login_info VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                username,
                password_hash,
                patient_data['age'],
                patient_data['height'],
                patient_data['gender'],
                patient_data['blood_group'],
                patient_data['weight'],
                patient_data['existing_conditions'],
                patient_data['allergies'],
                patient_data['current_medications'],
                patient_data['medical_history']
            ))
        else:
            cursor.execute(
                "INSERT INTO user_login_info (username, password_hash) VALUES (%s, %s)",
                (username, password_hash)
            )
        
        connection.commit()
        cursor.close()
        connection.close()
        return True, "User created successfully"
    except Error as e:
        print(f"Error creating user: {e}")
        return False, f"Error creating user: {e}"

def verify_user(username, password):
    """Verify user credentials"""
    connection = get_db_connection()
    if connection is None:
        return False, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT password_hash FROM user_login_info WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result is None:
            return False, "Username not found"
        
        password_hash = result[0]
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')
        
        if bcrypt.checkpw(password.encode('utf-8'), password_hash):
            return True, "Login successful"
        else:
            return False, "Incorrect password"
    except Error as e:
        print(f"Error verifying user: {e}")
        return False, f"Error verifying user: {e}"


def save_patient_info(username, patient_data):
    """Save patient information for a user"""
    connection = get_db_connection()
    if connection is None:
        return False, "Database connection failed"
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE user_login_info 
            SET Age = %s, Gender = %s, Weight = %s, Height = %s, Blood_Group = %s, 
                Medical_Conditions = %s, Allergies = %s, Medications = %s, Medical_History = %s
            WHERE username = %s
        """, (
            patient_data['age'],
            patient_data['gender'],
            patient_data['weight'],
            patient_data['height'],
            patient_data['blood_group'],
            patient_data['existing_conditions'],
            patient_data['allergies'],
            patient_data['current_medications'],
            patient_data['medical_history'],
            username
        ))
        connection.commit()
        cursor.close()
        connection.close()
        return True, "Patient info saved successfully"
    except Error as e:
        print(f"Error saving patient info: {e}")
        return False, f"Error saving patient info: {e}"

def get_patient_info(username):
    """Retrieve patient information for a user"""
    connection = get_db_connection()
    if connection is None:
        return None
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT Age, Gender, Weight, Height, Blood_Group, Medical_Conditions, Allergies, Medications, Medical_History
            FROM user_login_info WHERE username = %s
        """, (username,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        if result is None:
            return None
        
        return {
            'age': result[0],
            'gender': result[1],
            'weight': result[2],
            'height': result[3],
            'blood_group': result[4],
            'existing_conditions': result[5],
            'allergies': result[6],
            'current_medications': result[7],
            'medical_history': result[8]
        }
    except Error as e:
        print(f"Error retrieving patient info: {e}")
        return None
