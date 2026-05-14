from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import sqlite3
from pathlib import Path
import threading
import time
import os
from auth import auth_bp

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.secret_key = os.environ.get("SECRET_KEY", "replace_this_with_a_secret_key")

# Register blueprints
app.register_blueprint(auth_bp)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = get_db_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def parse_camera_url(value):
    if value is None or value == "":
        return 0
    try:
        return int(value)
    except ValueError:
        return value

CAMERA_URL = parse_camera_url(os.environ.get("CAMERA_URL", "0"))


# Initialize the database immediately when the app is imported
init_db()


class CameraStream:
    def __init__(self, camera_url=0):
        self.camera_url = camera_url
        self.cap = None
        self.lock = threading.Lock()
        self.frame = None
        self.running = False

    def start(self):
        if not CV2_AVAILABLE:
            return False
        if not self.running:
            self.cap = cv2.VideoCapture(self.camera_url)
            if not self.cap.isOpened():
                self.cap = None
                return False
            self.running = True
            threading.Thread(target=self._read_frames, daemon=True).start()
        return True

    def _read_frames(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break
            with self.lock:
                self.frame = frame

    def get_frame(self):
        with self.lock:
            if self.frame is None or self.cap is None:
                return None
            ret, buffer = cv2.imencode(".jpg", self.frame)
            return buffer.tobytes() if ret else None

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()


camera_stream = CameraStream(CAMERA_URL)


def generate_frames():
    while True:
        frame_bytes = camera_stream.get_frame()
        if frame_bytes:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
        else:
            time.sleep(0.05)


def login_required(view_func):
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    wrapped_view.__name__ = view_func.__name__
    return wrapped_view


@app.route("/")
@login_required
def home():
    return redirect(url_for("camera"))



@app.route("/camera")
@login_required
def camera():
    camera_available = camera_stream.start()
    if not camera_available:
        flash("Camera is unavailable in this environment.", "warning")
    return render_template(
        "camera.html",
        username=session.get("username"),
        camera_available=camera_available,
        camera_url=camera_stream.camera_url,
        camera_env=os.environ.get("CAMERA_URL", "0"),
    )


@app.route("/video_feed")
@login_required
def video_feed():
    if not camera_stream.running:
        return redirect(url_for("camera"))
    return Response(
        generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
