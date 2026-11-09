#!/usr/bin/env python3
"""
Facet Database Viewer
Utility script to quickly inspect tables and records in database/attendance.db
"""

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "attendance.db")

def print_table(title, headers, rows):
    print(f"\n{'='*20} {title} {'='*20}")
    if not rows:
        print("(No records found)")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(separator)

    for row in rows:
        print(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))
    print(f"Total: {len(rows)} record(s)")

def view_db():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        sys.exit(1)

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Students Table
    cursor.execute("SELECT id, name, roll_number, department, semester, created_at FROM students ORDER BY id ASC")
    student_rows = cursor.fetchall()
    print_table("STUDENTS TABLE", ["ID", "Name", "Roll Number", "Department", "Semester", "Created At"], student_rows)

    # 2. Attendance Table
    cursor.execute("""
        SELECT a.id, s.name, s.roll_number, a.date, a.time 
        FROM attendance a 
        LEFT JOIN students s ON a.student_id = s.id 
        ORDER BY a.id DESC
    """)
    attendance_rows = cursor.fetchall()
    print_table("ATTENDANCE LOGS", ["ID", "Student Name", "Roll Number", "Date", "Time"], attendance_rows)

    # 3. Admins Table
    cursor.execute("SELECT id, username FROM admins")
    admin_rows = cursor.fetchall()
    print_table("ADMIN ACCOUNTS", ["ID", "Username"], admin_rows)

    conn.close()

if __name__ == "__main__":
    view_db()
