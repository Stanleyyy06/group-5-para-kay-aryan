#!/usr/bin/env bash
set -e

APP_DIR="/app"

if [ ! -f "$APP_DIR/app.py" ]; then
  FOUND=$(find "$APP_DIR" -maxdepth 3 -type f -name app.py | head -n 1)
  if [ -n "$FOUND" ]; then
    APP_DIR=$(dirname "$FOUND")
  fi
fi

cd "$APP_DIR"
exec gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1
