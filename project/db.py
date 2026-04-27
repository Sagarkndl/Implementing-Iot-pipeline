# db.py  —  Lindstorm Warehouse database layer (SQLite)
# Smart routing: parses location codes (R01-10) to get row/col,
# then always returns the nearest pending task within the same order first.

import sqlite3, re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_FILE = "warehouse.db"


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def parse_location(loc):
    if not loc: return 0, 0
    m = re.match(r'[Rr](\d+)-(\d+)', loc)
    if m: return int(m.group(1)), int(m.group(2))
    parts = re.findall(r'\d+', loc)
    if len(parts) >= 2: return int(parts[0]), int(parts[1])
    if len(parts) == 1: return int(parts[0]), 0
    return 0, 0


def manhattan(loc_a, loc_b):
    """
    Weighted warehouse distance:
    Moving to a different ROW (aisle) costs 10x more than moving along a shelf.
    This correctly models that crossing an aisle is a much bigger detour.
    """
    r1,c1 = parse_location(loc_a)
    r2,c2 = parse_location(loc_b)
    return abs(r1-r2) * 10 + abs(c1-c2)


def create_tables():
    with get_conn() as c:
        for sql in [
            "ALTER TABLE tasks ADD COLUMN order_id TEXT DEFAULT NULL",
            "ALTER TABLE tasks ADD COLUMN row_num INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN col_num INTEGER DEFAULT 0",
        ]:
            try: c.execute(sql)
            except: pass

        c.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT DEFAULT NULL, location TEXT NOT NULL,
            confirm_code TEXT NOT NULL, products INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', sequence_no INTEGER NOT NULL,
            assigned_to TEXT DEFAULT NULL, in_progress INTEGER DEFAULT 0,
            started_at TEXT DEFAULT NULL, completed_at TEXT DEFAULT NULL,
            priority INTEGER DEFAULT 0, row_num INTEGER DEFAULT 0,
            col_num INTEGER DEFAULT 0)""")

        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('worker','supervisor')),
            full_name TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now')))""")

        c.execute("""CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            username TEXT, role TEXT, action TEXT NOT NULL, task_id INTEGER,
            location TEXT, entered_code TEXT, result TEXT, details TEXT)""")

        c.execute("""CREATE TABLE IF NOT EXISTS worker_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
            date TEXT NOT NULL, tasks_completed INTEGER DEFAULT 0,
            wrong_codes INTEGER DEFAULT 0, total_seconds INTEGER DEFAULT 0,
            UNIQUE(username, date))""")

        c.execute("""CREATE TABLE IF NOT EXISTS pick_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
            location TEXT NOT NULL, products INTEGER NOT NULL,
            wrong_codes INTEGER DEFAULT 0)""")

        # Back-fill row_num/col_num for existing rows
        for row in c.execute("SELECT id,location FROM tasks WHERE row_num=0 AND col_num=0"):
            r,col = parse_location(row["location"])
            if r or col:
                c.execute("UPDATE tasks SET row_num=?,col_num=? WHERE id=?", (r,col,row["id"]))


def seed_tasks():
    with get_conn() as c:
        if c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            for loc,code,qty,seq,pri in [
                ("R01-10","85",2,1,0),("R01-11","43",1,2,0),
                ("R02-01","99",4,3,1),("R02-05","17",3,4,0),
                ("R03-02","62",2,5,0),
            ]:
                r,col = parse_location(loc)
                c.execute("""INSERT INTO tasks
                    (location,confirm_code,products,status,sequence_no,priority,row_num,col_num)
                    VALUES (?,?,?,'pending',?,?,?,?)""", (loc,code,qty,seq,pri,r,col))


def seed_users():
    with get_conn() as c:
        if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            for u,p,r,n in [
                ("worker1","worker123","worker","Sagar Kandel"),
                ("worker2","worker456","worker","Khuman Singh Rana"),
                ("worker3","worker789","worker","Bijay Satyal"),
                ("supervisor1","super123","supervisor","Matti Lindstorm"),
            ]:
                c.execute("INSERT INTO users(username,password_hash,role,full_name) VALUES(?,?,?,?)",
                          (u, generate_password_hash(p), r, n))


def verify_user(username, password):
    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if row and check_password_hash(row["password_hash"], password):
        return dict(row)
    return None


def _warehouse_sort_locs(tasks):
    """
    Strict aisle-by-aisle routing:
    - Complete ALL of Row 1 (R01) first, shelf 1 → 2 → 3 in order
    - Then ALL of Row 2 (R02), shelf 1 → 2 → 3 in order
    - Then ALL of Row 3 (R03), shelf 1 → 2 → 3 in order
    - Never jumps to the next row until current row is fully done
    """
    from collections import defaultdict
    row_groups = defaultdict(list)
    for t in tasks:
        r, c = parse_location(t.get("location",""))
        row_groups[r].append((c, t))

    result = []
    for row_num in sorted(row_groups.keys()):   # R01 first, then R02, then R03
        items = row_groups[row_num]
        items.sort(key=lambda x: x[0])          # shelf 1, 2, 3... in strict order
        result.extend([t for _, t in items])
    return result


