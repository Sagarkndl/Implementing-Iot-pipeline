import os
import secrets
from functools import wraps
from flask import Flask, request, jsonify
from db import (
    get_order_completion_status,
    create_tables, seed_tasks, seed_users,
    get_next_pending_task, mark_task_done, reset_all_tasks, release_task,
    verify_user, log_action, get_recent_logs,
    create_new_task, delete_task, list_all_tasks, get_task_summary,
    get_todays_worker_stats, list_all_users, create_new_user
)

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "lindstorm-change-this-in-production")

# We store active login tokens in memory.
# Each token maps to the logged-in user's info and current task state.
# Format: { "token123": { "username": "worker1", "role": "worker", ... } }
active_sessions = {}


# ─────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────

def get_token_from_header():
    """Extract the Bearer token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def get_current_user():
    """Return the logged-in user dict, or None if not authenticated."""
    token = get_token_from_header()
    if not token:
        return None
    return active_sessions.get(token)


def require_login(role=None):
    """
    Decorator to protect routes.
    If role is given (e.g. "supervisor"), only that role can access the route.
    """
    def decorator(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"ok": False, "error": "Please log in first"}), 401
            if role and user["role"] != role:
                return jsonify({"ok": False, "error": "Access denied — supervisor only"}), 403
            return view_function(*args, **kwargs)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────
# General routes
# ─────────────────────────────────────────────────────────────

@app.get("/")
def home():
    """Show available API endpoints."""
    return jsonify({
        "ok":      True,
        "system":  "Lindstorm Warehouse Picking API",
        "version": "2.0",
        "endpoints": [
            "GET  /api/health",
            "POST /api/login",
            "POST /api/logout",
            "GET  /api/task/current",
            "POST /api/task/check-code",
            "POST /api/task/done",
            "POST /api/task/reset        [supervisor]",
            "POST /api/tasks/create      [supervisor]",
            "DELETE /api/tasks/<id>      [supervisor]",
            "GET  /api/tasks             [supervisor]",
            "GET  /api/tasks/stats       [supervisor]",
            "GET  /api/logs              [supervisor]",
            "GET  /api/workers           [supervisor]",
            "GET  /api/workers/stats     [supervisor]",
            "POST /api/workers/create    [supervisor]",
        ]
    })


@app.get("/api/health")
def health_check():
    """Simple check to confirm the API is running."""
    stats = get_task_summary()
    return jsonify({"ok": True, "message": "Lindstorm API is running", "stats": stats})


# ─────────────────────────────────────────────────────────────
# Login and logout
# ─────────────────────────────────────────────────────────────

@app.post("/api/login")
def login():
    """
    Log in with username and password.
    Returns a token that the frontend uses for all future requests.
    """
    data     = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = verify_user(username, password)
    if not user:
        return jsonify({"ok": False, "error": "Wrong username or password"}), 401

    # Create a random token for this session
    token = secrets.token_urlsafe(32)
    active_sessions[token] = {
        "username":       user["username"],
        "role":           user["role"],
        "full_name":      user["full_name"],
        "current_task":   None,   # the task this worker is currently doing
        "waiting_for_done": False # True after the code is confirmed
    }

    log_action(user["username"], user["role"], "login", result="success")

    return jsonify({
        "ok":    True,
        "token": token,
        "user": {
            "username":  user["username"],
            "role":      user["role"],
            "full_name": user["full_name"]
        }
    })


@app.post("/api/logout")
@require_login()
def logout():
    """
    Log out. If the worker had an active task, release it back to the queue
    so another worker can pick it up.
    """
    token = get_token_from_header()
    user  = get_current_user()

    # Release unfinished task back to pending
    active_task = user.get("current_task")
    if active_task:
        release_task(active_task["id"])

    log_action(user["username"], user["role"], "logout", result="success")
    active_sessions.pop(token, None)

    return jsonify({"ok": True, "message": "Logged out"})


# ─────────────────────────────────────────────────────────────
# Worker task flow
# ─────────────────────────────────────────────────────────────

@app.get("/api/task/current")
@require_login()
def get_current_task():
    """
    Get the worker's current task.
    If they don't have one yet, automatically assign the next available task.
    """
    token = get_token_from_header()
    user  = active_sessions[token]

    # Assign a task if the worker doesn't have one
    if user["current_task"] is None:
        task = get_next_pending_task(username=user["username"])
        user["current_task"]    = task
        user["waiting_for_done"] = False

    task             = user["current_task"]
    waiting_for_done = user["waiting_for_done"]

    if task is None:
        return jsonify({
            "ok":              True,
            "task":            None,
            "waiting_for_done": False,
            "message":         "All tasks are completed!"
        })

    return jsonify({
        "ok": True,
        "task": {
            "id":       task["id"],
            "location": task["location"],
            "products": task["products"] if waiting_for_done else None,
            "priority": task.get("priority", 0)
        },
        "waiting_for_done": waiting_for_done,
        "message": (
            f"Pick {task['products']} product(s) then mark done"
            if waiting_for_done
            else "Enter the confirmation code"
        )
    })


@app.post("/api/task/check-code")
@require_login()
def check_confirmation_code():
    """
    Worker submits the confirmation code from the cell label.
    If correct, they move to the picking step.
    If wrong, they try again.
    """
    token = get_token_from_header()
    user  = active_sessions[token]

    data         = request.get_json(silent=True) or {}
    entered_code = str(data.get("code", "")).strip()

    task = user.get("current_task")
    if not task:
        return jsonify({"ok": False, "error": "No active task"}), 400

    if user["waiting_for_done"]:
        return jsonify({"ok": False, "error": "Already confirmed — please mark done"}), 400

    if entered_code == task["confirm_code"]:
        # Code is correct - move to picking step
        user["waiting_for_done"] = True
        log_action(user["username"], user["role"], "check_code",
                   task_id=task["id"], location=task["location"],
                   entered_code=entered_code, result="correct")

        return jsonify({
            "ok":      True,
            "correct": True,
            "message": f"Code correct! Pick {task['products']} product(s).",
            "products": task["products"]
        })

    # Code is wrong
    log_action(user["username"], user["role"], "check_code",
               task_id=task["id"], location=task["location"],
               entered_code=entered_code, result="wrong")

    return jsonify({
        "ok":      False,
        "correct": False,
        "message": "Wrong code. Check the label on the cell."
    }), 400


@app.post("/api/task/done")
@require_login()
def mark_done():
    """
    Worker confirms they have picked all the products.
    The task is marked as completed and their stats are updated.
    """
    token = get_token_from_header()
    user  = active_sessions[token]

    task = user.get("current_task")
    if not task:
        return jsonify({"ok": False, "error": "No active task"}), 400

    if not user["waiting_for_done"]:
        return jsonify({"ok": False, "error": "Confirm the code first"}), 400

    # Save completed location for the response message
    completed_location = task["location"]

    mark_task_done(task["id"], username=user["username"])
    log_action(user["username"], user["role"], "done",
               task_id=task["id"], location=completed_location, result="completed")

    # Clear the worker's task so they get a new one next time
    user["current_task"]    = None
    user["waiting_for_done"] = False

    # Check if the whole order is now complete
    order_complete = False
    completed_order_id = task.get("order_id")
    if completed_order_id:
        try:
            order_complete = get_order_completion_status(user["username"], completed_order_id)
        except Exception:
            pass

    return jsonify({
        "ok":                  True,
        "message":             f"Task at {completed_location} completed!",
        "completed_location":  completed_location,
        "order_complete":      order_complete,
        "completed_order_id":  completed_order_id if order_complete else None
    })


# ─────────────────────────────────────────────────────────────
# Supervisor — task management
# ─────────────────────────────────────────────────────────────

@app.get("/api/tasks")
@require_login(role="supervisor")
def list_tasks():
    """Return the full list of tasks."""
    return jsonify({"ok": True, "tasks": list_all_tasks()})


@app.get("/api/tasks/stats")
@require_login(role="supervisor")
def task_stats():
    """Return task counts grouped by status."""
    return jsonify({"ok": True, "stats": get_task_summary()})


@app.post("/api/task/reset")
@require_login(role="supervisor")
def reset_tasks():
    """
    Reset all tasks back to pending.
    Also clears any in-memory task state for active workers.
    """
    user = get_current_user()

    # Clear all active workers' task states
    for session_data in active_sessions.values():
        session_data["current_task"]    = None
        session_data["waiting_for_done"] = False

    reset_all_tasks()
    log_action(user["username"], user["role"], "reset_tasks", result="success")

    return jsonify({"ok": True, "message": "All tasks have been reset to pending"})


@app.post("/api/tasks/create")
@require_login(role="supervisor")
def create_task():
    """Create a new picking task."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    location     = (data.get("location") or "").strip().upper()
    confirm_code = (data.get("confirm_code") or "").strip()
    products     = data.get("products")
    priority     = int(data.get("priority", 0))
    assigned_to  = data.get("assigned_to") or None

    # Check that all required fields are provided
    if not location or not confirm_code or products is None:
        return jsonify({"ok": False, "error": "location, confirm_code and products are required"}), 400

    create_new_task(location, confirm_code, int(products),
                    priority=priority, assigned_to=assigned_to)

    log_action(user["username"], user["role"], "create_task",
               location=location, result="created",
               details=f"products={products} priority={priority} assigned={assigned_to}")

    return jsonify({"ok": True, "message": f"Task created at {location}"})


