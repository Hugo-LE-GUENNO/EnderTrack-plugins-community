import json
import urllib.request
import urllib.error

NAME        = "EnderHuman"
VERSION     = "1.0.0"
DESCRIPTION = "Chat with an LLM to control the microscope in natural language."

# Conversation history (session-scoped)
_history = []

SYSTEM_PROMPT = """You are an assistant controlling a motorized microscope stage (EnderTrack).
The user speaks to you in natural language. You must respond ONLY with a valid JSON object.

Available actions:
- move_absolute     : params: x (float), y (float), z (float)
- move_relative     : params: dx (float), dy (float), dz (float)
- capture           : params: path (str), fmt (str, default "tiff")
- capture_series    : params: prefix (str), n (int), interval_s (float, default 1.0)
- light_on          : params: r (int 0-255), g (int 0-255), b (int 0-255), intensity (float 0-1)
- light_off         : params: (none)
- home              : params: (none)
- get_position      : params: (none)
- add_waypoint      : params: x (float), y (float), z (float), name (str)
- list_waypoints    : params: (none)
- go_to_waypoint    : params: name (str)
- z_stack           : params: range_mm (float), step_mm (float), prefix (str, default "stack")
- set_feedrate      : params: feedrate (float, mm/min)
- none              : use when the message is a question or requires no hardware action

Response format (strict JSON array, no markdown, always an array even for a single action):
[{"action": "<action_name>", "params": {}, "message": "<short human-readable explanation>"}]

For complex requests like "do a demo" or "run a sequence", return multiple steps.

Examples:
User: "go to x=10 y=20 z=5"
[{"action": "move_absolute", "params": {"x": 10, "y": 20, "z": 5}, "message": "Moving to X=10 Y=20 Z=5."}]

User: "do a demo"
[
  {"action": "light_on", "params": {"r": 255, "g": 255, "b": 255, "intensity": 1.0}, "message": "Turning on light."},
  {"action": "home", "params": {}, "message": "Homing the stage."},
  {"action": "move_absolute", "params": {"x": 50, "y": 50, "z": 10}, "message": "Moving to center."},
  {"action": "capture", "params": {"path": "/home/pi/demo.tiff"}, "message": "Capturing image."},
  {"action": "light_off", "params": {}, "message": "Turning off light."}
]

User: "where am I?"
[{"action": "get_position", "params": {}, "message": "Fetching current stage position."}]
"""

SECTIONS = {
    "settings": {
        "inputs": [
            {"type": "textarea", "id": "groq_url",   "label": "Groq API URL",  "default": "https://api.groq.com/openai/v1/chat/completions", "rows": 2},
            {"type": "textarea", "id": "groq_token", "label": "API Token",     "default": "", "rows": 2},
            {"type": "textarea", "id": "groq_model", "label": "Model",         "default": "qwen/qwen3.8-27b", "rows": 1},
            {"type": "button", "label": "Clear conversation", "action": "clear_history", "style": "secondary"},
        ],
        "outputs": [
            {"type": "text", "id": "settings_status", "label": "Status"},
        ]
    },
    "automation": {
        "inputs": [
            {"type": "textarea", "id": "user_message", "label": "Your message", "placeholder": "Ask me anything, e.g: do a demo, take a picture, go to x=50 y=50...", "rows": 4},
            {"type": "button", "label": "Send",  "action": "send_message",  "style": "primary"},
        ],
        "outputs": [
            {"type": "text",  "id": "chat_history", "label": "Conversation"},
            {"type": "text",  "id": "last_action",  "label": "Last action executed"},
        ]
    }
}

SCENARIO_ACTIONS = [
    {
        "id": "send_message",
        "label": "EnderHuman — Send message",
        "timeout_ms": 30000,
        "params": [
            {"id": "user_message", "label": "Message", "type": "string", "default": "take a picture"},
            {"id": "groq_url",     "label": "Groq API URL", "type": "string", "default": "https://api.groq.com/openai/v1/chat/completions"},
            {"id": "groq_token",   "label": "API Token",    "type": "string", "default": ""},
            {"id": "groq_model",   "label": "Model",        "type": "string", "default": "qwen/qwen3.8-27b"},
        ]
    }
]


# ── Groq API call ─────────────────────────────────────────────────────────────

def _call_groq(url, token, model, messages):
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1024,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0",
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


# ── Action dispatcher ─────────────────────────────────────────────────────────

