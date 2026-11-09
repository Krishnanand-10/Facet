import os
import cv2
import sqlite3
import numpy as np
import base64
import io
import csv

from PIL import Image
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, jsonify,
    make_response
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "facet-secret-key-mca-final-year")

# Directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(BASE_DIR, "dataset")
TRAINER = os.path.join(BASE_DIR, "trainer")
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE = os.path.join(DATABASE_DIR, "attendance.db")

for folder in [DATASET, TRAINER, DATABASE_DIR]:
    os.makedirs(folder, exist_ok=True)

MODEL_PATH = os.path.join(TRAINER, "trainer.yml")

# Face detector Haar Cascade
LOCAL_CASCADE = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
if os.path.exists(LOCAL_CASCADE):
    CASCADE_PATH = LOCAL_CASCADE
elif hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades") and os.path.exists(cv2.data.haarcascades + "haarcascade_frontalface_default.xml"):
    CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
else:
    CASCADE_PATH = LOCAL_CASCADE

face_detector = cv2.CascadeClassifier(CASCADE_PATH)
if face_detector.empty():
    print(f"CRITICAL: Failed to load Haar cascade classifier from {CASCADE_PATH}")
else:
    print(f"Haar cascade classifier loaded successfully from {CASCADE_PATH}")

# LBPH face recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()

model_ready = False
CONFIDENCE_LIMIT = float(os.environ.get("CONFIDENCE_LIMIT", 65.0))


# ---------------- DATABASE SETUP ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE COLLATE NOCASE NOT NULL,
            department TEXT,
            semester TEXT,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_students_roll_nocase
        ON students (LOWER(TRIM(roll_number)))
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            UNIQUE(student_id, date),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    """)

    admin = conn.execute(
        "SELECT id FROM admins WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:
        conn.execute(
            "INSERT INTO admins(username, password) VALUES (?, ?)",
            ("admin", generate_password_hash("admin123"))
        )

    conn.commit()
    conn.close()


initialize_database()


# ---------------- AUTHENTICATION ----------------

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if "admin" not in session:
            # If AJAX / API request, return JSON 401 instead of redirecting to HTML login page
            is_api = (
                request.path in ["/register_student", "/capture_face", "/train_model", "/recognize"] or
                request.headers.get("X-Requested-With") == "XMLHttpRequest" or
                request.is_json or
                "application/json" in request.headers.get("Accept", "")
            )
            if is_api:
                return jsonify({
                    "success": False,
                    "session_expired": True,
                    "message": "Session expired or not authenticated. Please log in again."
                }), 401
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


@app.errorhandler(500)
def handle_server_error(e):
    is_api = (
        request.path in ["/register_student", "/capture_face", "/train_model", "/recognize"] or
        request.headers.get("X-Requested-With") == "XMLHttpRequest" or
        request.is_json
    )
    if is_api:
        return jsonify({
            "success": False,
            "message": f"Internal server error: {str(e)}"
        }), 500
    return "Internal Server Error", 500


@app.errorhandler(404)
def handle_not_found(e):
    is_api = (
        request.path in ["/register_student", "/capture_face", "/train_model", "/recognize"] or
        request.headers.get("X-Requested-With") == "XMLHttpRequest" or
        request.is_json
    )
    if is_api:
        return jsonify({
            "success": False,
            "message": "API endpoint not found"
        }), 404
    return "Not Found", 404


@app.route("/", methods=["GET", "POST"])
def login():
    if "admin" in session:
        return redirect(url_for("dashboard"))

    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db()
        admin = conn.execute(
            "SELECT * FROM admins WHERE username = ?",
            (username,)
        ).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin"] = username
            return redirect(url_for("dashboard"))

        error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()

    total_students = conn.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    today = datetime.now().strftime("%Y-%m-%d")

    today_attendance = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE date = ?",
        (today,)
    ).fetchone()[0]

    students_raw = conn.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()

    students = []
    for s in students_raw:
        s_dict = dict(s)
        folder = os.path.join(DATASET, str(s["id"]))
        sample_count = len([f for f in os.listdir(folder) if f.lower().endswith(".jpg")]) if os.path.exists(folder) else 0
        s_dict["sample_count"] = sample_count
        students.append(s_dict)

    records = conn.execute("""
        SELECT students.name, students.roll_number, students.department,
               attendance.date, attendance.time
        FROM attendance
        JOIN students ON students.id = attendance.student_id
        ORDER BY attendance.id DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        total_students=total_students,
        today_attendance=today_attendance,
        students=students,
        records=records,
        today=today,
        model_ready=model_ready
    )


