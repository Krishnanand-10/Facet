# Proposal

## Why

Traditional manual attendance processes in academic environments are prone to proxy attendance, time consumption, and human error. This project delivers a web-based Face Recognition-Based Attendance Management System (Facet) built with Flask, OpenCV (Haar Cascade & LBPH), and SQLite to automate student identification and attendance logging seamlessly through webcam capture.

## What Changes

- Administrator authentication system with secure password hashing.
- Student record registration and management (adding, listing, deleting student records).
- Biometric facial image capture (10-30 samples per student) stored in categorized dataset directories.
- LBPH face recognizer training module (`trainer.yml`) with real-time recognition endpoint.
- Automated daily attendance logging with date/time stamps and strict single-entry-per-day enforcement.
- Interactive web interface with live webcam feed, stats dashboard, and date-filtered attendance lookup.
- CSV attendance report generation and download.

## Capabilities

### New Capabilities
- `admin-auth`: Administrative authentication, session control, and access protection for administrative endpoints.
- `student-registration`: Registration, deletion, and local dataset directory management for student profiles.
- `face-recognition`: Haar Cascade face detection, face sample image extraction, LBPH model training, and image prediction.
- `attendance-tracking`: Attendance marking, duplicate prevention per day, date-based querying, and CSV report export.

### Modified Capabilities
None (initial greenfield implementation).

## Impact

- Introduces web application backend in `app.py` utilizing Flask, OpenCV (`opencv-contrib-python`), SQLite, NumPy, and Pillow.
- Adds frontend user interface templates in `templates/login.html` and `templates/index.html`.
- Introduces persistent storage for SQLite database (`database/attendance.db`), image dataset (`dataset/`), and trained model (`trainer/trainer.yml`).
