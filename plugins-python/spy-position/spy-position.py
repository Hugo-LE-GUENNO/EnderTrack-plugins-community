import threading
import time

NAME        = "Spy Position"
VERSION     = "1.0.0"
DESCRIPTION = "Poll stage position via M114 at regular intervals."

SECTIONS = {
    "settings": {
        "inputs": [
            {"type": "input",  "id": "interval", "label": "Interval (s)", "default": "2"},
            {"type": "button", "label": "Start polling", "action": "start_live", "style": "primary"},
            {"type": "button", "label": "Stop polling",  "action": "stop_live"},
        ],
        "outputs": [],
    },
    "navigation": {
        "inputs": [],
        "outputs": [
            {"type": "text", "id": "position", "label": "Position (M114)"},
        ],
    },
}

_stop_event = threading.Event()
_worker     = None
_lock       = threading.Lock()


def _loop(ctx, interval):
    global _worker
    try:
        while not _stop_event.is_set():
            stage = ctx.stage
            if stage is not None:
                try:
                    p = stage.get_position(as_dict=True)
                    ctx.update_output("position", "X %.3f  Y %.3f  Z %.3f" % (p['X'], p['Y'], p['Z']))
                    ctx.bus.publish('position:gcode', {'x': p['X'], 'y': p['Y'], 'z': p['Z']})
                except Exception as e:
                    ctx.update_output("position", "Error: %s" % e)
            else:
                ctx.update_output("position", "No stage.")
            _stop_event.wait(interval)
    finally:
        with _lock:
            if _worker is threading.current_thread():
                _worker = None


def _start(ctx, interval):
    global _worker
    _stop_event.clear()
    t = threading.Thread(target=_loop, args=(ctx, interval), daemon=True)
    with _lock:
        _worker = t
    t.start()


def _stop():
    _stop_event.set()
    with _lock:
        w = _worker
    if w and w.is_alive():
        w.join(timeout=5)


def start_live(ctx, params):
    _stop()
    interval = max(0.5, float(params.get("interval") or 2))
    _start(ctx, interval)
    return {"success": True}


def stop_live(ctx, params=None):
    _stop()
    ctx.update_output("position", "—")
    return {"success": True}


def on_unload(ctx):
    _stop()
