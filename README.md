# Timetable Assistant

A simple Flask backend for viewing and managing classroom timetables, with a small rule-based chatbot.

**Features**
- **Timetable APIs**: today, week, next class, upcoming, free periods, search
- **Admin CRUD**: manage timetable entries, faculty, classrooms, departments
- **CSV upload**: bulk import timetable rows
- **Auth**: email/password/role session-based login
- **Chatbot**: rule-based natural language queries over the timetable

**Requirements**
- Python 3.8+
- See `requirements.txt` for exact dependencies

**Quick start**
1. Install dependencies:

```
pip install -r requirements.txt
```

2. Initialize the database (first run only):

```
python database.py
```

3. Run the app:

```
python app.py
```

The backend runs on http://127.0.0.1:5000 and serves a static frontend from the `static` folder.

**API overview**
- POST `/api/login` — body: `{ "email":"...", "password":"...", "role":"admin|faculty|student" }`
- POST `/api/logout`
- GET `/api/me`

- GET `/api/timetable/today` — logged-in users
- GET `/api/timetable/week`
- GET `/api/timetable/next-class`
- GET `/api/timetable/upcoming`
- GET `/api/free-periods?day=Monday&classroom=Lab&faculty=Smith`

- GET `/api/search?type=subject|faculty|classroom&query=...`

Admin endpoints (require `role=admin`):
- POST `/api/admin/timetable` — add entry
- PUT/DELETE `/api/admin/timetable/<id>` — edit/delete entry
- POST `/api/admin/timetable/upload-csv` — multipart file upload; CSV columns expected:
  `day,period_no,start_time,end_time,subject_code,faculty_email,classroom,department,year,section`
- CRUD endpoints for faculty, classroom, department under `/api/admin/`

Chatbot:
- POST `/api/chatbot/ask` — body: `{ "question": "..." }` returns a plain-text answer

**Notes & tips**
- Static frontend: the app serves `static/index.html` at `/`.
- Database helpers and initialization live in `database.py` — run it once to create seeded data.
- Default passwords for seeded faculty/users are set during seeding; check `database.py` for details.

If you want, I can:
- add example `curl` commands for common flows
- create a `requirements.txt` if missing
- commit the README to Git
# Periodly — AI Timetable Assistant

A full-stack college timetable assistant: single-portal login (student / faculty / admin),
daily & weekly timetable views, subject/faculty/classroom search, free-period finder,
admin timetable management (incl. CSV upload), and a rule-based **AI chatbot** that answers
questions like *"what's my next class"* or *"free periods today"* straight from the database.

## Stack
- **Backend:** Python + Flask + SQLite (`app.py`, `database.py`)
- **Frontend:** HTML + CSS + vanilla JavaScript (`static/`)

## Setup
```bash
pip install -r requirements.txt
python database.py     # creates timetable.db and seeds sample data (run once)
python app.py           # starts the server on http://127.0.0.1:5000
```
Open **http://127.0.0.1:5000** in your browser.

## Demo logins
| Role     | Email                        | Password    |
|----------|-------------------------------|-------------|
| Student  | ravi.shankar@college.edu      | student123  |
| Faculty  | anita.rao@college.edu         | faculty123  |
| Admin    | admin@college.edu             | admin123    |

Sample data covers Monday–Friday, so if you test on a weekend the "today" views
will correctly show no classes — try the weekly view or add entries as admin.

## Database schema
- `department(id, name)`
- `faculty(id, name, department, email)`
- `student(id, name, roll_no, year, dept, email)`
- `subjects(id, name, code, department)`
- `classroom(id, name, capacity, department)`
- `classroomtimetable(id, day, period_no, start_time, end_time, subject_id, faculty_id, classroom_id, department, year, section)`
- `users(id, email, password_hash, role, ref_id)` — single login portal; `role` is chosen at
  login and `ref_id` links to `faculty.id` or `student.id` (NULL for admin).

## CSV upload format (admin)
```
day,period_no,start_time,end_time,subject_code,faculty_email,classroom,department,year,section
```
See `sample_timetable.csv` for a working example.

## Notes / next steps
- Passwords are hashed with SHA-256 for this demo; swap in `bcrypt`/`werkzeug.security`
  and add rate limiting before deploying for real use.
- The chatbot is intent/keyword based (no external API key needed). To upgrade it to a
  true LLM, swap `chatbot_answer()` in `app.py` for a call to the Claude/OpenAI API,
  passing it the matched timetable rows as context so it stays grounded in real data.
- Add proper session expiry / CSRF protection for production.