@app.delete("/api/tasks/<int:task_id>")
@require_login(role="supervisor")
def remove_task(task_id):
    """Delete a pending task."""
    user = get_current_user()
    delete_task(task_id)
    log_action(user["username"], user["role"], "delete_task",
               task_id=task_id, result="deleted")
    return jsonify({"ok": True, "message": f"Task {task_id} deleted"})


# ─────────────────────────────────────────────────────────────
# Supervisor — worker management
# ─────────────────────────────────────────────────────────────

@app.get("/api/workers")
@require_login(role="supervisor")
def get_workers():
    """List all user accounts."""
    return jsonify({"ok": True, "workers": list_all_users()})


@app.get("/api/workers/stats")
@require_login(role="supervisor")
def get_worker_stats():
    """Get today's performance stats for all workers."""
    return jsonify({"ok": True, "stats": get_todays_worker_stats()})


@app.post("/api/workers/create")
@require_login(role="supervisor")
def create_worker():
    """Create a new worker or supervisor account."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    username  = (data.get("username") or "").strip()
    password  = data.get("password") or ""
    role      = data.get("role", "worker")
    full_name = (data.get("full_name") or "").strip()

    if not username or not password:
        return jsonify({"ok": False, "error": "Username and password are required"}), 400

    if role not in ("worker", "supervisor"):
        return jsonify({"ok": False, "error": "Role must be 'worker' or 'supervisor'"}), 400

    try:
        create_new_user(username, password, role, full_name)
        log_action(user["username"], user["role"], "create_user",
                   result="created", details=f"new_user={username} role={role}")
        return jsonify({"ok": True, "message": f"Account created for {username}"})
    except Exception as error:
        return jsonify({"ok": False, "error": str(error)}), 400


# ─────────────────────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────────────────────

@app.get("/api/logs")
@require_login(role="supervisor")
def view_logs():
    """Return recent audit log entries. Default is last 50."""
    limit = min(int(request.args.get("limit", 50)), 200)
    return jsonify({"ok": True, "logs": get_recent_logs(limit)})


# ─────────────────────────────────────────────────────────────
# Start the server
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_tables()
    seed_tasks()
    seed_users()
    print("Lindstorm API starting on port 5001...")
    app.run(host="0.0.0.0", port=5001, debug=True)
