# Facet: Face Recognition-Based Smart Attendance Management System

Facet is an automated, web-based Face Recognition Attendance Management System designed as an MCA Final-Year Project. It leverages **Python**, **Flask**, **OpenCV** (Haar Cascade detection and LBPH face recognition), and **SQLite** to register students, capture biometric face samples, recognize students via real-time webcam video feed, and maintain daily attendance logs without proxy marking.

Developed following **OpenSpec** (Spec-Driven Development).

---

## 🚀 Features

- **Admin Authentication**: Secure session-based login with Werkzeug password hashing.
- **Student Profile Management**: Register student records (name, roll number, department, semester) with unique constraints.
- **Biometric Face Capture**: Capture 10–30 grayscale facial samples directly from browser webcam stream.
- **LBPH Model Training**: Trains OpenCV's Local Binary Patterns Histograms (LBPH) face recognizer (`trainer.yml`) with one click.
- **Automated Attendance Marking**: Detects and recognizes registered student faces and logs attendance with date and time.
- **Strict Duplicate Prevention**: Enforces a single attendance record per student per calendar date (`UNIQUE(student_id, date)`).
- **Date-Filtered Reports**: Query attendance logs by specific date from the dashboard.
- **CSV Data Export**: Export full attendance records into standard CSV format for academic records.
- **OpenSpec Architecture**: Fully specified capabilities and delta specs inside `openspec/`.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|------------|---------|
| **Python 3** | Backend programming language |
| **Flask** | Web framework and REST routing |
| **OpenCV (`opencv-contrib-python`)** | Haar Cascade face detection & LBPH face recognition |
| **SQLite** | Embedded relational database |
| **NumPy & Pillow** | Array manipulations and image decoding |
| **HTML5 / CSS3 / JavaScript** | Responsive user interface & WebRTC camera streaming |
| **Pytest** | Automated test suite |

---

## 📁 Project Directory Structure

```text
Facet/
├── app.py                     # Main Flask web application
├── requirements.txt           # Project dependencies
├── README.md                  # Project documentation
├── .gitignore                 # Git ignore rules
│
├── database/
│   └── attendance.db          # SQLite database (auto-created on startup)
│
├── dataset/                   # Categorized student face image directories
│   └── <student_id>/
│       └── face_1.jpg ...
│
├── trainer/
│   └── trainer.yml            # Trained LBPH model weights
│
├── templates/
│   ├── login.html             # Administrator login view
│   └── index.html             # Main dashboard, camera & attendance interface
│
├── tests/
│   └── test_facet.py          # Pytest integration test suite
│
└── openspec/                  # Spec-Driven Development artifacts
    ├── changes/
    │   └── face-recognition-attendance/
    │       ├── proposal.md
    │       ├── design.md
    │       ├── tasks.md
    │       └── specs/
    └── config.yaml
```

---

## ⚡ Quick Start

### 1. Clone & Navigate to Repository
```bash
git clone https://github.com/Krishnanand-10/Facet.git
cd Facet
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

### 🔑 Default Credentials
- **Username**: `admin`
- **Password**: `admin123`

---

## 📖 Operational Workflow

1. **Admin Login**: Log in with the default admin credentials.
2. **Register Student**: In Section 1, input student details (Name, Roll Number, Department, Semester).
3. **Start Camera**: In Section 3, click **Start Camera** and grant browser webcam permissions.
4. **Capture Face Samples**: In Section 2, click **Capture Face Sample** 10–20 times while looking at the camera from slight angles.
5. **Train Model**: Click **Train Recognition Model**. The system fits the LBPH recognizer and creates `trainer/trainer.yml`.
6. **Mark Attendance**: Click **Start Attendance Marking**. The system identifies matching faces in real time and marks attendance.
7. **View & Export**: Search attendance logs by date or click **Export CSV Report** to download the record sheet.

---

## 🧪 Running Automated Tests

Run the test suite with pytest:
```bash
./venv/bin/pytest -v
```

---

## 📜 OpenSpec Workflow

Check OpenSpec status at any time:
```bash
openspec status --change face-recognition-attendance
openspec validate face-recognition-attendance
```