def _smart_next(tasks, current_loc):
    """
    Strict warehouse aisle routing:
    - Always finish the current row before moving to the next row
    - Within a row: go shelf 1, 2, 3... in strict ascending order
    - High priority tasks go first but still follow row order
    Example: R01-01, R01-05, R01-10 → then R02-01, R02-03 → then R03-02
    """
    if not tasks: return None

    # High priority first, same row logic applies within each group
    high   = [t for t in tasks if t.get("priority",0) > 0]
    normal = [t for t in tasks if t.get("priority",0) == 0]

    for group in [high, normal]:
        if not group:
            continue
        sorted_group = _warehouse_sort_locs(group)
        return sorted_group[0]

    return None


def get_order_completion_status(username, order_id):
    """
    Check if all tasks in an order are done for this worker.
    Returns True if the order is fully complete.
    """
    if not order_id:
        return False
    with get_conn() as c:
        total   = c.execute("SELECT COUNT(*) FROM tasks WHERE order_id=?",
                            (order_id,)).fetchone()[0]
        done    = c.execute("SELECT COUNT(*) FROM tasks WHERE order_id=? AND status='done'",
                            (order_id,)).fetchone()[0]
        pending = c.execute("SELECT COUNT(*) FROM tasks WHERE order_id=? AND status='pending'",
                            (order_id,)).fetchone()[0]
    return total > 0 and pending == 0 and done == total


def get_next_pending_task(username=None, current_location=None):
    """
    Strict order routing:
    1. Find which order the worker is currently assigned to
    2. If they have an active order — only return tasks FROM THAT ORDER (row by row)
    3. Only pick the NEXT order when the current order is 100% done
    4. High priority orders are picked first when choosing a new order
    """
    with get_conn() as c:

        # ── Step 1: Which order is this worker currently on? ──────
        current_order_id = None
        if username:
            # Check for any task they have in progress right now
            ip = c.execute("""
                SELECT order_id FROM tasks
                WHERE assigned_to=? AND in_progress=1 AND order_id IS NOT NULL
                LIMIT 1""", (username,)).fetchone()
            if ip:
                current_order_id = ip["order_id"]

            if not current_order_id:
                # Check if their last completed task belongs to an order
                # that still has pending tasks remaining
                last = c.execute("""
                    SELECT order_id FROM tasks
                    WHERE assigned_to=? AND status='done' AND order_id IS NOT NULL
                    ORDER BY completed_at DESC LIMIT 1""", (username,)).fetchone()
                if last:
                    oid = last["order_id"]
                    still_pending = c.execute("""
                        SELECT COUNT(*) FROM tasks
                        WHERE order_id=? AND status='pending' AND in_progress=0""",
                        (oid,)).fetchone()[0]
                    if still_pending > 0:
                        current_order_id = oid

        # ── Step 2: Get pending tasks ─────────────────────────────
        if username:
            rows = c.execute("""
                SELECT * FROM tasks
                WHERE status='pending' AND in_progress=0
                  AND (assigned_to=? OR assigned_to IS NULL)
                ORDER BY priority DESC, row_num ASC, col_num ASC
            """, (username,)).fetchall()
        else:
            rows = c.execute("""
                SELECT * FROM tasks
                WHERE status='pending' AND in_progress=0
                ORDER BY priority DESC, row_num ASC, col_num ASC
            """).fetchall()

        if not rows:
            return None

        tasks = [dict(r) for r in rows]

        # ── Step 3: Pick next task ────────────────────────────────
        chosen = None

        if current_order_id:
            # Worker is mid-order — ONLY give them tasks from this order
            same_order = [t for t in tasks if t.get("order_id") == current_order_id]
            if same_order:
                same_order = _warehouse_sort_locs(same_order)
                chosen = same_order[0]
            # If same_order is empty — this order is fully done, fall through to next order

        if chosen is None:
            # No current order (or current order fully done) — pick the next order
            # Choose the earliest order_id (FIFO — first created order goes first)
            # Group all pending tasks by order
            from collections import defaultdict
            order_groups = defaultdict(list)
            solo_tasks   = []
            for t in tasks:
                oid = t.get("order_id")
                if oid:
                    order_groups[oid].append(t)
                else:
                    solo_tasks.append(t)

            if order_groups:
                # Pick highest priority order first, then earliest order_id (FIFO)
                def order_priority(oid):
                    grp = order_groups[oid]
                    max_pri = max(t.get("priority",0) for t in grp)
                    return (-max_pri, oid)  # highest priority first, then alphabetical

                best_order_id = sorted(order_groups.keys(), key=order_priority)[0]
                ordered = _warehouse_sort_locs(order_groups[best_order_id])
                chosen = ordered[0]
            elif solo_tasks:
                solo_tasks = _warehouse_sort_locs(solo_tasks)
                chosen = solo_tasks[0]

        if chosen is None:
            return None

        # ── Step 4: Lock the task ─────────────────────────────────
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        affected = c.execute("""
            UPDATE tasks SET in_progress=1, assigned_to=?, started_at=?
            WHERE id=? AND in_progress=0
        """, (username or "unassigned", now, chosen["id"])).rowcount

        return chosen if affected else None


