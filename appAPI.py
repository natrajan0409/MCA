import secrets
from flask import Flask, flash, make_response, render_template, request, redirect, session, url_for, jsonify
from datetime import datetime, timedelta
import mysql.connector
import random
from smtplib import SMTP_SSL
from email.message import EmailMessage
import pytz
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY  

# Session timeout settings
SESSION_TIMEOUT = timedelta(minutes=2)  # session expires after 2 minutes of inactivity

# Database connection
mydb = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)
mycursor = mydb.cursor()

def send_otp(email, otp):
    message = EmailMessage()
    message['From'] = 'your-email@example.com'
    message['To'] = email
    message['Subject'] = 'Your OTP for Password Reset'
    message.set_content(f'Your OTP is {otp}')
    
    with SMTP_SSL("smtp.mail.yahoo.com", 465) as server:
        server.login("your-email@example.com", "your-email-password")
        server.send_message(message)

def generate_otp():
    return random.randint(100000, 999999)

@app.before_request
def check_session_expiration():
    if 'logged_in' in session:
        utc_now = datetime.now(pytz.UTC)
        if utc_now > session.get('expiration', utc_now):  # check if session expired
            refresh_token = session.get('refresh_token')
            if refresh_token:
                # Refresh the session token if possible
                new_token = refresh_session_token(refresh_token)
                if new_token:
                    session['token'] = new_token
                    session['expiration'] = utc_now + SESSION_TIMEOUT
                else:
                    session.clear()
                    return redirect(url_for('login_page'))
            else:
                session.clear()
                return redirect(url_for('login_page'))
        else:
            session['expiration'] = utc_now + SESSION_TIMEOUT  # Extend session expiration on activity

def refresh_session_token(refresh_token):
    query = "SELECT * FROM sessions WHERE refresh_token = %s"
    mycursor.execute(query, (refresh_token,))
    session_data = mycursor.fetchone()
    
    if session_data:
        new_token = generate_session_token()
        update_query = "UPDATE sessions SET token = %s WHERE refresh_token = %s"
        mycursor.execute(update_query, (new_token, refresh_token))
        mydb.commit()
        return new_token
    return None

def generate_session_token():
    return secrets.token_hex(16)

@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    # Query to check user existence
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    mycursor.execute(query, (username, password))
    user = mycursor.fetchone()

    if user:
        # Check for existing active session for the user
        session_active_query = "SELECT token FROM sessions WHERE username = %s"
        mycursor.execute(session_active_query, (username,))
        session_useractive = mycursor.fetchone()

        if session_useractive:  # Update existing session if found
            token = session_useractive[0]  # Get existing token
            expiration = datetime.now() + SESSION_TIMEOUT  # Update expiration

            # Update session data in database (optional, might be redundant)
            update_query = """
                UPDATE sessions 
                SET expiration = %s 
                WHERE username = %s
            """
            mycursor.execute(update_query, (expiration, username))
            mydb.commit()

            # Update session variables (optional, might be redundant)
            session['expiration'] = expiration

        else:  # Create new session if no active session exists
            token = generate_session_token()
            refresh_token = generate_session_token()
            expiration = datetime.now() + SESSION_TIMEOUT

            session['logged_in'] = True
            session['username'] = username
            session['token'] = token
            session['refresh_token'] = refresh_token
            session['expiration'] = expiration

            # Insert new session data into the database
            insert_query = """
                INSERT INTO sessions (username, token, refresh_token, expiration) 
                VALUES (%s, %s, %s, %s)
            """
            mycursor.execute(insert_query, (username, token, refresh_token, expiration))
            mydb.commit()

        # Set the token as a cookie (use the existing token if available)
        resp = make_response(redirect(url_for("home")))
        resp.set_cookie('auth_token', token, httponly=True, secure=True, samesite='Strict')

        # Ensure the response is returned
        return resp

    else:  # Invalid username or password
        return "Invalid username or password"


@app.route("/home")
def home():
    if 'logged_in' in session:
        return render_template("home.html", username=session['username'])
    return redirect(url_for('login_page'))

@app.route("/logout")
def logout():
    # Clear Flask session
    session.clear()

    # Create response for redirection
    resp = make_response(redirect(url_for("login_page")))

    # Remove the authentication cookie
    resp.set_cookie('auth_token', '', expires=0, httponly=True, secure=True, samesite='Strict')

    # Optional: Debugging log to verify logout flow
    app.logger.info("User logged out and session cleared.")

    return resp


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        otp = generate_otp()
        send_otp(email, otp)
        return render_template("verify.html", username=username, password=password, email=email, otp=otp)
    return render_template("register.html")

