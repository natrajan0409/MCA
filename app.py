from curses import flash
from datetime import datetime
import smtplib
import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import random
from flask import Flask, render_template, request, redirect, session, url_for
from smtplib import SMTP_SSL
from email.message import EmailMessage



app = Flask(__name__)

user_session =None;


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
  user_session=data["username"]
  query = "SELECT * FROM users WHERE username = %s AND password = %s"
  mycursor.execute(query, (data["username"], data["password"]))
  user = mycursor.fetchone()
  if user:
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
      "otp": generate_otp()
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
    "otp": request.form["otp"],
    "entered_otp": request.form["entered_otp"]
  }
  if data["otp"] == data["entered_otp"]:
    query = "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)"
    mycursor.execute(query, (data["username"], data["password"], data["email"]))
    mydb.commit()
    return redirect(url_for("home"))
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
    return redirect(url_for("home"))
  else:
    return "Invalid OTP"

def get_patient_details_for_user(user_id):
    query = "SELECT * FROM patientdetails WHERE username = %s ORDER BY Patient_ID DESC LIMIT 50"
    mycursor.execute(query, (user_id,))
    rows = mycursor.fetchall()
    return rows
  
def get_patient_history(name):
    query = "select diagnosis,treatment,visit_date from patienthistory WHERE name = %s"
    mycursor.execute(query, (name,))
    patient_history = mycursor.fetchall()
    return patient_history

@app.route("/home",methods=['GET', 'POST'])
def home():
  
    patient_details = get_patient_details_for_user(user_session)
    print("home"+user_session)
    return render_template("home.html", username=user_session,patient_details=patient_details)


# Add a new record to the database
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
            "next_appointment": request.form.get("next_appointment")
        }

        # Retrieve user's ID from the session
        username= user_session
        print("add records"+username)

        # Insert patient details for the user's ID
        query = "INSERT INTO patientdetails (username, Name, phone_number, Age, sex, Diagnosis, Treatment, Next_appointment_date)VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        mycursor.execute(query, (username,data["name"], data["phone_number"], data["age"], data["sex"], data["diagnosis"], data["treatment"], data["next_appointment"]))
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
    
    # Retrieve the patient details from the database
    query = "SELECT * FROM patientdetails WHERE username = %s AND name = %s AND phone_number = %s AND age = %s AND Sex = %s AND diagnosis = %s AND treatment = %s AND Next_appointment_date = %s"
    mycursor.execute(query, (user_session, name, phone, age, gender, diagnosis, treatment, Next_appointment_date))
    patient_details = mycursor.fetchone()
    
     # Retrieve the patient history from the database
    patient_history =get_patient_history(name)
    print(patient_history)
    
    # Render the modify.html template and pass the parameters and patient details
    return render_template('modify.html', name=name, phone=phone, age=age, gender=gender, diagnosis=diagnosis, treatment=treatment, date=Next_appointment_date, patient_details=patient_details, history=patient_history)




@app.route('/update_record', methods=['POST'])
def update_record():
    name = request.form.get('name')
    phone_number = request.form.get('phone')
    age = request.form.get('age')
    Sex = request.form.get('gender')
    diagnosis = request.form.get('diagnosis')
    treatment = request.form.get('treatment')
    Next_appointment_date = request.form.get('date')
    
    # Retrieve user's ID from the session
    username= user_session
    
    # Prepare the UPDATE query
    query = "UPDATE patientdetails SET phone_number = %s, age = %s, Sex = %s, diagnosis = %s, treatment = %s, Next_appointment_date = %s WHERE name = %s AND username = %s"

     # Execute the query and commit the changes
    mycursor.execute(query, (phone_number, age, Sex, diagnosis, treatment, Next_appointment_date, name, username))
    mydb.commit()

    # Update the patient history in the database
    visit_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    feedback = request.form.get('feedback')
    mycursor.execute("INSERT INTO patienthistory (name, treatment, visit_date, diagnosis, feedback) VALUES (%s, %s, %s, %s, %s)", (name, treatment, visit_date, diagnosis, feedback))
    mydb.commit()

   

    # Redirect to the home page
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

if __name__ == '__main__':
  app.run(debug=True)