def _execute_action(ctx, action, params):  # noqa: C901
    stage = ctx.stage
    cam   = ctx.cam
    light = ctx.light

    if action == "move_absolute":
        if stage is None:
            return "Stage not connected."
        pos = stage.position
        x = params.get("x", pos["X"])
        y = params.get("y", pos["Y"])
        z = params.get("z", pos["Z"])
        stage.move_absolute(x, y, z)
        stage.finish_moves()
        return f"Moved to X={x} Y={y} Z={z}"

    elif action == "move_relative":
        if stage is None:
            return "Stage not connected."
        stage.move_relative(
            dx=params.get("dx", 0),
            dy=params.get("dy", 0),
            dz=params.get("dz", 0)
        )
        stage.finish_moves()
        return f"Relative move: dx={params.get('dx',0)} dy={params.get('dy',0)} dz={params.get('dz',0)}"

    elif action == "capture":
        if cam is None:
            return "Camera not available."
        path = params.get("path", "/home/pi/capture.tiff")
        fmt  = params.get("fmt", "tiff")
        result = cam.capture(path, fmt=fmt)
        return f"Image saved to {result.get('path', path)}" if result.get("success") else "Capture failed."

    elif action == "light_on":
        light.on(
            r=params.get("r", 255),
            g=params.get("g", 255),
            b=params.get("b", 255),
            intensity=params.get("intensity", 1.0)
        )
        return "Light on."

    elif action == "light_off":
        light.off()
        return "Light off."

    elif action == "home":
        if stage is None:
            return "Stage not connected."
        stage.home()
        return "Homing done."

    elif action == "get_position":
        if stage is None:
            return "Stage not connected."
        pos = stage.position
        return f"Position: X={pos['X']} Y={pos['Y']} Z={pos['Z']}"

    elif action == "add_waypoint":
        x    = params.get("x", 0)
        y    = params.get("y", 0)
        z    = params.get("z", 0)
        name = params.get("name", "Point")
        ctx.lists.add(x, y, z, name=name)
        return f"Waypoint '{name}' added at X={x} Y={y} Z={z}"

    elif action == "list_waypoints":
        all_lists = ctx.lists.all
        if not all_lists:
            return "No waypoints saved."
        lines = []
        for group in all_lists:
            for pt in group.get("positions", []):
                lines.append(f"  {pt.get('name','?')} — X={pt.get('x')} Y={pt.get('y')} Z={pt.get('z')}")
        return "Waypoints:\n" + "\n".join(lines) if lines else "No waypoints saved."

    elif action == "go_to_waypoint":
        if stage is None:
            return "Stage not connected."
        name = params.get("name", "")
        all_lists = ctx.lists.all
        for group in all_lists:
            for pt in group.get("positions", []):
                if pt.get("name", "").lower() == name.lower():
                    x, y, z = pt["x"], pt["y"], pt["z"]
                    stage.move_absolute(x, y, z)
                    stage.finish_moves()
                    return f"Moved to waypoint '{name}' at X={x} Y={y} Z={z}"
        return f"Waypoint '{name}' not found."

    elif action == "z_stack":
        if stage is None:
            return "Stage not connected."
        if cam is None:
            return "Camera not available."
        import time
        rng    = float(params.get("range_mm", 1.0))
        step   = float(params.get("step_mm", 0.2))
        prefix = params.get("prefix", "stack")
        pos    = stage.position
        x0, y0, z0 = pos["X"], pos["Y"], pos["Z"]
        z_start = round(z0 - rng / 2, 4)
        z_end   = round(z0 + rng / 2, 4)
        stage.move_absolute(x0, y0, z_start, feedrate=3000)
        stage.finish_moves()
        i, z = 0, z_start
        while z <= z_end + 1e-6:
            cam.capture(f"./captures/{prefix}_{i:03d}.tiff")
            i += 1
            z = round(z + step, 4)
            stage.move_absolute(x0, y0, z, feedrate=1000)
            stage.finish_moves()
            time.sleep(0.05)
        stage.move_absolute(x0, y0, z0, feedrate=3000)
        stage.finish_moves()
        return f"Z-stack done: {i} frames, range={rng}mm, step={step}mm"

    elif action == "capture_series":
        if cam is None:
            return "Camera not available."
        import time
        prefix   = params.get("prefix", "capture")
        n        = int(params.get("n", 5))
        interval = float(params.get("interval_s", 1.0))
        for i in range(n):
            cam.capture(f"./captures/{prefix}_{i:03d}.tiff")
            if i < n - 1:
                time.sleep(interval)
        return f"Series done: {n} images saved with prefix '{prefix}'"

    elif action == "set_feedrate":
        if stage is None:
            return "Stage not connected."
        feedrate = float(params.get("feedrate", 3000))
        stage.send_gcode(f"M203 X{feedrate/60:.1f} Y{feedrate/60:.1f}", wait_ok=True)
        return f"Feedrate set to {feedrate} mm/min"

    elif action == "none":
        return ""

    return f"Unknown action: {action}"


