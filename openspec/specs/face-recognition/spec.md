# face-recognition Specification

## Purpose
Detects student faces from camera frames, captures training samples, trains LBPH models, and performs real-time face matching.

## Requirements

### Requirement: Face Sample Capture
The system SHALL detect human faces from submitted webcam frames, extract face regions, and save up to 30 grayscale samples per student.

#### Scenario: Face detected in frame
- **WHEN** a valid image frame containing a detectable human face is posted for a registered student
- **THEN** the system crops and resizes the primary face region and writes it to the student dataset directory

#### Scenario: No face detected in frame
- **WHEN** an image frame without a clear face is submitted
- **THEN** the system rejects the sample and prompts the user to face the camera

### Requirement: LBPH Model Training
The system SHALL train an LBPH face recognition model on all gathered student face samples and persist the model to disk.

#### Scenario: Training with available face samples
- **WHEN** the administrator initiates model training and student face samples exist in the dataset
- **THEN** the system fits the LBPH model, writes `trainer.yml`, and marks the recognizer ready

#### Scenario: Training with empty dataset
- **WHEN** model training is initiated with no face samples available
- **THEN** the system returns an error message indicating no samples are available

### Requirement: Real-Time Face Recognition
The system SHALL match incoming face frames against the trained model within the established confidence threshold.

#### Scenario: Known face recognized
- **WHEN** a face frame matching a registered student is submitted with confidence below the threshold
- **THEN** the system identifies the student name, roll number, and confidence score
