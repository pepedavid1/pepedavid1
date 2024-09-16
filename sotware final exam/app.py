from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flaskwebgui import FlaskUI

# Initialize Flask app and configure the SQLite database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///clinic.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Patient model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    matricule = db.Column(db.String(20), unique=True, nullable=False)

# Define the Appointment model
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    appointment_time = db.Column(db.DateTime, nullable=False)

    # Establish relationship with Patient
    patient = db.relationship('Patient', backref=db.backref('appointments', lazy=True))

# Create the SQLite database directly in app startup
with app.app_context():
    db.create_all()

# Function to generate unique matricules
def generate_matricule():
    last_patient = Patient.query.order_by(Patient.id.desc()).first()
    if last_patient:
        last_matricule = int(last_patient.matricule.split('-')[1])
        new_matricule = f"PAT-{last_matricule + 1:04d}"
    else:
        new_matricule = "PAT-0001"
    return new_matricule

# Function to generate a weekly schedule with 2-hour appointment slots
def generate_schedule(start_date):
    schedule = []
    start_time = datetime(start_date.year, start_date.month, start_date.day, 8, 0)  # 8:00 AM
    end_time = datetime(start_date.year, start_date.month, start_date.day, 16, 30)  # 4:30 PM

    for day in range(5):  # Monday to Friday (0 to 4)
        current_day_start_time = start_time + timedelta(days=day)
        current_time = current_day_start_time
        while current_time < current_day_start_time.replace(hour=16, minute=30):
            schedule.append(current_time)
            current_time += timedelta(hours=2)  # 2-hour slots
    return schedule

# Function to assign the first available appointment time from the schedule
def assign_rendezvous(schedule, patient):
    existing_appointments = Appointment.query.with_entities(Appointment.appointment_time).all()
    existing_times = [appointment_time[0] for appointment_time in existing_appointments]

    for time_slot in schedule:
        if time_slot not in existing_times:
            return time_slot  # Return the first available time slot
    return None  # Return None if no available time slots are found

# Route for the main page where you can register patients
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get form data
        name = request.form.get("name")
        phone = request.form.get("phone")
        address = request.form.get("address")

        # Register the patient
        matricule = generate_matricule()  # Generate a unique matricule
        new_patient = Patient(name=name, phone=phone, address=address, matricule=matricule)
        db.session.add(new_patient)
        db.session.commit()

        # Generate the schedule and assign a rendezvous
        schedule_start_date = datetime.now()
        schedule = generate_schedule(schedule_start_date)
        appointment_time = assign_rendezvous(schedule, new_patient)

        # Create and save the appointment
        new_appointment = Appointment(patient_id=new_patient.id, appointment_time=appointment_time)
        db.session.add(new_appointment)
        db.session.commit()

        # Redirect to the schedule page after registering
        return redirect(url_for("schedule"))

    return render_template("index.html")

# Route to display the schedule
@app.route("/schedule")
def schedule():
    appointments = Appointment.query.all()
    return render_template("schedule.html", appointments=appointments)

# Run the application
if __name__ == "__main__":
    FlaskUI(app=app, server="flask").run()