# ── Plugin functions ──────────────────────────────────────────────────────────

def send_message(ctx, params):
    global _history

    user_msg = params.get("user_message", "").strip()
    if not user_msg:
        ctx.update_output("chat_history", "Please enter a message.")
        return {"success": False}

    url   = params.get("groq_url",   "https://api.groq.com/openai/v1/chat/completions")
    token = params.get("groq_token", "")
    model = params.get("groq_model", "qwen/qwen3.8-27b")

    if not token:
        ctx.update_output("chat_history", "No API token set in Settings.")
        return {"success": False}

    # Build stage context
    stage_ctx = _build_stage_context(ctx)

    # Build messages
    _history.append({"role": "user", "content": user_msg})
    system_with_ctx = SYSTEM_PROMPT + "\n" + stage_ctx
    messages = [{"role": "system", "content": system_with_ctx}] + _history

    ctx.log(f"EnderHuman — sending: {user_msg}")
    ctx.log(f"EnderHuman — token length: {len(token)}, starts with: {token[:8]}")
    ctx.log(f"EnderHuman — url: {url}, model: {model}")

    try:
        raw = _call_groq(url, token, model, messages)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        err = f"HTTP {e.code}: {e.reason} — {body}"
        ctx.log(err, level="warn")
        ctx.update_output("chat_history", err)
        return {"success": False}
    except Exception as e:
        ctx.log(str(e), level="warn")
        ctx.update_output("chat_history", str(e))
        return {"success": False}

    # Parse JSON response (always an array)
    try:
        clean = raw.strip()
        # Strip markdown code fences
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1]
            clean = clean.rsplit("```", 1)[0]
        clean = clean.strip()
        # Extract first JSON array found in the response
        start = clean.find('[')
        end   = clean.rfind(']')
        if start != -1 and end != -1:
            clean = clean[start:end+1]
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            parsed = [parsed]
    except json.JSONDecodeError:
        ctx.log(f"Invalid JSON from model: {raw}", level="warn")
        _history.append({"role": "assistant", "content": raw})
        ctx.update_output("chat_history", _format_history())
        ctx.update_output("last_action", "Could not parse model response.")
        return {"success": False}

    results = []
    for step in parsed:
        action  = step.get("action", "none")
        aparams = step.get("params", {})
        message = step.get("message", "")
        action_result = _execute_action(ctx, action, aparams)
        ctx.log(f"Action: {action} -> {action_result}", level="ok")
        if message:
            results.append(message)
        if action_result:
            results.append(f"[{action}] {action_result}")

    assistant_reply = "\n".join(results)
    _history.append({"role": "assistant", "content": assistant_reply})
    ctx.update_output("chat_history", _format_history())
    ctx.update_output("last_action", assistant_reply)

    return {"success": True}


def clear_history(ctx, params):
    global _history
    _history = []
    ctx.update_output("settings_status", "Conversation cleared.")
    ctx.update_output("chat_history", "")
    ctx.update_output("last_action", "")
    ctx.log("EnderHuman — conversation cleared.")
    return {"success": True}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_stage_context(ctx):
    lines = ["\n## Current microscope state"]
    stage = ctx.stage
    if stage:
        pos = stage.position
        lines.append(f"- Current position: X={pos['X']} Y={pos['Y']} Z={pos['Z']} mm")
        lim = stage.limits
        if lim:
            x_min, x_max = lim['x']
            y_min, y_max = lim['y']
            z_min, z_max = lim['z']
        else:
            cfg = ctx.config
            b = cfg.get('coordinateBounds', {})
            x_min = float(b.get('x', {}).get('min', 0))
            x_max = float(b.get('x', {}).get('max', 220))
            y_min = float(b.get('y', {}).get('min', 0))
            y_max = float(b.get('y', {}).get('max', 220))
            z_min = float(b.get('z', {}).get('min', 0))
            z_max = float(b.get('z', {}).get('max', 250))
        cx = round((x_min + x_max) / 2, 2)
        cy = round((y_min + y_max) / 2, 2)
        cz = round((z_min + z_max) / 2, 2)
        lines.append(f"- X range: {x_min} to {x_max} mm  (center: {cx})")
        lines.append(f"- Y range: {y_min} to {y_max} mm  (center: {cy})")
        lines.append(f"- Z range: {z_min} to {z_max} mm  (center: {cz})")
        lines.append(f"- Stage center: X={cx} Y={cy} Z={cz}")
    else:
        lines.append("- Stage: not connected")
    if ctx.cam:
        lines.append("- Camera: available")
    else:
        lines.append("- Camera: not available")
    return "\n".join(lines)


def _format_history():
    lines = []
    for msg in _history:
        role = "You" if msg["role"] == "user" else "Agent"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