@app.route("/verify", methods=["POST"])
def verify():
    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]
    otp = request.form["otp"]
    entered_otp = request.form["entered_otp"]
    
    if otp == entered_otp:
        query = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
        mycursor.execute(query, (username, password, email))
        mydb.commit()
        return redirect(url_for("login_page"))
    else:
        return "Invalid OTP"

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form["email"]
        query = "SELECT * FROM users WHERE email = %s"
        mycursor.execute(query, (email,))
        user = mycursor.fetchone()
        if user:
            otp = generate_otp()
            send_otp(email, otp)
            return render_template("reset.html", email=email, otp=otp)
        else:
            return "Email not registered"
    return render_template("forget.html")

@app.route("/reset", methods=["POST"])
def reset():
    email = request.form["email"]
    password = request.form["password"]
    otp = request.form["otp"]
    entered_otp = request.form["entered_otp"]

    if otp == entered_otp:
        query = "UPDATE users SET password = %s WHERE email = %s"
        mycursor.execute(query, (password, email))
        mydb.commit()
        return redirect(url_for("login_page"))
    return "Invalid OTP"


@app.route('/search_record', methods=['GET', 'POST'])
def search_record():
    query = """
        SELECT * FROM patientdetails 
        WHERE hospital_id = %s 
        AND (Name LIKE %s OR phone_number LIKE %s OR Age LIKE %s OR Sex LIKE %s 
        OR Diagnosis LIKE %s OR Treatment LIKE %s OR Next_appointment_date LIKE %s) 
        ORDER BY Patient_ID DESC
    """
    current_time = datetime.now()
    hospital_id = session.get('hospital_id')
    user_type = session.get('user_type')
    doctor_name = session.get('doctor_name')
    doctor_photo = session.get('doctor_photo')
    doctors = session.get('doctors')
    
    if not hospital_id:
        return "Hospital ID not found in session.", 400

    if request.method == 'POST':
        search_term = "%" + request.form.get('searchInput', '') + "%"
        try:
            cursor = mydb.cursor()
            cursor.execute(query, (hospital_id, search_term, search_term, search_term, search_term, search_term, search_term, search_term))
            results = cursor.fetchall()
        finally:
            cursor.close()
        
        if user_type == "Doctor":
            return render_template(
                "dashboard.html",
                current_time=current_time,
                greeting=f"Hello, Dr. {doctor_name}",
                doctor_name=doctor_name,
                doctor_photo=doctor_photo,
                doctors=doctors,
                patient_details=results,
                user_type=user_type
            )
        else:
            return render_template(
                'home.html',
                hospital_id=hospital_id,
                patient_details=results,
                user_type=user_type,
                doctor_name=doctor_name
            )
    
    return render_template('search_page.html')

@app.route('/add', methods=['POST', 'GET'])
def add_record():
    if request.method == 'POST':
        # Retrieve and validate form data
        data = {
            "name": request.form.get("name"),
            "phone_number": request.form.get("phone"),
            "age": request.form.get("age"),
            "sex": request.form.get("sex"),
            "diagnosis": request.form.get("diagnosis"),
            "treatment": request.form.get("treatment"),
            "feedback": request.form.get("feedback"),
            "next_appointment": request.form.get("next_appointment")
        }

        # Check if any required field is missing
        if not all(data.values()):
            flash("Please fill in all required fields.", "error")
            return render_template("add_new_record.html")

        # Convert and validate age field
        try:
            data["age"] = int(data["age"])
        except ValueError:
            flash("Please enter a valid age.", "error")
            return render_template("add_new_record.html")

        # Retrieve user's ID and hospital ID from session
        username = session.get('username')
        hospital_id = session.get('hospital_id')

        if not username or not hospital_id:
            flash("User or hospital information is missing from the session. Please log in again.", "error")
            return redirect(url_for('login_page'))

        # Get the current timestamp and set expiration time
        created_time = datetime.now()
        expire_time = created_time + timedelta(days=1)  # For example, expire in 1 day

        # Insert patient details
        query = """
            INSERT INTO patientdetails (
                username, hospital_id, Name, phone_number, Age, sex, Diagnosis, Treatment, 
                Next_appointment_date, feedback, created_time, expire_time
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            cursor = mydb.cursor()
            cursor.execute(query, (
                username, hospital_id, data["name"], data["phone_number"], data["age"], 
                data["sex"], data["diagnosis"], data["treatment"], data["next_appointment"], 
                data["feedback"], created_time, expire_time
            ))
            mydb.commit()
            flash("Patient record added successfully.", "success")
            return redirect(url_for("home"))
        except Exception as e:
            mydb.rollback()
            flash(f"An error occurred while adding the record: {str(e)}", "error")
            return render_template("add_new_record.html")
        finally:
            cursor.close()

    return render_template("add_new_record.html")

@app.route('/validate_token', methods=['POST'])
def validate_token():
    token = request.json.get('token')
    query = "SELECT * FROM sessions WHERE token = %s"
    mycursor.execute(query, (token,))
    token_db = mycursor.fetchone()

    if token_db:
        
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'Invalid token'})

if __name__ == '__main__':
    app.run(host='192.168.29.184',port=5000,debug=True)
