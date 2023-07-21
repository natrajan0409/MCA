from curses import flash
from datetime import datetime
import smtplib
import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import random
from flask import Flask, render_template, request, redirect, session, url_for
from smtplib import SMTP_SSL
from email.message import EmailMessage
from datetime import datetime



app = Flask(__name__)

user_session =None;
hospital_id=None;



# Connect to the database
# mydb = mysql.connector.connect(**db_config)
mydb = mysql.connector.connect(
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)


# Create a cursor object
mycursor = mydb.cursor()


def send_otp(email, otp):
    message = EmailMessage()
    message['From'] = 'cksoftware@yahoo.com'
    message['To'] = email
    message['Subject'] = 'Your OTP for Password Reset'
    message.set_content(f'Your OTP is {otp}')

    with smtplib.SMTP_SSL("smtp.mail.yahoo.com", 465) as server:
        server.login("cksoftware@yahoo.com", "evmlhhupbpriumoz")
        server.send_message(message)


def generate_otp():
  return random.randint(100000, 999999)

def generate_hospital_id(hospital_name):
    # Generate a random integer between 10000 and 99999 as the unique identifier
    unique_identifier = random.randint(10000, 99999)
    
    # Combine the hospital name and unique identifier to create the hospital ID
    hospital_id = f"{hospital_name}_{unique_identifier}"
    
    return hospital_id



@app.route("/")
def login_page():
  return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    data = {
        "username": request.form["username"],
        "password": request.form["password"]
    }
    global user_session
    user_session = data["username"]
    user_type = get_user_type(user_session)
    
    query = "SELECT * FROM users WHERE username = %s AND password = %s"
    mycursor.execute(query, (data["username"], data["password"]))
    user = mycursor.fetchone()
    
    if user:
        
        if user_type == "Doctor":
            return redirect(url_for("doctor_dashboard"))
        else:
            return redirect(url_for("home"))
    else:
        return "Invalid username or password"
    

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = {
            "username": request.form["username"],
            "password": request.form["password"],
            "email": request.form["email"],
            "hospital_name": request.form["hospital_name"],
            "location": request.form["location"],
            "otp": generate_otp(),
            "hospital_id":generate_hospital_id(request.form["hospital_name"])
        }
        send_otp(data["email"], data["otp"])
        return render_template("verify.html", **data)
    else:
        return render_template("register.html")
    
@app.route("/verify", methods=["POST"])
def verify():
    data = {
        "username": request.form["username"],
        "password": request.form["password"],
        "email": request.form["email"],
        "hospital_name": request.form["hospital_name"],
        "location": request.form["location"],
        "otp": request.form["otp"],
        "entered_otp": request.form["entered_otp"],
        "user_type": "Admin",  # Hardcoded user_type as "Admin"
        "hospital_id": request.form["hospital_id"]
    }

    if data["otp"] == data["entered_otp"]:
        query = "INSERT INTO users (username, password, email, user_type,hospital_id) VALUES (%s, %s, %s, %s,%s)"
        mycursor.execute(query, (data["username"], data["password"], data["email"], data['user_type'],data['hospital_id']))
        mydb.commit()

        query2 = "INSERT INTO hospitals (hospital_name, location,hospital_id) VALUES (%s,%s,%s)"
        mycursor.execute(query2, (data["hospital_name"], data["location"],data['hospital_id']))
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
  else:
    return render_template("forget.html")

@app.route("/reset", methods=["POST"])
def reset():
  data = {
    "email": request.form["email"],
    "password": request.form["password"],
    "otp": request.form["otp"],
    "entered_otp": request.form["entered_otp"]
  }
  if data["otp"] == data["entered_otp"]:
    query = "UPDATE users SET password = %s WHERE email = %s"
    mycursor.execute(query, (data["password"], data["email"]))
    mydb.commit()
    return redirect(url_for("login_page"))
  else:
    return "Invalid OTP"

def get_user_type(user_id):
    query = "SELECT user_type FROM users WHERE username = %s"
    mycursor.execute(query, (user_id,))
    user_type = mycursor.fetchone()
    # mycursor.close()
    if user_type:
        return user_type[0]
    else:
        return None

def get_login_user(user_id):
    query = "SELECT username FROM users WHERE username = %s"
    mycursor.execute(query, (user_id,))
    username = mycursor.fetchone()
    # mycursor.close()
    if username:
        return username[0]
    else:
        return None




