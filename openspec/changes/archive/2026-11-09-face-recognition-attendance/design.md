# Design

## Context

See proposal.md - Why.
The system is built as a lightweight, standalone Python web application deployable on local workstations for college / MCA attendance tracking, using OpenCV for computer vision, SQLite for persistence, and browser WebRTC (`navigator.mediaDevices.getUserMedia`) for video streaming.

## Goals / Non-Goals

**Goals:**
- Provide a responsive Flask web application running on `127.0.0.1:5000`.
- Utilize standard Haar Cascade (`haarcascade_frontalface_default.xml`) for reliable face bounding box detection.
- Utilize OpenCV LBPH (`cv2.face.LBPHFaceRecognizer`) for face recognition without heavy external deep learning models.
- Implement responsive browser-based camera capture using HTML5 `<video>` and `<canvas>` without requiring client-side native plugins.
- Maintain SQLite database integrity with unique constraints (`UNIQUE(student_id, date)` and `UNIQUE(roll_number)`).

**Non-Goals:**
- Cloud-scale distributed facial databases or multi-camera RTSP surveillance streams.
- Heavy deep learning frameworks (PyTorch, TensorFlow) to keep hardware footprint minimal.

## Decisions

- **SQLite over MySQL**: SQLite provides zero-configuration local persistence, perfectly matching project demonstration and standalone deployment requirements.
- **Client-Side Camera Capture with HTTP POST**: The browser captures frames on canvas and sends base64 image data to the backend via REST endpoints (`/capture_face`, `/recognize`). This avoids continuous MJPEG video server streaming and reduces server CPU overhead.
- **LBPH (Local Binary Pattern Histograms)**: Robust against illumination variations, executes fast on CPUs, and creates compact model files (`trainer.yml`).
- **Confidence Threshold**: Configured to `65.0` distance cutoff. In LBPH, 0 indicates a perfect match; higher distances indicate divergence.

## Risks / Trade-offs

- [Lighting and Angle Variations] → Encourage users to capture 10–20 varied angle samples during registration.
- [Presentation Attacks (Photo spoofing)] → Acknowledged as a starter system limitation; production enhancements can add blink/motion liveness detection.
- [Camera Access Permissions] → Browser requires HTTPS or `localhost` / `127.0.0.1` for `getUserMedia` permissions.