def mark_task_done(task_id, username=None):
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_conn() as c:
        task = c.execute(
            "SELECT location,products,started_at FROM tasks WHERE id=?", (task_id,)
        ).fetchone()
        c.execute("UPDATE tasks SET status='done',in_progress=0,completed_at=? WHERE id=?", (now,task_id))
        if username and task:
            elapsed = 0
            if task["started_at"]:
                try:
                    s = datetime.fromisoformat(task["started_at"].replace("Z",""))
                    elapsed = int((datetime.utcnow()-s).total_seconds())
                except: pass
            today = datetime.utcnow().strftime("%Y-%m-%d")
            c.execute("""INSERT INTO worker_stats(username,date,tasks_completed,total_seconds)
                VALUES(?,?,1,?) ON CONFLICT(username,date) DO UPDATE SET
                tasks_completed=tasks_completed+1, total_seconds=total_seconds+?""",
                (username,today,elapsed,elapsed))
            c.execute("INSERT INTO pick_log(timestamp,location,products,wrong_codes) VALUES(?,?,?,0)",
                      (now,task["location"],task["products"]))


def release_task(task_id):
    with get_conn() as c:
        c.execute("UPDATE tasks SET in_progress=0,assigned_to=NULL,started_at=NULL WHERE id=? AND status='pending'", (task_id,))


def reset_all_tasks():
    with get_conn() as c:
        c.execute("UPDATE tasks SET status='pending',in_progress=0,assigned_to=NULL,started_at=NULL,completed_at=NULL")


def list_all_tasks():
    with get_conn() as c:
        rows = c.execute("""SELECT * FROM tasks
            ORDER BY
                CASE WHEN order_id IS NULL THEN 1 ELSE 0 END,
                order_id,
                row_num ASC,
                col_num ASC
        """).fetchall()
    return [dict(r) for r in rows]


def get_task_summary():
    with get_conn() as c:
        total   = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        done    = c.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
        pending = c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending' AND in_progress=0").fetchone()[0]
        active  = c.execute("SELECT COUNT(*) FROM tasks WHERE in_progress=1").fetchone()[0]
    return {"total":total,"done":done,"pending":pending,"in_progress":active}


def get_recent_logs(limit=100):
    with get_conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]


def get_todays_worker_stats():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_conn() as c:
        rows = c.execute("""SELECT ws.username, u.full_name,
            ws.tasks_completed, ws.wrong_codes, ws.total_seconds
            FROM worker_stats ws LEFT JOIN users u ON ws.username=u.username
            WHERE ws.date=? ORDER BY ws.tasks_completed DESC""", (today,)).fetchall()
    return [dict(r) for r in rows]


def log_action(username, role, action, task_id=None, location=None,
               entered_code=None, result=None, details=None):
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with get_conn() as c:
        c.execute("""INSERT INTO audit_logs
            (timestamp,username,role,action,task_id,location,entered_code,result,details)
            VALUES(?,?,?,?,?,?,?,?,?)""", (ts,username,role,action,task_id,location,entered_code,result,details))
        if action == "check_code" and result == "wrong" and username:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            c.execute("""INSERT INTO worker_stats(username,date,wrong_codes) VALUES(?,?,1)
                ON CONFLICT(username,date) DO UPDATE SET wrong_codes=wrong_codes+1""", (username,today))


def next_seq():
    with get_conn() as c:
        return int(c.execute("SELECT COALESCE(MAX(sequence_no),0)+1 FROM tasks").fetchone()[0])


def create_new_task(location, confirm_code, products, status="pending",
                    sequence_no=None, priority=0, assigned_to=None, order_id=None):
    if sequence_no is None: sequence_no = next_seq()
    row_num, col_num = parse_location(location)
    with get_conn() as c:
        c.execute("""INSERT INTO tasks
            (order_id,location,confirm_code,products,status,sequence_no,priority,assigned_to,row_num,col_num)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (order_id,location,confirm_code,int(products),status,int(sequence_no),int(priority),assigned_to,row_num,col_num))


def delete_task(task_id):
    with get_conn() as c:
        c.execute("DELETE FROM tasks WHERE id=? AND status='pending' AND in_progress=0", (task_id,))


def list_all_users():
    with get_conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM users ORDER BY role,username").fetchall()]


def create_new_user(username, password, role, full_name=""):
    with get_conn() as c:
        c.execute("INSERT INTO users(username,password_hash,role,full_name) VALUES(?,?,?,?)",
                  (username, generate_password_hash(password), role, full_name))
