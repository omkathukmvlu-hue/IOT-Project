from flask import Flask, render_template, Response, jsonify, request, send_from_directory
from camera import VideoCamera
from hardware import set_alarm_outputs, cleanup
from database import init_db, add_event, get_events, get_stats
import os
import threading
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURES_DIR = os.path.join(BASE_DIR, "captures")
os.makedirs(CAPTURES_DIR, exist_ok=True)

app = Flask(__name__)
init_db()

state_lock = threading.Lock()
system_state = {
    "system": "ONLINE",
    "motion": False,
    "alarm": False,
    "armed": True,
    "total_events": 0,
    "today_events": 0,
    "last_event_time": "--:--:--",
    "camera": "STARTING"
}
last_saved_event = 0.0
EVENT_COOLDOWN_SECONDS = 5

def handle_motion(frame_bytes):
    """Called by camera when motion is detected; logs a snapshot and activates LED."""
    global last_saved_event
    now = time.time()
    with state_lock:
        armed = system_state["armed"]
        system_state["motion"] = True
        system_state["alarm"] = bool(armed)
    set_alarm_outputs(bool(armed))
    if not armed or now - last_saved_event < EVENT_COOLDOWN_SECONDS:
        return
    last_saved_event = now
    stamp = datetime.now()
    filename = "motion_" + stamp.strftime("%Y%m%d_%H%M%S") + ".jpg"
    path = os.path.join(CAPTURES_DIR, filename)
    try:
        with open(path, "wb") as f:
            f.write(frame_bytes)
        add_event(stamp.isoformat(timespec="seconds"), "MOTION", filename)
    except OSError as exc:
        app.logger.exception("Could not save motion snapshot: %s", exc)
    refresh_stats()


def refresh_stats():
    stats = get_stats()
    with state_lock:
        system_state.update(stats)


# Camera opens lazily so the dashboard can show an error rather than crash on import.
cam = VideoCamera(on_motion=handle_motion)


def frame_generator():
    while True:
        try:
            frame, motion, camera_ok = cam.get_frame()
            with state_lock:
                system_state["camera"] = "ONLINE" if camera_ok else "ERROR"
                system_state["system"] = "ONLINE" if camera_ok else "CAMERA ERROR"
                # Motion state is updated each frame. Alarm remains on only while armed motion is active.
                system_state["motion"] = bool(motion)
                armed_now = bool(system_state["armed"])
                system_state["alarm"] = bool(motion and armed_now)
            set_alarm_outputs(bool(motion and armed_now))
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n"
                       b"Cache-Control: no-cache\r\n\r\n" + frame + b"\r\n")
            else:
                time.sleep(0.2)
        except GeneratorExit:
            break
        except Exception:
            app.logger.exception("Camera stream error")
            time.sleep(1)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video")
def video():
    return Response(frame_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame",
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.route("/api/status")
def api_status():
    with state_lock:
        return jsonify(dict(system_state))


@app.route("/api/arm", methods=["POST"])
def arm_control():
    data = request.get_json(silent=True) or {}
    armed = data.get("armed")
    if not isinstance(armed, bool):
        return jsonify({"success": False, "error": "Send JSON: {\"armed\": true|false}"}), 400
    with state_lock:
        system_state["armed"] = armed
        if not armed:
            system_state["alarm"] = False
    if not armed:
        set_alarm_outputs(False)
    return jsonify({"success": True, "armed": armed})


@app.route("/api/events")
def api_events():
    return jsonify(get_events(limit=25))


@app.route("/captures/<path:filename>")
def capture_file(filename):
    return send_from_directory(CAPTURES_DIR, filename)


@app.route("/api/health")
def health():
    with state_lock:
        return jsonify({"ok": True, "camera": system_state["camera"], "armed": system_state["armed"]})


if __name__ == "__main__":
    print("Smart Security API starting. On the Pi, open http://<PI_IP>:5000")
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
    finally:
        cam.close()
        cleanup()
