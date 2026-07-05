"""
Timetable Assistant - Flask Backend
------------------------------------
Full backend with:
 - User registration & login (session based, hashed passwords)
 - SQLite database via SQLAlchemy
 - Timetable + Exam models
 - REST-ish API endpoints used by the frontend (dashboard + chat-style Q&A)

Run with:  python app.py
"""

from datetime import datetime, date, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///timetable.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(80), default="")
    semester = db.Column(db.String(20), default="")
    section = db.Column(db.String(20), default="")
    role = db.Column(db.String(20), default="student")  # student / teacher

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


class ClassSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(80), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    faculty = db.Column(db.String(120), nullable=False)
    room = db.Column(db.String(20), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday..Sunday
    start_time = db.Column(db.String(10), nullable=False)   # "09:00"
    end_time = db.Column(db.String(10), nullable=False)     # "10:00"
    status = db.Column(db.String(20), default="Scheduled")  # Scheduled/Cancelled/Extra


class ExamEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(80), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    section = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.String(20), nullable=False)  # "2026-07-10"
    details = db.Column(db.String(300), default="")


# --------------------------------------------------------------------------
# Auth helpers
# --------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


# --------------------------------------------------------------------------
# Auth routes
# --------------------------------------------------------------------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        department = request.form.get("department", "").strip()
        semester = request.form.get("semester", "").strip()
        section = request.form.get("section", "").strip()
        role = request.form.get("role", "student")

        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
            return redirect(url_for("register"))

        user = User(
            name=name, email=email, department=department,
            semester=semester, section=section, role=role
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user_name"] = user.name
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# --------------------------------------------------------------------------
# Dashboard (frontend page)
# --------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user())


# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------
def user_scope_filter(query, user):
    return query.filter_by(
        department=user.department, semester=user.semester, section=user.section
    )


def serialize_class(c):
    return {
        "id": c.id,
        "subject": c.subject,
        "faculty": c.faculty,
        "room": c.room,
        "day": c.day_of_week,
        "start_time": c.start_time,
        "end_time": c.end_time,
        "status": c.status,
    }


# --------------------------------------------------------------------------
# API routes
# --------------------------------------------------------------------------
@app.route("/api/timetable/today")
@login_required
def api_today():
    user = current_user()
    today_name = DAYS[date.today().weekday()]
    classes = user_scope_filter(ClassSession.query, user).filter_by(day_of_week=today_name).all()
    classes.sort(key=lambda c: c.start_time)
    return jsonify({
        "date": date.today().strftime("%A, %d %B %Y"),
        "day": today_name,
        "classes": [serialize_class(c) for c in classes],
    })


@app.route("/api/timetable/day/<day_name>")
@login_required
def api_day(day_name):
    user = current_user()
    day_name = day_name.capitalize()
    if day_name not in DAYS:
        return jsonify({"error": "Invalid day name"}), 400
    classes = user_scope_filter(ClassSession.query, user).filter_by(day_of_week=day_name).all()
    classes.sort(key=lambda c: c.start_time)
    return jsonify({"day": day_name, "classes": [serialize_class(c) for c in classes]})


@app.route("/api/timetable/week")
@login_required
def api_week():
    user = current_user()
    result = {}
    for day in DAYS:
        classes = user_scope_filter(ClassSession.query, user).filter_by(day_of_week=day).all()
        classes.sort(key=lambda c: c.start_time)
        result[day] = [serialize_class(c) for c in classes]
    return jsonify(result)


@app.route("/api/timetable/next-class")
@login_required
def api_next_class():
    user = current_user()
    now = datetime.now()
    today_name = DAYS[now.weekday()]
    current_time = now.strftime("%H:%M")

    todays = user_scope_filter(ClassSession.query, user).filter_by(day_of_week=today_name).all()
    todays = [c for c in todays if c.status != "Cancelled" and c.start_time >= current_time]
    todays.sort(key=lambda c: c.start_time)
    if todays:
        return jsonify({"found": True, "class": serialize_class(todays[0]), "when": "today"})

    # look ahead through the week
    for i in range(1, 8):
        d = DAYS[(now.weekday() + i) % 7]
        classes = user_scope_filter(ClassSession.query, user).filter_by(day_of_week=d).all()
        classes = [c for c in classes if c.status != "Cancelled"]
        classes.sort(key=lambda c: c.start_time)
        if classes:
            return jsonify({"found": True, "class": serialize_class(classes[0]), "when": d})

    return jsonify({"found": False})


@app.route("/api/timetable/free-periods/<day_name>")
@login_required
def api_free_periods(day_name):
    """Very simple free-period calculator between a fixed 09:00-17:00 day window."""
    user = current_user()
    day_name = day_name.capitalize()
    if day_name not in DAYS:
        return jsonify({"error": "Invalid day name"}), 400

    classes = user_scope_filter(ClassSession.query, user).filter_by(day_of_week=day_name).all()
    classes = [c for c in classes if c.status != "Cancelled"]
    classes.sort(key=lambda c: c.start_time)

    day_start, day_end = "09:00", "17:00"
    free_slots = []
    cursor = day_start
    for c in classes:
        if c.start_time > cursor:
            free_slots.append({"start": cursor, "end": c.start_time})
        cursor = max(cursor, c.end_time)
    if cursor < day_end:
        free_slots.append({"start": cursor, "end": day_end})

    return jsonify({"day": day_name, "free_periods": free_slots})


@app.route("/api/exams")
@login_required
def api_exams():
    user = current_user()
    exams = ExamEvent.query.filter_by(
        department=user.department, semester=user.semester, section=user.section
    ).all()
    exams.sort(key=lambda e: e.event_date)
    return jsonify([
        {"title": e.title, "date": e.event_date, "details": e.details} for e in exams
    ])


@app.route("/api/cancelled-this-week")
@login_required
def api_cancelled_week():
    user = current_user()
    classes = user_scope_filter(ClassSession.query, user).filter_by(status="Cancelled").all()
    return jsonify([serialize_class(c) for c in classes])


@app.route("/api/ask", methods=["POST"])
@login_required
def api_ask():
    """A lightweight natural-language query handler for common timetable questions."""
    user = current_user()
    query = (request.json or {}).get("query", "").lower().strip()
    now = datetime.now()
    today_name = DAYS[now.weekday()]

    def classes_for(day):
        c = user_scope_filter(ClassSession.query, user).filter_by(day_of_week=day).all()
        c.sort(key=lambda x: x.start_time)
        return c

    if "cancel" in query:
        cancelled = user_scope_filter(ClassSession.query, user).filter_by(status="Cancelled").all()
        if not cancelled:
            return jsonify({"answer": "No classes have been cancelled this week. 🎉"})
        lines = [f"{c.subject} on {c.day_of_week} ({c.start_time}-{c.end_time})" for c in cancelled]
        return jsonify({"answer": "Cancelled classes: " + "; ".join(lines)})

    if "exam" in query:
        exams = ExamEvent.query.filter_by(
            department=user.department, semester=user.semester, section=user.section
        ).all()
        if not exams:
            return jsonify({"answer": "No exam schedule is available yet."})
        lines = [f"{e.title} on {e.date if hasattr(e,'date') else e.event_date}" for e in exams]
        return jsonify({"answer": "Upcoming exams: " + "; ".join(
            f"{e.title} on {e.event_date}" for e in exams
        )})

    if "free" in query:
        day = "tomorrow" if "tomorrow" in query else "today"
        target_day = DAYS[(now.weekday() + (1 if day == "tomorrow" else 0)) % 7]
        c = classes_for(target_day)
        c = [x for x in c if x.status != "Cancelled"]
        if not c:
            return jsonify({"answer": f"You have no classes on {target_day}, so the whole day is free!"})
        cursor, free = "09:00", []
        for cls in c:
            if cls.start_time > cursor:
                free.append(f"{cursor}-{cls.start_time}")
            cursor = max(cursor, cls.end_time)
        if cursor < "17:00":
            free.append(f"{cursor}-17:00")
        if not free:
            return jsonify({"answer": f"No free periods on {target_day}, it's fully booked."})
        return jsonify({"answer": f"Free periods on {target_day}: " + ", ".join(free)})

    if "next class" in query or "next period" in query:
        todays = classes_for(today_name)
        todays = [c for c in todays if c.status != "Cancelled" and c.start_time >= now.strftime("%H:%M")]
        if todays:
            c = todays[0]
            return jsonify({"answer": f"Your next class is {c.subject} at {c.start_time} in Room {c.room} with {c.faculty}."})
        return jsonify({"answer": "You have no more classes today."})

    if "today" in query:
        c = classes_for(today_name)
        if not c:
            return jsonify({"answer": "You have no classes scheduled today."})
        lines = [f"{x.subject} ({x.start_time}-{x.end_time}, Room {x.room}, {x.faculty})" for x in c]
        return jsonify({"answer": "Today's classes: " + "; ".join(lines)})

    for day in DAYS:
        if day.lower() in query:
            c = classes_for(day)
            if not c:
                return jsonify({"answer": f"You have no classes on {day}."})
            lines = [f"{x.subject} ({x.start_time}-{x.end_time}, Room {x.room}, {x.faculty})" for x in c]
            return jsonify({"answer": f"{day}'s classes: " + "; ".join(lines)})

    if "who is taking" in query or "faculty" in query or "teacher" in query:
        for c in user_scope_filter(ClassSession.query, user).all():
            if c.subject.lower() in query:
                return jsonify({"answer": f"{c.subject} is taken by {c.faculty} in Room {c.room}."})
        return jsonify({"answer": "I couldn't find that subject in your timetable."})

    return jsonify({"answer": "I can help with today's classes, weekly timetable, next class, free periods, cancelled classes, or exam schedules. Try asking one of those!"})


# --------------------------------------------------------------------------
# Database bootstrap + demo seed data
# --------------------------------------------------------------------------
def seed_demo_data():
    """Adds a demo student + sample timetable/exam data the first time the app runs."""
    if User.query.first():
        return  # already seeded

    demo = User(
        name="Demo Student",
        email="demo@student.com",
        department="CSE",
        semester="5",
        section="A",
        role="student",
    )
    demo.set_password("demo1234")
    db.session.add(demo)
    db.session.commit()

    sample_classes = [
        ("Database Management Systems", "Dr. A. Sharma", "301", "Monday", "09:00", "10:00"),
        ("Operating Systems", "Prof. R. Iyer", "302", "Monday", "10:00", "11:00"),
        ("Computer Networks", "Dr. M. Verma", "303", "Monday", "11:15", "12:15"),
        ("Database Management Systems", "Dr. A. Sharma", "301", "Wednesday", "09:00", "10:00"),
        ("Software Engineering", "Prof. K. Rao", "304", "Wednesday", "10:00", "11:00"),
        ("Operating Systems Lab", "Prof. R. Iyer", "Lab-2", "Friday", "13:00", "15:00"),
    ]
    for subject, faculty, room, day, start, end in sample_classes:
        db.session.add(ClassSession(
            department="CSE", semester="5", section="A",
            subject=subject, faculty=faculty, room=room,
            day_of_week=day, start_time=start, end_time=end, status="Scheduled"
        ))

    upcoming = (date.today() + timedelta(days=10)).isoformat()
    db.session.add(ExamEvent(
        department="CSE", semester="5", section="A",
        title="Database Management Systems - Mid Sem",
        event_date=upcoming, details="Room 301, 10:00 AM"
    ))

    db.session.commit()


with app.app_context():
    db.create_all()
    seed_demo_data()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
