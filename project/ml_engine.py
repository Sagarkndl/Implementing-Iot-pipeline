# ml_engine.py  —  ML models for Lindstorm Warehouse
# Model 1: Demand Forecasting  (Linear Regression)
# Model 2: Worker Performance  (Weighted Scoring)

import sqlite3, random
from datetime import datetime, timedelta
from collections import defaultdict

DB_FILE = "warehouse.db"


def _conn():
    c = sqlite3.connect(DB_FILE)
    c.row_factory = sqlite3.Row
    return c


# ── Model 1: Linear Regression ────────────────────────────────

def _linreg(xs, ys):
    n = len(xs)
    if n < 2:
        return 0, sum(ys)/n if ys else 0
    xm, ym = sum(xs)/n, sum(ys)/n
    num = sum((xs[i]-xm)*(ys[i]-ym) for i in range(n))
    den = sum((xs[i]-xm)**2 for i in range(n))
    if den == 0:
        return 0, ym
    slope = num/den
    return slope, ym - slope*xm


def predict_location_demand():
    today = datetime.utcnow().date()
    days  = [(today - timedelta(days=i)) for i in range(6,-1,-1)]
    day_s = [d.strftime("%Y-%m-%d") for d in days]
    try:
        with _conn() as c:
            rows = c.execute("""
                SELECT location,
                       substr(timestamp,1,10) AS d,
                       COUNT(*) AS cnt
                FROM pick_log
                WHERE substr(timestamp,1,10) >= ?
                GROUP BY location, d""", (day_s[0],)).fetchall()
    except Exception:
        return []

    data = defaultdict(dict)
    for r in rows:
        data[r["location"]][r["d"]] = r["cnt"]

    results = []
    for loc, dc in data.items():
        ys = [dc.get(d,0) for d in day_s]
        slope, intercept = _linreg(list(range(7)), ys)
        pred = max(0, round(slope*7 + intercept))
        trend = "rising" if slope > 0.3 else ("falling" if slope < -0.3 else "stable")
        results.append({
            "location":   loc,
            "predicted":  pred,
            "trend":      trend,
            "recent_avg": round(sum(dc.get(d,0) for d in day_s[-3:])/3, 1),
        })
    return sorted(results, key=lambda r: r["predicted"], reverse=True)[:10]


# ── Model 2: Worker Performance Scoring ───────────────────────

def score_worker_performance():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            rows = c.execute("""
                SELECT ws.username, u.full_name,
                       ws.tasks_completed, ws.wrong_codes, ws.total_seconds
                FROM worker_stats ws
                LEFT JOIN users u ON ws.username=u.username
                WHERE ws.date=? AND u.role='worker'""", (today,)).fetchall()
    except Exception:
        return []

    out = []
    for r in rows:
        tasks = r["tasks_completed"] or 0
        if tasks == 0:
            continue
        wrongs   = r["wrong_codes"] or 0
        secs     = r["total_seconds"] or 0
        wr       = wrongs / tasks
        avg_t    = secs / tasks
        ws       = (1 - wr) * 50
        ss       = max(0, 50 - max(0, avg_t - 60) * 0.3)
        score    = min(100, max(0, round(ws + ss)))
        risk     = "Good" if score>=80 else ("Watch" if score>=60 else "At Risk")
        risk_col = "green" if score>=80 else ("amber" if score>=60 else "red")
        out.append({
            "username":       r["username"],
            "full_name":      r["full_name"] or r["username"],
            "tasks":          tasks,
            "wrong_codes":    wrongs,
            "avg_time_sec":   round(avg_t),
            "score":          score,
            "risk":           risk,
            "risk_col":       risk_col,
            "wrong_rate_pct": round(wr*100),
        })
    return sorted(out, key=lambda r: r["score"], reverse=True)


# ── Seed demo pick data ────────────────────────────────────────

def seed_demo_pick_log():
    random.seed(42)
    today = datetime.utcnow().date()
    locs  = ["R01-10","R01-11","R02-01","R02-05","R03-02"]
    try:
        with _conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS pick_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    location TEXT NOT NULL,
                    products INTEGER NOT NULL,
                    wrong_codes INTEGER DEFAULT 0
                )""")
            if c.execute("SELECT COUNT(*) FROM pick_log").fetchone()[0] > 5:
                return
            rows = []
            for off in range(7, 0, -1):
                day = today - timedelta(days=off)
                for _ in range(2 + off):
                    rows.append((day.strftime("%Y-%m-%dT09:00:00Z"),
                                 "R01-10", random.randint(1,4), 0))
                for loc in locs[1:]:
                    for _ in range(random.randint(1,3)):
                        rows.append((day.strftime("%Y-%m-%dT10:00:00Z"),
                                     loc, random.randint(1,3), random.randint(0,1)))
            c.executemany(
                "INSERT INTO pick_log(timestamp,location,products,wrong_codes) VALUES(?,?,?,?)",
                rows)
    except Exception as e:
        print(f"  ML seed note: {e}")
