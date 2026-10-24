from flask import (
    Flask, request, redirect, url_for,
    session, render_template_string, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json
import os
import re
from functools import wraps

app = Flask(__name__)

# Demo secret key. Change this before deployment.
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "change-this-secret-key-before-deployment"
)

BASE_DIR = app.root_path
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATA_FILE = os.path.join(BASE_DIR, "applications.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# JSON HELPERS
def read_json(filename):
    if not os.path.exists(filename):
        return []

    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def write_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


# HOME PAGE
@app.route("/")
def home():
    user = session.get("user_email", "")
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Job Portal Management</title>
        <style>
            body {
                margin: 0;
                font-family: Arial;
                background: #f0f4f8;
                color: #333;
            }
            nav {
                background: #123b69;
                color: white;
                padding: 20px;
                text-align: center;
            }
            nav a {
                color: white;
                margin: 8px;
                text-decoration: none;
            }
            .hero {
                text-align: center;
                padding: 70px 20px;
            }
            h1 { color: #123b69; }
            .btn {
                display: inline-block;
                background: #123b69;
                color: white;
                padding: 12px 22px;
                text-decoration: none;
                border-radius: 5px;
                margin: 5px;
            }
            footer {
                text-align: center;
                padding: 20px;
                background: #123b69;
                color: white;
            }
        </style>
    </head>
    <body>
        <nav>
            <h2>JobPortal</h2>
            <a href="/">Home</a>
            <a href="/jobs">Search Jobs</a>
            {% if user %}
                <span>Welcome, {{ user }}</span>
                <a href="/logout">Logout</a>
            {% else %}
                <a href="/register">Register</a>
                <a href="/login">Login</a>
            {% endif %}
        </nav>

        <div class="hero">
            <h1>Find Your Dream Job</h1>
            <p>Discover exciting career opportunities.</p>
            <p>Connect with employers and build your future.</p>
            <a class="btn" href="/jobs">Explore Jobs</a>
            {% if not user %}
                <a class="btn" href="/register">Create Account</a>
            {% endif %}
        </div>

        <footer>Job Portal Management System</footer>
    </body>
    </html>
    """, user=user)


# USER REGISTRATION
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not name or not email or not password:
            message = "Please fill all fields."
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            message = "Please enter a valid email address."
        elif len(password) < 8:
            message = "Password must be at least 8 characters."
        elif password != confirm:
            message = "Passwords do not match."
        else:
            users = read_json(USERS_FILE)

            if any(u.get("email") == email for u in users):
                message = "This email is already registered."
            else:
                users.append({
                    "name": name,
                    "email": email,
                    "password_hash": generate_password_hash(password)
                })
                write_json(USERS_FILE, users)
                return redirect(url_for("login", registered="1"))

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Registration</title>
        <style>
            body {
                font-family: Arial;
                background: #f0f4f8;
                padding: 30px;
            }
            .box {
                max-width: 420px;
                background: white;
                padding: 25px;
                margin: 30px auto;
                border-radius: 10px;
                box-shadow: 0 2px 8px #ccc;
            }
            input {
                width: 95%;
                padding: 11px;
                margin: 8px 0 15px;
                box-sizing: border-box;
            }
            button {
                background: #123b69;
                color: white;
                padding: 12px;
                border: none;
                width: 100%;
                cursor: pointer;
            }
            .error { color: #c62828; }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>Create Account</h1>
            {% if message %}<p class="error">{{ message }}</p>{% endif %}

            <form method="POST">
                <label>Full Name</label>
                <input type="text" name="name" required
                       value="{{ request.form.get('name', '') }}">

                <label>Email</label>
                <input type="email" name="email" required
                       value="{{ request.form.get('email', '') }}">

                <label>Password (minimum 8 characters)</label>
                <input type="password" name="password"
                       minlength="8" required>

                <label>Confirm Password</label>
                <input type="password" name="confirm_password"
                       minlength="8" required>

                <button type="submit">Register</button>
            </form>

            <p>Already registered? <a href="/login">Login</a></p>
            <a href="/">Back to Home</a>
        </div>
    </body>
    </html>
    """, message=message)


# USER LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    if request.args.get("registered") == "1":
        message = "Registration successful! Please log in."

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        users = read_json(USERS_FILE)
        user = next(
            (u for u in users if u.get("email") == email),
            None
        )

        if user and check_password_hash(
            user.get("password_hash", ""), password
        ):
            session.clear()
            session["user_email"] = user["email"]
            session["user_name"] = user["name"]
            return redirect(url_for("home"))

        message = "Invalid email or password."

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Login</title>
        <style>
            body {
                font-family: Arial;
                background: #f0f4f8;
                padding: 30px;
            }
            .box {
                max-width: 420px;
                background: white;
                padding: 25px;
                margin: 30px auto;
                border-radius: 10px;
                box-shadow: 0 2px 8px #ccc;
            }
            input {
                width: 95%;
                padding: 11px;
                margin: 8px 0 15px;
                box-sizing: border-box;
            }
            button {
                background: #123b69;
                color: white;
                padding: 12px;
                border: none;
                width: 100%;
                cursor: pointer;
            }
            .error { color: #c62828; }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>User Login</h1>
            {% if message %}<p class="error">{{ message }}</p>{% endif %}

            <form method="POST">
                <label>Email</label>
                <input type="email" name="email" required>

                <label>Password</label>
                <input type="password" name="password" required>

                <button type="submit">Login</button>
            </form>

            <p>New user? <a href="/register">Register here</a></p>
            <a href="/">Back to Home</a>
        </div>
    </body>
    </html>
    """, message=message)


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# AVAILABLE JOBS
@app.route("/jobs")
def jobs():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Available Jobs</title>
        <style>
            body {
                font-family: Arial;
                background: #f0f4f8;
                padding: 30px;
            }
            h1 { color: #123b69; text-align: center; }
            .job {
                background: white;
                padding: 20px;
                margin: 20px auto;
                max-width: 500px;
                border-radius: 10px;
                box-shadow: 0 2px 8px #ccc;
            }
            button {
                background: #123b69;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            input {
                padding: 10px;
                width: 95%;
                box-sizing: border-box;
            }
            .form-box {
                background: white;
                padding: 20px;
                margin: 30px auto;
                max-width: 500px;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <h1>Available Jobs</h1>

        <div class="job">
            <h2>Python Developer</h2>
            <p>Company: Tech Solutions</p>
            <p>Location: Pune</p>
            <button onclick="openForm('Python Developer')">
                Apply Now
            </button>
        </div>

        <div class="job">
            <h2>Web Developer</h2>
            <p>Company: Web Technologies</p>
            <p>Location: Mumbai</p>
            <button onclick="openForm('Web Developer')">
                Apply Now
            </button>
        </div>

        <div id="applicationForm" class="form-box"
             style="display:none;">
            <h2>Job Application Form</h2>

            <form action="/apply" method="POST"
                  enctype="multipart/form-data">
                <p>Selected Job</p>
                <input type="text" id="jobName" readonly>
                <input type="hidden" name="job" id="jobValue">

                <p>Full Name</p>
                <input type="text" name="fullname" required>

                <p>Email</p>
                <input type="email" name="email" required>

                <p>Phone Number</p>
                <input type="tel" name="phone"
                       pattern="[0-9]{10}" maxlength="10" required>

                <p>Upload Resume (PDF, DOC, DOCX)</p>
                <input type="file" name="resume"
                       accept=".pdf,.doc,.docx" required>

                <br><br>
                <button type="submit">Submit Application</button>
            </form>
        </div>

        <br><a href="/">Back to Home</a>

        <script>
        function openForm(jobName) {
            document.getElementById("applicationForm")
                .style.display = "block";
            document.getElementById("jobName").value = jobName;
            document.getElementById("jobValue").value = jobName;
            document.getElementById("applicationForm")
                .scrollIntoView({behavior: "smooth"});
        }
        </script>
    </body>
    </html>
    """)


# SUBMIT APPLICATION AND SAVE DATA
@app.route("/apply", methods=["POST"])
def apply():
    name = request.form.get("fullname", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    job = request.form.get("job", "").strip()
    resume = request.files.get("resume")

    if not all([name, email, phone, job]):
        return "Please fill in all application fields.", 400

    if not re.fullmatch(r"[0-9]{10}", phone):
        return "Please enter a valid 10-digit phone number.", 400

    if not resume or not resume.filename:
        return "Please upload your resume.", 400

    filename = secure_filename(resume.filename)
    extension = os.path.splitext(filename)[1].lower()

    if extension not in [".pdf", ".doc", ".docx"]:
        return "Upload a PDF, DOC or DOCX resume.", 400

    base, ext = os.path.splitext(filename)
    counter = 1

    while os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
        filename = f"{base}_{counter}{ext}"
        counter += 1

    resume.save(os.path.join(UPLOAD_FOLDER, filename))

    applications = read_json(DATA_FILE)
    applications.append({
        "name": name,
        "email": email,
        "phone": phone,
        "job": job,
        "resume": filename
    })
    write_json(DATA_FILE, applications)

    return render_template_string("""
    <h2>Application Submitted Successfully!</h2>
    <p>Job: {{ job }}</p>
    <p>Name: {{ name }}</p>
    <p>Email: {{ email }}</p>
    <p>Phone: {{ phone }}</p>
    <p>Resume: {{ resume }}</p>
    <a href="/jobs">Back to Jobs</a> |
    <a href="/">Home</a>
    """, job=job, name=name, email=email,
       phone=phone, resume=filename)


# ADMIN DASHBOARD
@app.route("/admin")
def admin():
    applications = read_json(DATA_FILE)

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard</title>
        <style>
            body { font-family: Arial; background: #f0f4f8; padding: 20px; }
            table { width: 100%; background: white; border-collapse: collapse; }
            th, td { border: 1px solid #ccc; padding: 10px; text-align: left; }
            th { background: #123b69; color: white; }
        </style>
    </head>
    <body>
        <h1>Admin Dashboard</h1>
        <h3>Total Applications: {{ applications|length }}</h3>
        <table>
            <tr>
                <th>Name</th><th>Email</th><th>Phone</th>
                <th>Job</th><th>Resume</th>
            </tr>
            {% for item in applications %}
            <tr>
                <td>{{ item.get('name', '') }}</td>
                <td>{{ item.get('email', '') }}</td>
                <td>{{ item.get('phone', '') }}</td>
                <td>{{ item.get('job', '') }}</td>
                <td>
                    <a href="{{ url_for('view_resume',
                    filename=item.get('resume', '')) }}">View Resume</a>
                </td>
            </tr>
            {% endfor %}
        </table>
        <br><a href="/">Back to Home</a>
    </body>
    </html>
    """, applications=applications)


# VIEW RESUME
@app.route("/resume/<filename>")
def view_resume(filename):
    filename = secure_filename(filename)

    if not filename or not os.path.isfile(
        os.path.join(UPLOAD_FOLDER, filename)
    ):
        return "Resume not found.", 404

    return send_from_directory(
        UPLOAD_FOLDER, filename, as_attachment=True
    )


if __name__ == "__main__":
    app.run(debug=True)