# ---------------- FACE PROCESSING UTILS ----------------

def decode_image(data):
    if not data:
        return None

    try:
        if "," in data:
            data = data.split(",", 1)[1]

        raw = base64.b64decode(data)
        image = Image.open(io.BytesIO(raw)).convert("RGB")

        return cv2.cvtColor(
            np.array(image),
            cv2.COLOR_RGB2BGR
        )
    except Exception:
        return None


def extract_face(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)

    faces = face_detector.detectMultiScale(
        equalized,
        scaleFactor=1.1,
        minNeighbors=4,
        minSize=(50, 50)
    )

    if len(faces) == 0:
        faces = face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=3,
            minSize=(40, 40)
        )

    if len(faces) == 0:
        return None

    # Pick the largest face in frame
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    face = gray[y:y+h, x:x+w]
    face = cv2.resize(face, (200, 200))
    return face


# ---------------- STUDENT REGISTRATION ----------------

@app.route("/register_student", methods=["POST"])
@login_required
def register_student():
    try:
        name = request.form.get("name", "").strip()
        roll = request.form.get("roll_number", "").strip()
        department = request.form.get("department", "").strip()
        semester = request.form.get("semester", "").strip()

        if not name or not roll:
            return jsonify({
                "success": False,
                "message": "Name and roll number are required"
            })

        conn = get_db()

        # Strict uniqueness validation: no two students can share the same roll number (case-insensitive and trimmed)
        existing = conn.execute(
            "SELECT id, name, roll_number FROM students WHERE LOWER(TRIM(roll_number)) = LOWER(?)",
            (roll,)
        ).fetchone()

        if existing:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Roll number '{roll}' already exists (assigned to student '{existing['name']}', ID #{existing['id']}). Duplicate roll numbers are not permitted."
            })

        try:
            cursor = conn.execute("""
                INSERT INTO students
                (name, roll_number, department, semester, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                name,
                roll,
                department,
                semester,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))

            student_id = cursor.lastrowid
            conn.commit()
            conn.close()

            os.makedirs(os.path.join(DATASET, str(student_id)), exist_ok=True)

            return jsonify({
                "success": True,
                "student_id": student_id,
                "name": name,
                "roll_number": roll,
                "message": f"Student '{name}' registered successfully! Assigned Unique ID #{student_id}."
            })

        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Roll number '{roll}' already exists in database records."
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500


def check_biometric_conflict(face, current_student_id):
    """
    Checks whether a candidate face sample already belongs to another enrolled student.
    Returns (conflict_found: bool, conflicting_student_info: dict or None).
    """
    try:
        cur_id = int(current_student_id)
    except (ValueError, TypeError):
        return False, None

    # 1. Check against active trained model if available
    if model_ready:
        try:
            label, distance = recognizer.predict(face)
            if label != cur_id and distance < 55.0:
                conn = get_db()
                other = conn.execute(
                    "SELECT id, name, roll_number FROM students WHERE id = ?",
                    (int(label),)
                ).fetchone()
                conn.close()
                if other:
                    return True, dict(other)
        except Exception:
            pass

    # 2. Check directly against captured sample files in DATASET from other students
    other_faces = []
    other_labels = []
    if os.path.exists(DATASET):
        for s_dir in os.listdir(DATASET):
            if not s_dir.isdigit() or int(s_dir) == cur_id:
                continue
            s_folder = os.path.join(DATASET, s_dir)
            if not os.path.isdir(s_folder):
                continue
            for fname in os.listdir(s_folder):
                if fname.lower().endswith((".jpg", ".png")):
                    fpath = os.path.join(s_folder, fname)
                    img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
                    if img is not None:
                        if img.shape != (200, 200):
                            img = cv2.resize(img, (200, 200))
                        other_faces.append(img)
                        other_labels.append(int(s_dir))

    if other_faces and other_labels:
        try:
            temp_rec = cv2.face.LBPHFaceRecognizer_create()
            temp_rec.train(other_faces, np.array(other_labels, dtype=np.int32))
            pred_id, dist = temp_rec.predict(face)
            if dist < 55.0:
                conn = get_db()
                other = conn.execute(
                    "SELECT id, name, roll_number FROM students WHERE id = ?",
                    (int(pred_id),)
                ).fetchone()
                conn.close()
                if other:
                    return True, dict(other)
        except Exception:
            pass

    return False, None


@app.route("/capture_face", methods=["POST"])
@login_required
def capture_face():
    try:
        student_id = request.form.get("student_id", "").strip()
        image_data = request.form.get("image", "").strip()

        if not student_id.isdigit():
            return jsonify({
                "success": False,
                "message": "Invalid student ID"
            })

        conn = get_db()
        student = conn.execute(
            "SELECT id, name, roll_number FROM students WHERE id = ?",
            (int(student_id),)
        ).fetchone()
        conn.close()

        if not student:
            return jsonify({
                "success": False,
                "message": "Student not found in database"
            })

        image = decode_image(image_data)
        if image is None:
            return jsonify({
                "success": False,
                "message": "Invalid image payload"
            })

        face = extract_face(image)
        if face is None:
            return jsonify({
                "success": False,
                "message": "No face detected. Please ensure your face is clearly visible."
            })

        # Biometric uniqueness check: prevent enrolling the same face for two different students
        has_conflict, other_student = check_biometric_conflict(face, student_id)
        if has_conflict and other_student:
            return jsonify({
                "success": False,
                "message": f"Biometric Conflict: This face already belongs to enrolled student '{other_student['name']}' (Roll No: {other_student['roll_number']}). Each student must have a distinct biometric identity."
            })

        folder = os.path.join(DATASET, str(student_id))
        os.makedirs(folder, exist_ok=True)

        existing = len([f for f in os.listdir(folder) if f.lower().endswith(".jpg")])

        if existing >= 15:
            return jsonify({
                "success": False,
                "count": existing,
                "message": "Maximum samples already collected for this student"
            })

        filename = os.path.join(folder, f"face_{existing + 1}.jpg")
        cv2.imwrite(filename, face)

        count = existing + 1
        if count >= 5:
            msg = f"Sample {count}/5 saved for {student['name']} (5/5 Target Reached! Ready to train)"
        else:
            msg = f"Sample {count}/5 saved for {student['name']}"

        return jsonify({
            "success": True,
            "count": count,
            "message": msg
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Server error during capture: {str(e)}"
        }), 500


# ---------------- TRAIN MODEL ----------------

@app.route("/train_model", methods=["POST"])
@login_required
def train_model():
    try:
        global model_ready

        faces = []
        labels = []

        conn = get_db()
        students = conn.execute("SELECT id FROM students").fetchall()
        conn.close()

        for student in students:
            student_id = student["id"]
            folder = os.path.join(DATASET, str(student_id))

            if not os.path.isdir(folder):
                continue

            for filename in os.listdir(folder):
                if not filename.lower().endswith(".jpg"):
                    continue

                path = os.path.join(folder, filename)
                face = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

                if face is not None:
                    face = cv2.resize(face, (200, 200))
                    faces.append(face)
                    labels.append(student_id)

        if not faces:
            return jsonify({
                "success": False,
                "message": "No face samples available to train. Please capture student faces first."
            })

        # Cross-validation: detect if multiple students have identical/conflicting facial samples
        unique_student_ids = list(set(labels))
        if len(unique_student_ids) > 1:
            samples_by_student = {}
            for f, l in zip(faces, labels):
                samples_by_student.setdefault(l, []).append(f)

            conflict_pair = None
            for i in range(len(unique_student_ids)):
                for j in range(i + 1, len(unique_student_ids)):
                    s1 = unique_student_ids[i]
                    s2 = unique_student_ids[j]

                    chk_rec = cv2.face.LBPHFaceRecognizer_create()
                    chk_rec.train(samples_by_student[s1], np.array([s1] * len(samples_by_student[s1]), dtype=np.int32))
                    for sample in samples_by_student[s2]:
                        _, d = chk_rec.predict(sample)
                        if d < 48.0:
                            conflict_pair = (s1, s2)
                            break
                    if conflict_pair:
                        break
                if conflict_pair:
                    break

            if conflict_pair:
                conn = get_db()
                st1 = conn.execute("SELECT name, roll_number FROM students WHERE id = ?", (conflict_pair[0],)).fetchone()
                st2 = conn.execute("SELECT name, roll_number FROM students WHERE id = ?", (conflict_pair[1],)).fetchone()
                conn.close()
                desc1 = f"'{st1['name']}' (Roll: {st1['roll_number']})" if st1 else f"Student #{conflict_pair[0]}"
                desc2 = f"'{st2['name']}' (Roll: {st2['roll_number']})" if st2 else f"Student #{conflict_pair[1]}"
                return jsonify({
                    "success": False,
                    "message": f"Biometric Conflict: Conflicting facial samples detected between {desc1} and {desc2}. Two students cannot share identical facial biometrics. Please delete the duplicate profile or recapture distinct samples."
                })

        recognizer.train(faces, np.array(labels, dtype=np.int32))
        recognizer.save(MODEL_PATH)
        model_ready = True

        unique_students = len(set(labels))
        return jsonify({
            "success": True,
            "message": f"Model trained successfully with {len(faces)} face samples across {unique_students} student(s)!"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Server error during training: {str(e)}"
        }), 500


def load_model():
    global model_ready

    if os.path.exists(MODEL_PATH):
        try:
            recognizer.read(MODEL_PATH)
            model_ready = True
        except Exception:
            model_ready = False


load_model()


# ---------------- MARK ATTENDANCE ----------------

@app.route("/recognize", methods=["POST"])
@login_required
def recognize():
    try:
        if not model_ready:
            return jsonify({
                "success": False,
                "message": "Face recognition model is not trained yet. Please train it first."
            })

        image_data = request.form.get("image", "").strip()
        image = decode_image(image_data)

        if image is None:
            return jsonify({
                "success": False,
                "message": "Invalid image received"
            })

        face = extract_face(image)
        if face is None:
            return jsonify({
                "success": False,
                "message": "No face detected in camera frame"
            })

        try:
            label, confidence = recognizer.predict(face)
        except Exception:
            return jsonify({
                "success": False,
                "message": "Recognition processing error"
            })

        # LBPH: confidence represents Euclidean distance. Smaller distance = better match.
        if confidence > CONFIDENCE_LIMIT:
            return jsonify({
                "success": False,
                "confidence": round(float(confidence), 2),
                "message": f"Face not recognized (Distance: {round(float(confidence), 1)} > {CONFIDENCE_LIMIT})"
            })

        conn = get_db()
        student = conn.execute(
            "SELECT * FROM students WHERE id = ?",
            (int(label),)
        ).fetchone()

        if student is None:
            conn.close()
            return jsonify({
                "success": False,
                "message": "Student record not found in system"
            })

        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        is_new_mark = False
        try:
            conn.execute("""
                INSERT INTO attendance(student_id, date, time)
                VALUES (?, ?, ?)
            """, (int(label), date, time))
            conn.commit()
            message = "Attendance marked successfully"
            is_new_mark = True
        except sqlite3.IntegrityError:
            message = "Attendance already marked today"
            is_new_mark = False

        conn.close()

        return jsonify({
            "success": True,
            "student_id": student["id"],
            "name": student["name"],
            "roll_number": student["roll_number"],
            "department": student["department"] or "General",
            "date": date,
            "time": time,
            "confidence": round(float(confidence), 2),
            "is_new_mark": is_new_mark,
            "message": message
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Server error during recognition: {str(e)}"
        }), 500


# ---------------- ATTENDANCE REPORT & EXPORT ----------------

@app.route("/attendance")
@login_required
def attendance():
    selected_date = request.args.get(
        "date",
        datetime.now().strftime("%Y-%m-%d")
    )

    conn = get_db()

    total_students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    students = conn.execute("SELECT * FROM students ORDER BY id DESC").fetchall()

    records = conn.execute("""
        SELECT students.name,
               students.roll_number,
               students.department,
               attendance.date,
               attendance.time
        FROM attendance
        JOIN students ON students.id = attendance.student_id
        WHERE attendance.date = ?
        ORDER BY attendance.time DESC
    """, (selected_date,)).fetchall()

    conn.close()

    return render_template(
        "index.html",
        total_students=total_students,
        today_attendance=len(records),
        students=students,
        records=records,
        today=selected_date,
        model_ready=model_ready
    )


@app.route("/export")
@login_required
def export():
    conn = get_db()
    records = conn.execute("""
        SELECT students.name,
               students.roll_number,
               students.department,
               attendance.date,
               attendance.time
        FROM attendance
        JOIN students ON students.id = attendance.student_id
        ORDER BY attendance.date DESC, attendance.time DESC
    """).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Roll Number", "Department", "Date", "Time"])

    for row in records:
        writer.writerow(list(row))

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=attendance_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


# ---------------- STUDENT DELETION ----------------

@app.route("/delete_student/<int:student_id>", methods=["POST"])
@login_required
def delete_student(student_id):
    conn = get_db()
    conn.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

    folder = os.path.join(DATASET, str(student_id))
    if os.path.exists(folder):
        import shutil
        shutil.rmtree(folder)

    return redirect(url_for("dashboard"))


# ---------------- MAIN RUNNER ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="127.0.0.1",
        port=port,
        debug=False
    )