def get_hospital_id(user_id):
    query = "SELECT hospital_id FROM users WHERE username = %s"
    mycursor.execute(query, (user_id,))
    hospital_id = mycursor.fetchone()
    # mycursor.close()
    if hospital_id:
        return hospital_id[0]
    else:
        return None




def get_patient_details_for_user(hospital_id):
    query = "SELECT * FROM patientdetails WHERE hospital_id = %s ORDER BY Patient_ID DESC LIMIT 50"
    mycursor.execute(query, (hospital_id,))
    rows = mycursor.fetchall()
    return rows

  
def get_patient_history(name):
    query = "select diagnosis,treatment,visit_date from patienthistory WHERE name = %s"
    mycursor.execute(query, (name,))
    patient_history = mycursor.fetchall()
    return patient_history

@app.route("/home", methods=['GET', 'POST'])
def home():
    user_type = get_user_type(user_session)
    hospital_id = get_hospital_id(user_session)
    patient_details = get_patient_details_for_user(hospital_id)  # Assuming you have a function to retrieve patient details based on hospital_id.
    print("User Type:", user_type)
    print("patient_details:", patient_details)
    return render_template("home.html", hospital_id=hospital_id, patient_details=patient_details, user_type=user_type)

@app.route('/add', methods=['POST'])
def add_record():
    if request.method == 'POST':
        data = {
            "name": request.form.get("name"),
            "phone_number": request.form.get("phone"),
            "age": int(request.form.get("age")),
            "sex": request.form.get("sex"),
            "diagnosis": request.form.get("diagnosis"),
            "treatment": request.form.get("treatment"),
             "feedback": request.form.get("feedback"),
            "next_appointment": request.form.get("next_appointment")
        }

        # Retrieve user's ID from the session
        username = user_session

        # Retrieve hospital ID from the session
        hospital_id = get_hospital_id(username)

        # Insert patient details for the user's ID and hospital ID
        query = "INSERT INTO patientdetails (username, hospital_id, Name, phone_number, Age, sex, Diagnosis, Treatment, Next_appointment_date,feedback) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        mycursor.execute(query, (username, hospital_id, data["name"], data["phone_number"], data["age"], data["sex"], data["diagnosis"], data["treatment"], data["next_appointment"], data["feedback"]))
        mydb.commit()

        return redirect(url_for("home"))

    return render_template("add_new_record.html")

@app.route('/modify')
def modify():
    # Extract the parameters from the URL
    name = request.args.get('name', '')
    phone = request.args.get('phone', '')
    age = request.args.get('age', '')
    gender = request.args.get('gender', '')
    diagnosis = request.args.get('diagnosis', '')
    treatment = request.args.get('treatment', '')
    Next_appointment_date = request.args.get('date', '')
    feedback = request.args.get('feedback', '')

    # Retrieve the hospital_id from the session (assuming you have a function to get it)
    hospital_id = get_hospital_id(user_session)

    # Retrieve the patient details from the database
    query = "SELECT * FROM patientdetails WHERE hospital_id = %s AND name = %s AND phone_number = %s AND age = %s AND Sex = %s AND diagnosis = %s AND treatment = %s AND Next_appointment_date = %s AND feedback = %s"
    mycursor.execute(query, (hospital_id, name, phone, age, gender, diagnosis, treatment, Next_appointment_date, feedback))
    patient_details = mycursor.fetchone()

    # Retrieve the patient history from the database
    patient_history = get_patient_history(name)

    # Get the user_type from the session
    user_type = get_user_type(user_session)

    # Render the modify.html template and pass the parameters and patient details
    return render_template('modify.html', name=name, phone=phone, age=age, gender=gender, diagnosis=diagnosis, treatment=treatment, date=Next_appointment_date, feedback=feedback, patient_details=patient_details, history=patient_history, user_type=user_type)




