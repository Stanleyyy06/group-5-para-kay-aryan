from flask import Flask, render_template, redirect, url_for, session
from pathlib import Path
import sqlite3
import os

from auth import auth_bp

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "replace_this_with_a_secret_key"
)

# Register auth blueprint
app.register_blueprint(auth_bp)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# Initialize database
init_db()


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
    return render_template(
        "camera.html",
        username=session.get("username")
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
