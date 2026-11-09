# student-registration Specification

## Purpose
Enables creation, maintenance, and deletion of student profiles along with their associated dataset images.

## Requirements

### Requirement: Student Registration
The system SHALL register new student profiles with unique roll numbers and demographic metadata.

#### Scenario: Successful student registration
- **WHEN** an administrator submits a valid student name and unused roll number
- **THEN** the system stores the student record in SQLite, creates a dataset folder, and returns the assigned student ID

#### Scenario: Duplicate roll number registration
- **WHEN** an administrator attempts to register a student with an already existing roll number
- **THEN** the system rejects registration with an error indicating duplicate roll number

### Requirement: Student Deletion
The system SHALL support removing a student along with their attendance logs and face sample files.

#### Scenario: Deleting existing student
- **WHEN** an administrator requests deletion of a student by ID
- **THEN** the system deletes student records, related attendance logs, and removes the student's face dataset directory