@app.route('/update_record', methods=['POST'])
def update_record():
    name = request.form.get('name')
    phone_number = request.form.get('phone')
    age = request.form.get('age')
    Sex = request.form.get('gender')
    diagnosis = request.form.get('diagnosis')
    treatment = request.form.get('treatment')
    Next_appointment_date = request.form.get('date')
    feedback = request.form.get('feedback')  # Move this line up to extract the feedback value

    # Retrieve user's ID from the session
    username = user_session
    user_type = get_user_type(user_session)

    # Retrieve hospital ID from the session
    hospital_id = get_hospital_id(username)

    # Prepare the UPDATE query
    query = "UPDATE patientdetails SET phone_number = %s, age = %s, Sex = %s, diagnosis = %s, treatment = %s, Next_appointment_date = %s, feedback = %s WHERE name = %s AND username = %s AND hospital_id = %s"

    # Execute the query and commit the changes
    mycursor.execute(query, (phone_number, age, Sex, diagnosis, treatment, Next_appointment_date, feedback, name, username, hospital_id))  # Corrected the order of the parameters
    mydb.commit()

    # Update the patient history in the database
    visit_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mycursor.execute("INSERT INTO patienthistory (name, treatment, visit_date, diagnosis, feedback, hospital_id) VALUES (%s, %s, %s, %s, %s, %s)", (name, treatment, visit_date, diagnosis, feedback, hospital_id))
    mydb.commit()

    # Redirect to the home page
    if user_type == "Doctor":
            return redirect(url_for("doctor_dashboard"))
    else:
            return redirect(url_for("home"))



  
@app.route('/delete_record', methods=['POST'])
def delete_record():
    name = request.form.get('name')
    # print(Patient_ID)
    mycursor.execute("DELETE FROM patientdetails WHERE Name = %s", (name,))
    mydb.commit()
    # Redirect to the home page
    return redirect(url_for("home"))
 
 
@app.route('/search_record', methods=['GET', 'POST'])
def search_record():
 
    if request.method == 'POST':
        search_term = "%" + request.form['searchInput'] + "%"
        cursor = mydb.cursor()
        query = "SELECT * FROM patientdetails WHERE username = %s AND (Name LIKE %s OR phone_number LIKE %s OR Age LIKE %s OR Sex LIKE %s OR Diagnosis LIKE %s OR Treatment LIKE %s OR Next_appointment_date LIKE %s) ORDER BY Patient_ID Desc"
        cursor.execute(query, (user_session, search_term, search_term, search_term, search_term, search_term, search_term, search_term))
        results = cursor.fetchall()
        return render_template('home.html', patient_details=results)
    else:
        name = request.args.get('searchInput')
        if name is None:
            return redirect(url_for('home'))
        search_term = "%" + name + "%"
        cursor = mydb.cursor()
        query = "SELECT * FROM patientdetails WHERE username = %s AND (Name LIKE %s OR phone_number LIKE %s OR Age LIKE %s OR Sex LIKE %s OR Diagnosis LIKE %s OR Treatment LIKE %s OR Next_appointment_date LIKE %s) ORDER BY Patient_ID Desc"
        cursor.execute(query, (user_session, search_term, search_term, search_term, search_term, search_term, search_term, search_term))
        results = cursor.fetchall()
        return render_template('home.html', patient_details=results)


@app.route('/dashboard.html')
def doctor_dashboard():
    current_time = datetime.now()
    greeting = get_time_greeting(current_time)
    doctor_name = get_login_user(user_session)  # Replace with actual doctor name
    doctor_photo = "defaut_pic.jpg"   # Replace with the path to the doctor's photo

    # Assuming the get_doctors_in_same_hospital function takes the hospital_id as an argument
    hospital_id = get_hospital_id(user_session)
    doctors = get_doctors_in_same_hospital(hospital_id)


    user_type = get_user_type(user_session)
    hospital_id = get_hospital_id(user_session)
    patient_details = get_patient_details_for_user(hospital_id)  # Assuming you have a function to retrieve patient details based on hospital_id.
    print("User Type:", user_type)
    print("patient_details:", patient_details)
    # return render_template("home.html", hospital_id=hospital_id, patient_details=patient_details, user_type=user_type)


    # Assuming the get_all_patients function takes the hospital_id as an argument


    return render_template(
        "dashboard.html",
        current_time=current_time,
        greeting=greeting,
        doctor_name=doctor_name,
        doctor_photo=doctor_photo,
        doctors=doctors,
        patient_details=patient_details,
        user_type=user_type
    )

    
def get_time_greeting(current_time):
    hour = current_time.hour
    if 5 <= hour < 12:
        greeting = "Morning"
    elif 12 <= hour < 18:
        greeting = "Afternoon"
    else:
        greeting = "Evening"
    return greeting
  
  
def get_doctors_in_same_hospital(hospital_id):
    query = "SELECT doctor_name FROM Doctors_Records WHERE hospital_id = %s ORDER BY id DESC LIMIT 50"
    mycursor.execute(query, (hospital_id,))
    rows = mycursor.fetchall()
    return rows



  
 
@app.route('/Search_Patient', methods=['GET', 'POST'])
def SearchPatient():
    current_time = datetime.now()
    greeting = get_time_greeting(current_time)
    doctor_name = get_login_user(user_session) # Replace with actual doctor name
    doctor_photo = "D:\VS workspace\08-04-2023\static\defaut_pic.jpg"  # Replace with the path to the doctor's photo

    # Assuming the get_doctors_in_same_hospital function takes the hospital_id as an argument
    hospital_id = get_hospital_id(user_session)
    doctors = get_doctors_in_same_hospital(hospital_id)

    # Assuming the get_all_patients function takes the hospital_id as an argument
    patients = get_patient_details_for_user(hospital_id)
 
    if request.method == 'POST':
        search_term = "%" + request.form['patient_name'] + "%"
        cursor = mydb.cursor()
        query = "SELECT * FROM patientdetails WHERE username = %s AND (Name LIKE %s OR phone_number LIKE %s OR Age LIKE %s OR Sex LIKE %s OR Diagnosis LIKE %s OR Treatment LIKE %s OR Next_appointment_date LIKE %s) ORDER BY Patient_ID Desc"
        cursor.execute(query, (hospital_id, search_term, search_term, search_term, search_term, search_term, search_term, search_term))
        results = cursor.fetchall()
        return render_template(
        "dashboard.html",
        current_time=current_time,
        greeting=greeting,
        doctor_name=doctor_name,
        doctor_photo=doctor_photo,
        doctors=doctors,
        patients=patients
    )
    else:
        name = request.args.get('patient_name')
        if name is None:
            return redirect(url_for('home'))
        search_term = "%" + name + "%"
        cursor = mydb.cursor()
        query = "SELECT * FROM patientdetails WHERE username = %s AND (Name LIKE %s OR phone_number LIKE %s OR Age LIKE %s OR Sex LIKE %s OR Diagnosis LIKE %s OR Treatment LIKE %s OR Next_appointment_date LIKE %s) ORDER BY Patient_ID Desc"
        cursor.execute(query, (hospital_id, search_term, search_term, search_term, search_term, search_term, search_term, search_term))
        results = cursor.fetchall()
        return render_template(
        "dashboard.html",
        current_time=current_time,
        greeting=greeting,
        doctor_name=doctor_name,
        doctor_photo=doctor_photo,
        doctors=doctors,
        patients=patients
    )

@app.route("/role", methods=["GET", "POST"])
def role_page():
    if request.method == "GET":
        # Render the HTML page for the form
        return render_template("Role.html")

    # POST request handling
    # Extract the form data
    username = request.form["username"]
    password = request.form["password"]
    email = request.form["email"]
    role = request.form["role"]
    specialization = request.form["specialization"]
    contact_number = request.form["contact_number"]
    
    # Validate the form data (you can add more validation if required)
    if not username or not password or not email or not role:
        return "Please fill out all fields."

    # Check if the username is already taken
    user_session = get_login_user(username)
    if username in user_session:
        return "Username already exists. Please choose a different username."

    # Store the sub-user data in the dictionary (you can replace this with database insertion)
    user_session[username] = {
        "password": password,
        "specialization": specialization,
        "contact_number": contact_number,
        "role": role,
        "email": email,
    }
    # Get the user_type from the session
    user_type = get_user_type(user_session)

    query = "INSERT INTO users (username, password, email, user_type, hospital_id) VALUES (%s, %s, %s, %s, %s)"
    mycursor.execute(query, (username, password, email, role, hospital_id))
    mydb.commit()

    if role == "Doctor":
        query2 = "INSERT INTO doctors_records (doctor_name, specialization, contact_number, email, hospital_id) VALUES (%s, %s, %s, %s, %s)"
        mycursor.execute(query2, (username, specialization, contact_number, email, hospital_id))
        mydb.commit()

    # Redirect to a success page or any other desired page
    return redirect("/success")

  
if __name__ == '__main__':
  app.run(debug=True)
